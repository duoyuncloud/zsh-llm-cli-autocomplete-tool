#!/usr/bin/env bash
# Upload a trained LoRA adapter to Hugging Face.
#
# Steps:
# 1) Authenticate once: huggingface-cli login
# 2) Set repository placeholder values below (or export env vars)
# 3) Run: ./upload_to_huggingface.sh

set -euo pipefail
cd "$(dirname "$0")"

REPO_ID="${HF_REPO_ID:-HF_USERNAME_PLACEHOLDER/zsh-autocomplete-lora}"
ADAPTER_PATH="${ADAPTER_DIR:-zsh-lora-output}"
BASE_MODEL="${BASE_MODEL_ID:-Qwen/Qwen2.5-1.5B-Instruct}"

if [[ "$REPO_ID" == *"HF_USERNAME_PLACEHOLDER"* ]]; then
  echo "Set Hugging Face repository id before uploading:"
  echo "  export HF_REPO_ID=HF_USERNAME_PLACEHOLDER/zsh-autocomplete-lora"
  echo "Then run: ./upload_to_huggingface.sh"
  exit 1
fi

echo "Uploading adapter to https://huggingface.co/$REPO_ID"
echo "Adapter path: $ADAPTER_PATH"
echo "Base model  : $BASE_MODEL"

PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}" \
venv/bin/python -m training.upload_to_hf \
  --adapter "$ADAPTER_PATH" \
  --repo-id "$REPO_ID" \
  --base-model "$BASE_MODEL" \
  "$@"

echo "Upload completed."
