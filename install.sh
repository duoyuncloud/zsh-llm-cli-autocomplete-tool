#!/usr/bin/env bash
# zsh-autocomplete — one-time install
#
# 1. Creates a venv and installs dependencies
# 2. Downloads the pre-trained LoRA adapter from HuggingFace
# 3. Merges the adapter into its base model (one-time, ~60s)
# 4. Adds the plugin to ~/.zshrc and starts the daemon

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN="$DIR/src/scripts/zsh_autocomplete.plugin.zsh"
HF_REPO="duoyuncloud/zsh-autocomplete-lora"
ADAPTER_DIR="$HOME/.local/share/zsh-autocomplete/lora-adapter"
MERGED_DIR="$HOME/.local/share/zsh-autocomplete/merged-model"

# ---------------------------------------------------------------------------
# 1. Python
# ---------------------------------------------------------------------------

if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found. Install Python 3.10+ and retry." >&2
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(sys.version_info.minor)')
if (( PY_VER < 10 )); then
    echo "Error: Python 3.10+ required (found 3.$PY_VER)" >&2
    exit 1
fi

echo "[1/4] Setting up virtual environment..."
if [[ ! -d "$DIR/venv" ]]; then
    python3 -m venv "$DIR/venv"
fi
source "$DIR/venv/bin/activate"
PY="$DIR/venv/bin/python3"

# ---------------------------------------------------------------------------
# 2. Dependencies
# ---------------------------------------------------------------------------

echo "[2/4] Installing dependencies..."
"$PY" -m pip install -q --upgrade pip
"$PY" -m pip install -q -r "$DIR/requirements.txt"
"$PY" -m pip install -q \
    torch transformers peft sentencepiece huggingface_hub protobuf

# ---------------------------------------------------------------------------
# 3. Download pre-trained adapter from HuggingFace
# ---------------------------------------------------------------------------

echo "[3/4] Downloading pre-trained LoRA adapter from HuggingFace..."
echo "      (repo: $HF_REPO)"
"$PY" - <<PYEOF
from huggingface_hub import snapshot_download
import socket
import os

def hf_reachable(host: str = "huggingface.co", port: int = 443, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

adapter_dir = os.path.expanduser("$ADAPTER_DIR")
os.makedirs(adapter_dir, exist_ok=True)

# Prefer local cache first so offline installs still work if previously downloaded.
try:
    snapshot_download(
        repo_id="$HF_REPO",
        local_dir=adapter_dir,
        local_files_only=True,
    )
    print(f"      Adapter already cached at {adapter_dir}")
except Exception:
    if not hf_reachable():
        raise SystemExit(
            "      ERROR: huggingface.co unreachable and adapter not in local cache.\n"
            "      Retry on a network that can reach Hugging Face."
        )
    snapshot_download(
        repo_id="$HF_REPO",
        local_dir=adapter_dir,
    )
    print(f"      Adapter saved to {adapter_dir}")
PYEOF

# ---------------------------------------------------------------------------
# 4. Merge adapter into base model
# ---------------------------------------------------------------------------

echo "[4/4] Merging LoRA adapter into its base model..."
echo "      Downloads base model on first run; merge takes ~60s."
"$PY" - <<PYEOF
import torch
import json
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import socket

ADAPTER  = Path.home() / ".local/share/zsh-autocomplete/lora-adapter"
MERGED   = Path.home() / ".local/share/zsh-autocomplete/merged-model"

def hf_reachable(host: str = "huggingface.co", port: int = 443, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

adapter_cfg = ADAPTER / "adapter_config.json"
if not adapter_cfg.exists():
    raise SystemExit(f"adapter_config.json not found in {ADAPTER}")
cfg = json.loads(adapter_cfg.read_text())
MODEL_ID = cfg.get("base_model_name_or_path", "Qwen/Qwen2.5-1.5B-Instruct")
print(f"      Adapter base model: {MODEL_ID}")

if MERGED.exists() and (MERGED / "config.json").exists():
    print("      Merged model already exists, skipping.")
else:
    dtype = torch.float16 if (
        torch.backends.mps.is_available() or torch.cuda.is_available()
    ) else torch.float32
    print("      Loading base model...")
    # Prefer local cache first; fallback to network only if HF is reachable.
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID, trust_remote_code=True, local_files_only=True
        )
        base = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=dtype,
            device_map="cpu",
            trust_remote_code=True,
            local_files_only=True,
        )
    except Exception:
        if not hf_reachable():
            raise SystemExit(
                "      ERROR: base model not cached and huggingface.co unreachable.\n"
                "      Re-run install on a network that can access Hugging Face."
            )
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
        base = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, torch_dtype=dtype, device_map="cpu", trust_remote_code=True
        )
    print("      Applying LoRA adapter...")
    merged = PeftModel.from_pretrained(base, str(ADAPTER)).merge_and_unload()
    MERGED.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(MERGED))
    tokenizer.save_pretrained(str(MERGED))
    print(f"      Merged model saved to {MERGED}")
PYEOF

# ---------------------------------------------------------------------------
# 5. Add plugin to ~/.zshrc and start daemon
# ---------------------------------------------------------------------------

ZSHRC="${ZDOTDIR:-$HOME}/.zshrc"
if grep -qF "zsh_autocomplete.plugin.zsh" "$ZSHRC" 2>/dev/null; then
    if grep -qF "ZSH_AUTOCOMPLETE_DIR=\"$DIR\"" "$ZSHRC" 2>/dev/null; then
        echo "      Already in $ZSHRC"
    else
        # Stale entry — replace it
        sed -i.bak \
            -e '/# zsh-autocomplete/d' \
            -e '/ZSH_AUTOCOMPLETE_DIR=/d' \
            -e '/zsh_autocomplete.plugin.zsh/d' \
            "$ZSHRC"
        printf '\n# zsh-autocomplete\nexport ZSH_AUTOCOMPLETE_DIR="%s"\nsource "%s"\n' \
            "$DIR" "$PLUGIN" >> "$ZSHRC"
        echo "      Updated path in $ZSHRC"
    fi
else
    printf '\n# zsh-autocomplete\nexport ZSH_AUTOCOMPLETE_DIR="%s"\nsource "%s"\n' \
        "$DIR" "$PLUGIN" >> "$ZSHRC"
    echo "      Added to $ZSHRC"
fi

echo "      Starting autocomplete daemon..."
pkill -f autocomplete_daemon.py 2>/dev/null || true
sleep 0.3
PYTHONPATH="$DIR/src${PYTHONPATH:+:$PYTHONPATH}" nohup "$PY" -m model_completer.daemon \
    >> "$HOME/.cache/zsh-autocomplete.log" 2>&1 &
disown

# ---------------------------------------------------------------------------

echo ""
echo "Done. Reload your shell:"
echo "  source ~/.zshrc"
echo ""
echo "Then start typing, grey completions will appear after your cursor."
echo "Press Shift+. (>) to accept ghost suggestions."
