#!/usr/bin/env python3
"""Autocomplete daemon.

Loads Qwen2.5-0.5B-Instruct + the local LoRA adapter (if trained) directly
via transformers/peft.  Stays alive across commands; the model is always warm.

Socket  : ~/.cache/zsh-autocomplete.sock
Log     : ~/.cache/zsh-autocomplete.log
PID     : ~/.cache/zsh-autocomplete.pid

Request  (JSON): {"id": "...", "input": "git comm"}
Response (JSON): {"id": "...", "completion": "git commit -m \"\""}
"""

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path

MODEL_ID     = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_DIR  = Path.home() / ".local/share/zsh-autocomplete/lora-adapter"
MERGED_DIR   = Path.home() / ".local/share/zsh-autocomplete/merged-model"
SOCKET_PATH  = Path.home() / ".cache/zsh-autocomplete.sock"
PID_PATH     = Path.home() / ".cache/zsh-autocomplete.pid"
LOG_PATH     = Path.home() / ".cache/zsh-autocomplete.log"

SYSTEM_PROMPT = (
    "You complete shell commands. "
    "Output only the completed command — no explanation, no markdown."
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="a")],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model backend (runs in a thread executor, keeps model in memory)
# ---------------------------------------------------------------------------

class _ModelBackend:
    def __init__(self) -> None:
        self.model = None
        self.tokenizer = None
        self.device: str = "cpu"

    def load(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if torch.backends.mps.is_available():
            self.device = "mps"
            dtype = torch.float16
        elif torch.cuda.is_available():
            self.device = "cuda"
            dtype = torch.float16
        else:
            self.device = "cpu"
            dtype = torch.float32

        # _model_source may do the one-time merge+save, so call it once
        src = self._model_source()

        self.tokenizer = AutoTokenizer.from_pretrained(src, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        logger.info(f"Loading model from '{src}' on {self.device} ({dtype})")
        self.model = AutoModelForCausalLM.from_pretrained(
            src,
            dtype=dtype,
            device_map=self.device,
            trust_remote_code=True,
        )
        self.model.eval()
        logger.info("Model ready")

    @staticmethod
    def _model_source() -> str:
        """Return path to the merged fine-tuned model, or the base HF id.

        Priority:
          1. Merged model on disk  (~/.local/share/zsh-autocomplete/merged-model)
             → instant load, no merge step needed
          2. LoRA adapter exists   (~/.local/share/zsh-autocomplete/lora-adapter)
             → load base + apply adapter + merge + save merged to disk for next time
          3. Base model only       (Qwen/Qwen2.5-0.5B-Instruct from HF cache)
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        # Fast path: merged model already on disk
        if (MERGED_DIR / "config.json").exists():
            logger.info(f"Loading merged fine-tuned model from {MERGED_DIR}")
            return str(MERGED_DIR)

        # Slow path: adapter exists — merge and cache
        adapter_cfg = ADAPTER_DIR / "adapter_config.json"
        if adapter_cfg.exists():
            logger.info(f"First run after fine-tuning: merging LoRA adapter into base model...")
            logger.info("This takes ~30 s and is only done once.")

            if torch.backends.mps.is_available():
                dtype = torch.float16
            elif torch.cuda.is_available():
                dtype = torch.float16
            else:
                dtype = torch.float32

            from peft import PeftModel
            tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
            base = AutoModelForCausalLM.from_pretrained(
                MODEL_ID, dtype=dtype, device_map="cpu", trust_remote_code=True
            )
            merged = PeftModel.from_pretrained(base, str(ADAPTER_DIR))
            merged = merged.merge_and_unload()

            MERGED_DIR.mkdir(parents=True, exist_ok=True)
            merged.save_pretrained(str(MERGED_DIR))
            tokenizer.save_pretrained(str(MERGED_DIR))
            logger.info(f"Merged model saved to {MERGED_DIR} — future starts will be fast")
            return str(MERGED_DIR)

        # No adapter yet
        logger.info(f"No LoRA adapter found — using base {MODEL_ID}. Run ai-setup to fine-tune.")
        return MODEL_ID

    def complete(self, input_text: str) -> str:
        import torch

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Complete: {input_text}"},
        ]

        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        input_len = inputs["input_ids"].shape[1]

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=60,
                do_sample=False,            # greedy = deterministic, fast
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        new_tokens = output_ids[0][input_len:]
        completion = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        # Strip stop tokens the model might include inline
        for stop in ("\n", ";", " &&", " ||", " #"):
            if stop in completion:
                completion = completion[: completion.index(stop)]
        completion = completion.strip()

        # Ensure completion extends the input (model sometimes returns only suffix)
        if completion and not completion.startswith(input_text):
            completion = input_text + completion.lstrip()

        return completion if completion != input_text else ""


_backend = _ModelBackend()


# ---------------------------------------------------------------------------
# Daemon
# ---------------------------------------------------------------------------

class AutocompleteDaemon:
    def __init__(self) -> None:
        self._pending_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        loop = asyncio.get_running_loop()

        # Load model in thread so the event loop stays responsive
        logger.info("Starting model load...")
        await loop.run_in_executor(None, _backend.load)

        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)

        server = await asyncio.start_unix_server(
            self._handle, path=str(SOCKET_PATH)
        )
        logger.info(f"Listening on {SOCKET_PATH}")
        async with server:
            await server.serve_forever()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            raw = await asyncio.wait_for(reader.read(8192), timeout=2)
            req = json.loads(raw.decode())
            req_id = req.get("id", "")
            inp = req.get("input", "").strip()

            completion = await self._fetch(inp)

            writer.write(json.dumps({"id": req_id, "completion": completion}).encode())
            await writer.drain()
        except (asyncio.TimeoutError, json.JSONDecodeError):
            pass
        except Exception as e:
            logger.error(f"Handle error: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _fetch(self, inp: str) -> str:
        """Cancel any pending request, start a new one."""
        async with self._lock:
            if self._pending_task and not self._pending_task.done():
                self._pending_task.cancel()
                try:
                    await self._pending_task
                except (asyncio.CancelledError, Exception):
                    pass
            task = asyncio.create_task(self._complete(inp))
            self._pending_task = task

        try:
            return await task
        except asyncio.CancelledError:
            return ""
        except Exception as e:
            logger.error(f"Completion error: {e}")
            return ""

    @staticmethod
    async def _complete(inp: str) -> str:
        if not inp:
            return ""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _backend.complete, inp)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()))

    def _shutdown(sig, _):
        logger.info(f"Signal {sig} — shutting down")
        for p in (SOCKET_PATH, PID_PATH):
            try:
                p.unlink()
            except FileNotFoundError:
                pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        asyncio.run(AutocompleteDaemon().start())
    except KeyboardInterrupt:
        pass
    finally:
        for p in (SOCKET_PATH, PID_PATH):
            try:
                p.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    main()
