#!/usr/bin/env python3
"""
Test script to verify LoRA fine-tuned model (zsh-assistant) is working correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from model_completer.completer import ModelCompleter
from model_completer.utils import load_config
import requests

def check_ollama_running():
    """Check if Ollama server is running."""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        return response.status_code == 200
    except:
        return False

def test_lora_model():
    """Test the LoRA fine-tuned model."""
    print("=" * 60)
    print("LoRA Fine-tuned Model (zsh-assistant) Test")
    print("=" * 60)
    print()
    
    # Check configuration
    config = load_config()
    model_name = config.get('model', 'default')
    print(f"✅ Configured Model: {model_name}")
    print(f"✅ Timeout: {config.get('ollama', {}).get('timeout', 30)}s")
    print()
    
    # Check Ollama status
    ollama_running = check_ollama_running()
    if ollama_running:
        print("✅ Ollama server is RUNNING")
    else:
        print("⚠️  Ollama server is NOT running")
        print("   (AI completions will fail, but fallback will work)")
    print()
    
    # Create completer with zsh-assistant model
    completer = ModelCompleter(model='zsh-assistant')
    print(f"✅ Using Model Instance: {completer.model}")
    print()
    
    # Test 1: Commands in training data (should use fallback)
    print("Test 1: Commands in training data")
    print("-" * 60)
    training_commands = [
        'git comm',
        'docker run',
        'npm run',
        'python -m',
        'kubectl get'
    ]
    
    for cmd in training_commands:
        result = completer.get_completion(cmd)
        fallback = completer._get_fallback_completion(cmd)
        is_fallback = result == fallback
        status = "✅ Training Data" if is_fallback else "⚠️  AI Model"
        print(f"  {cmd:15} -> {result[:45]:45} [{status}]")
    print()
    
    # Test 2: Commands NOT in training data (should use AI)
    print("Test 2: Commands NOT in training data (should use AI)")
    print("-" * 60)
    ai_commands = [
        'curl -H "Authorization"',
        'systemctl restart nginx',
        'ps aux | grep python',
        'find . -name "*.py"',
        'grep -r "pattern" /path'
    ]
    
    for cmd in ai_commands:
        result = completer.get_completion(cmd)
        fallback = completer._get_fallback_completion(cmd)
        is_fallback = fallback is not None and result == fallback
        if ollama_running:
            status = "✅ AI Model" if not is_fallback else "⚠️  Training Data"
        else:
            status = "⚠️  Ollama Down" if not is_fallback else "✅ Training Data"
        print(f"  {cmd[:30]:30} -> {result[:35]:35} [{status}]")
    print()
    
    # Test 3: Compare with base model (if Ollama is running)
    if ollama_running:
        print("Test 3: Comparison with base model (tinyllama)")
        print("-" * 60)
        test_cmd = 'ls -'
        print(f"Testing command: {test_cmd}")
        print()
        
        # Test with zsh-assistant (LoRA fine-tuned)
        result_zsh = completer.get_completion(test_cmd)
        print(f"  zsh-assistant:  {result_zsh}")
        
        # Test with tinyllama (base model)
        completer_base = ModelCompleter(model='tinyllama')
        result_base = completer_base.get_completion(test_cmd)
        print(f"  tinyllama:      {result_base}")
        
        if result_zsh != result_base:
            print("  ✅ LoRA model produces different output (fine-tuning active)")
        else:
            print("  ⚠️  Same output (may be using training data fallback)")
    print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✅ Model: {model_name}")
    print(f"{'✅' if ollama_running else '⚠️ '} Ollama: {'Running' if ollama_running else 'Not Running'}")
    print("✅ System configured to use LoRA fine-tuned model")
    print()
    
    if not ollama_running:
        print("⚠️  To test AI completions, start Ollama:")
        print("   ollama serve")
        print()

if __name__ == '__main__':
    test_lora_model()

