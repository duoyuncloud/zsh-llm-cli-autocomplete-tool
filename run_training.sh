#!/usr/bin/env bash
# Run LoRA training with CPU-only (no MPS) to avoid OOM on Apple Silicon.
# Usage: ./run_training.sh [extra args for trainer]
# Example: ./run_training.sh --epochs 3

set -e
cd "$(dirname "$0")"

export PYTORCH_MPS_DISABLE=1
export AXOLOTL_DO_NOT_TRACK=1

echo "Env: PYTORCH_MPS_DISABLE=1 (CPU only), AXOLOTL_DO_NOT_TRACK=1"
echo ""

PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}" \
venv/bin/python -m training.qwen3_axolotl_trainer \
  --base-model "${BASE_MODEL_ID:-Qwen/Qwen2.5-1.5B-Instruct}" \
  --epochs 2 \
  --low-memory \
  "$@"
