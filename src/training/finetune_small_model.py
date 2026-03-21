#!/usr/bin/env python3
"""Fine-tune Qwen2.5-1.5B-Instruct with LoRA for shell command completion.

Everything is hardcoded — no choices needed.
Run via: python finetune_small_model.py
Or via:  ai-setup  (from the zsh plugin)

Output: LoRA adapter saved to ~/.local/share/zsh-autocomplete/lora-adapter/
"""

import json
import logging
import sys
from pathlib import Path

MODEL_ID    = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_DIR = Path.home() / ".local/share/zsh-autocomplete/lora-adapter"
DATA_PATH   = Path(__file__).parent / "zsh_training_data.jsonl"

SYSTEM_PROMPT = (
    "You complete shell commands. "
    "Output only the completed command — no explanation, no markdown."
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------

def _check_deps() -> None:
    missing = []
    for pkg in ("torch", "transformers", "peft", "trl", "datasets", "accelerate"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        logger.error(f"Missing: {', '.join(missing)}")
        logger.error("pip install torch transformers peft trl datasets accelerate bitsandbytes")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

def _build_dataset(tokenizer, max_length: int = 256):
    """Return a pre-tokenized Dataset with input_ids and labels."""
    from datasets import Dataset

    records = []
    with open(DATA_PATH) as f:
        for line in f:
            rec = json.loads(line.strip())
            messages = [
                {"role": "system",    "content": SYSTEM_PROMPT},
                {"role": "user",      "content": f"Complete: {rec['input']}"},
                {"role": "assistant", "content": rec["output"]},
            ]
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            enc = tokenizer(text, truncation=True, max_length=max_length)
            enc["labels"] = enc["input_ids"].copy()
            records.append(enc)

    logger.info(f"Dataset: {len(records)} examples")
    return Dataset.from_list(records)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def _device_dtype():
    import torch
    if torch.backends.mps.is_available():
        return "mps", torch.float16
    if torch.cuda.is_available():
        return "cuda", torch.float16
    return "cpu", torch.float32


def train() -> None:
    _check_deps()

    # Try unsloth (2× faster on GPU/Apple Silicon) then fall back to peft
    try:
        _train_unsloth()
    except (ImportError, NotImplementedError):
        logger.info("unsloth not available — using standard peft path (still works, just slower)")
        _train_peft()


def _train_unsloth() -> None:
    from unsloth import FastLanguageModel
    from trl import SFTTrainer, SFTConfig
    import torch

    logger.info(f"Loading {MODEL_ID} via unsloth")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_ID,
        max_seq_length=256,
        dtype=None,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    use_bf16 = torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False
    _run_trainer(model, tokenizer, use_bf16=use_bf16)


def _train_peft() -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, TaskType

    _, dtype = _device_dtype()
    # Always load on CPU for training — accelerate/SFTTrainer handles
    # moving to MPS/CUDA. Loading directly to MPS causes device-index
    # errors in accelerate's prepare() step.
    logger.info(f"Loading {MODEL_ID} on cpu (trainer moves to accelerator device)")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, torch_dtype=dtype, trust_remote_code=True,
    )

    lora_cfg = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_cfg)
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable()
    model.print_trainable_parameters()

    use_bf16 = (dtype == torch.bfloat16)
    _run_trainer(model, tokenizer, use_bf16=use_bf16)


def _run_trainer(model, tokenizer, use_bf16: bool) -> None:
    import torch
    from trl import SFTTrainer, SFTConfig

    tmp_dir = str(ADAPTER_DIR) + "-tmp"
    dataset = _build_dataset(tokenizer)

    # MPS doesn't support fp16/bf16 training flags via accelerate —
    # use full float32 precision on MPS, fp16 on CUDA only.
    use_mps = torch.backends.mps.is_available() and not torch.cuda.is_available()
    cfg = SFTConfig(
        output_dir=tmp_dir,
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        fp16=(not use_bf16 and not use_mps and torch.cuda.is_available()),
        bf16=(use_bf16 and torch.cuda.is_available()),
        logging_steps=20,
        save_strategy="no",
        optim="adamw_torch",
        weight_decay=0.01,
        report_to="none",
    )
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=cfg,
    )

    logger.info("Training started...")
    trainer.train()

    # Save LoRA adapter (only the small delta weights, not the full model)
    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(ADAPTER_DIR))
    tokenizer.save_pretrained(str(ADAPTER_DIR))
    logger.info(f"LoRA adapter saved to {ADAPTER_DIR}")

    # Invalidate any previously cached merged model so the daemon re-merges
    # with the new adapter on next restart
    merged_dir = Path.home() / ".local/share/zsh-autocomplete/merged-model"
    if merged_dir.exists():
        import shutil
        shutil.rmtree(merged_dir)
        logger.info("Cleared cached merged model — daemon will re-merge on next start")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not DATA_PATH.exists():
        logger.error(f"Training data not found: {DATA_PATH}")
        logger.error("Run: python generate_shell_data.py")
        sys.exit(1)

    train()
    print(f"\nDone. Adapter at: {ADAPTER_DIR}")
    print("Restart the daemon to load the fine-tuned model: ai-restart")
