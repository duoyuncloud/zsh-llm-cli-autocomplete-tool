#!/usr/bin/env python3
"""
Test the trained LoRA adapter to verify it works correctly.
"""

import os
import sys
import json
from pathlib import Path

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

def test_adapter(adapter_path: str, base_model: str = "distilgpt2"):
    """Test a trained LoRA adapter."""
    if not TRANSFORMERS_AVAILABLE:
        print("❌ transformers and peft not available")
        print("💡 Install with: pip install transformers peft torch")
        return False
    
    adapter_dir = Path(adapter_path)
    if not adapter_dir.exists():
        print(f"❌ Adapter directory not found: {adapter_path}")
        return False
    
    print(f"🧪 Testing LoRA adapter: {adapter_path}")
    print(f"📦 Base model: {base_model}")
    print("-" * 50)
    
    try:
        # Load base model
        print("📥 Loading base model...")
        base_model_obj = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=torch.float32,
            device_map="auto" if torch.cuda.is_available() else None
        )
        
        # Load tokenizer
        print("📥 Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Load LoRA adapter
        print("📥 Loading LoRA adapter...")
        model = PeftModel.from_pretrained(base_model_obj, adapter_path)
        model.eval()
        
        print("✅ Model loaded successfully")
        print("-" * 50)
        
        # Test cases
        test_cases = [
            "Input: git comm\nOutput:",
            "Input: docker run\nOutput:",
            "Input: npm run\nOutput:",
            "Input: python -m\nOutput:",
            "Input: kubectl get\nOutput:",
        ]
        
        print("🧪 Running test cases...")
        print()
        
        for i, test_input in enumerate(test_cases, 1):
            print(f"Test {i}: {test_input.split('Input:')[1].split('Output:')[0].strip()}")
            
            inputs = tokenizer(test_input, return_tensors="pt")
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=50,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=tokenizer.eos_token_id,
                    num_return_sequences=1
                )
            
            result = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract the output part
            if "Output:" in result:
                output_part = result.split("Output:")[-1].strip()
                print(f"   Result: {output_part[:100]}")
            else:
                print(f"   Result: {result[-100:]}")
            print()
        
        print("✅ All tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test trained LoRA adapter')
    parser.add_argument('--adapter', '-a', 
                       default='zsh-lora-output',
                       help='Path to adapter directory')
    parser.add_argument('--base-model', '-b',
                       default='distilgpt2',
                       help='Base model name')
    
    args = parser.parse_args()
    
    # Resolve adapter path
    adapter_path = Path(args.adapter)
    if not adapter_path.is_absolute():
        # Try relative to project root
        project_root = Path(__file__).parent.parent.parent
        adapter_path = project_root / adapter_path
    
    success = test_adapter(str(adapter_path), args.base_model)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
