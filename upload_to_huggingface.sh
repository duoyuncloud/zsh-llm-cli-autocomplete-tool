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
DEFAULT_TRAINED_ADAPTER="zsh-lora-output"
DEFAULT_INSTALLED_ADAPTER="$HOME/.local/share/zsh-autocomplete/lora-adapter"
ADAPTER_PATH="${ADAPTER_DIR:-$DEFAULT_TRAINED_ADAPTER}"
MODEL_CARD_PATH="${MODEL_CARD_PATH:-docs/HF_MODEL_CARD.md}"
BASE_MODEL="${BASE_MODEL_ID:-}"

if [[ "$REPO_ID" == *"HF_USERNAME_PLACEHOLDER"* ]]; then
  echo "Set Hugging Face repository id before uploading:"
  echo "  export HF_REPO_ID=HF_USERNAME_PLACEHOLDER/zsh-autocomplete-lora"
  echo "Then run: ./upload_to_huggingface.sh"
  exit 1
fi

# Auto-fallback to installed adapter if training output is absent.
if [[ ! -d "$ADAPTER_PATH" ]]; then
  if [[ "$ADAPTER_PATH" == "$DEFAULT_TRAINED_ADAPTER" && -d "$DEFAULT_INSTALLED_ADAPTER" ]]; then
    ADAPTER_PATH="$DEFAULT_INSTALLED_ADAPTER"
  else
    echo "❌ Adapter directory not found: $(pwd)/$ADAPTER_PATH"
    echo "   Set ADAPTER_DIR=/path/to/adapter and retry."
    exit 1
  fi
fi

ADAPTER_CFG="$ADAPTER_PATH/adapter_config.json"
if [[ -z "$BASE_MODEL" && -f "$ADAPTER_CFG" ]]; then
  BASE_MODEL="$(python3 - <<PYEOF
import json
from pathlib import Path
cfg = Path(r"$ADAPTER_CFG")
try:
    data = json.loads(cfg.read_text())
    print(data.get("base_model_name_or_path", "").strip())
except Exception:
    print("")
PYEOF
)"
fi
BASE_MODEL="${BASE_MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"

UPLOAD_DIR="$ADAPTER_PATH"
if [[ -f "$MODEL_CARD_PATH" ]]; then
  TMP_UPLOAD_DIR="$(mktemp -d)"
  cp -R "$ADAPTER_PATH"/. "$TMP_UPLOAD_DIR"/
  cp "$MODEL_CARD_PATH" "$TMP_UPLOAD_DIR/README.md"
  UPLOAD_DIR="$TMP_UPLOAD_DIR"
  trap 'rm -rf "$TMP_UPLOAD_DIR"' EXIT
fi

echo "Uploading adapter to https://huggingface.co/$REPO_ID"
echo "Adapter path: $ADAPTER_PATH"
if [[ -f "$MODEL_CARD_PATH" ]]; then
  echo "Model card : $MODEL_CARD_PATH (will upload as README.md)"
fi
echo "Base model  : $BASE_MODEL"

PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}" \
venv/bin/python -m training.upload_to_hf \
  --adapter "$UPLOAD_DIR" \
  --repo-id "$REPO_ID" \
  --base-model "$BASE_MODEL" \
  "$@"

echo "Upload completed."
