#!/usr/bin/env python3
"""Upload the trained LoRA adapter to HuggingFace.

Run after fine-tuning completes:
    python src/training/upload_adapter_to_hf.py

Requires HF_TOKEN env var or `huggingface-cli login` to be done first.
Uploads to: duoyuncloud/zsh-autocomplete-lora
"""

import os
import sys
from pathlib import Path

ADAPTER_DIR = Path.home() / ".local/share/zsh-autocomplete/lora-adapter"
HF_REPO     = "duoyuncloud/zsh-autocomplete-lora"


def main() -> None:
    if not ADAPTER_DIR.exists() or not (ADAPTER_DIR / "adapter_config.json").exists():
        print(f"Error: adapter not found at {ADAPTER_DIR}", file=sys.stderr)
        print("Run fine-tuning first: python src/training/finetune_small_model.py")
        sys.exit(1)

    # Verify base model in adapter config
    import json
    cfg = json.loads((ADAPTER_DIR / "adapter_config.json").read_text())
    base = cfg.get("base_model_name_or_path", "")
    if "1.5B" not in base and "1.5b" not in base:
        print(f"Warning: adapter base model is '{base}', expected Qwen2.5-1.5B-Instruct")
        if input("Continue anyway? [y/N] ").strip().lower() != "y":
            sys.exit(1)

    from huggingface_hub import HfApi
    api = HfApi()

    # Create repo if it doesn't exist
    try:
        api.repo_info(repo_id=HF_REPO)
        print(f"Repo {HF_REPO} exists, uploading...")
    except Exception:
        print(f"Creating repo {HF_REPO}...")
        api.create_repo(repo_id=HF_REPO, exist_ok=True)

    print(f"Uploading adapter from {ADAPTER_DIR} to {HF_REPO}...")
    api.upload_folder(
        folder_path=str(ADAPTER_DIR),
        repo_id=HF_REPO,
        commit_message=f"Update LoRA adapter: Qwen2.5-1.5B-Instruct base",
    )
    print(f"\nDone. Adapter uploaded to https://huggingface.co/{HF_REPO}")
    print("\nUsers can now install with:")
    print("  ./install.sh")


if __name__ == "__main__":
    main()
