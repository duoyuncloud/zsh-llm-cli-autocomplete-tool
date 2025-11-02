#!/usr/bin/env python3
"""
Preload LoRA model on terminal startup.
This ensures the fine-tuned model is ready when needed.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from model_completer.lora_inference import ensure_lora_ready, is_lora_ready
    
    if is_lora_ready():
        # Preload the model
        if ensure_lora_ready():
            print("✅ Fine-tuned LoRA model ready", end='')
            sys.exit(0)
        else:
            print("⚠️  LoRA model found but failed to load", end='')
            sys.exit(1)
    else:
        print("ℹ️  LoRA model not found", end='')
        sys.exit(0)
except Exception as e:
    # Silent failure - don't break terminal startup
    sys.exit(0)

