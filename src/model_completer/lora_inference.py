#!/usr/bin/env python3
"""
Direct inference using the fine-tuned LoRA model.
This allows using the trained model without requiring Ollama.
"""

import os
import logging
import torch
from pathlib import Path
from typing import Optional, Dict, Any
import time

logger = logging.getLogger(__name__)

# Try to import required libraries
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class LoRAInference:
    """Direct inference using fine-tuned LoRA model."""
    
    _model = None
    _tokenizer = None
    _base_model_name = None
    _lora_path = None
    _last_access = None
    _model_loaded = False
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if LoRA inference is available."""
        if not TRANSFORMERS_AVAILABLE:
            return False
        
        # Check if LoRA model exists
        base_dir = Path(__file__).parent.parent.parent
        lora_path = base_dir / "zsh-lora-output"
        
        if not lora_path.exists():
            return False
        
        # Check for required files
        required_files = ["adapter_config.json", "adapter_model.safetensors"]
        for file in required_files:
            if not (lora_path / file).exists():
                return False
        
        return True
    
    @classmethod
    def get_lora_path(cls) -> Optional[Path]:
        """Get path to LoRA model."""
        base_dir = Path(__file__).parent.parent.parent
        lora_path = base_dir / "zsh-lora-output"
        if lora_path.exists():
            return lora_path
        return None
    
    @classmethod
    def load_model(cls, force_reload: bool = False) -> bool:
        """Load the LoRA model for inference."""
        if cls._model_loaded and not force_reload:
            cls._last_access = time.time()
            return True
        
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Transformers not available for LoRA inference")
            return False
        
        lora_path = cls.get_lora_path()
        if not lora_path:
            logger.warning("LoRA model not found")
            return False
        
        try:
            # Load adapter config to get base model
            import json
            config_file = lora_path / "adapter_config.json"
            with open(config_file) as f:
                adapter_config = json.load(f)
            
            base_model_name = adapter_config.get("base_model_name_or_path", "distilgpt2")
            
            logger.info(f"Loading LoRA model from {lora_path}")
            logger.info(f"Base model: {base_model_name}")
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(str(lora_path))
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # Load base model
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                dtype=torch.float32,
                device_map="cpu",  # Use CPU for compatibility
                low_cpu_mem_usage=True
            )
            
            # Load LoRA weights
            model = PeftModel.from_pretrained(base_model, str(lora_path))
            model.eval()  # Set to evaluation mode
            
            # Store loaded model
            cls._model = model
            cls._tokenizer = tokenizer
            cls._base_model_name = base_model_name
            cls._lora_path = lora_path
            cls._model_loaded = True
            cls._last_access = time.time()
            
            logger.info("LoRA model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load LoRA model: {e}")
            cls._model_loaded = False
            return False
    
    @classmethod
    def generate_completion(cls, prompt: str, max_length: int = 100, 
                           temperature: float = 0.7) -> Optional[str]:
        """Generate completion using LoRA model."""
        if not cls._model_loaded:
            if not cls.load_model():
                return None
        
        try:
            # Format prompt for command completion
            formatted_prompt = f"{prompt}"
            
            # Tokenize
            inputs = cls._tokenizer(
                formatted_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=512
            )
            
            # Generate
            with torch.no_grad():
                outputs = cls._model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=temperature,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=cls._tokenizer.eos_token_id,
                    eos_token_id=cls._tokenizer.eos_token_id
                )
            
            # Decode
            generated_text = cls._tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract completion (remove prompt)
            if generated_text.startswith(prompt):
                completion = generated_text[len(prompt):].strip()
            else:
                completion = generated_text.strip()
            
            # Clean up the completion
            completion = cls._clean_completion(completion, prompt)
            
            cls._last_access = time.time()
            return completion
            
        except Exception as e:
            logger.error(f"LoRA inference error: {e}")
            return None
    
    @classmethod
    def _clean_completion(cls, completion: str, original_prompt: str) -> str:
        """Clean up the completion to return just the command."""
        # Remove common prefixes and explanations
        lines = completion.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip explanatory text
            if any(word in line.lower() for word in [
                'input:', 'output:', 'complete:', 'command:', 'here', 'sure',
                'you can', 'this will', 'to complete', 'note:', 'example:'
            ]):
                continue
            
            # Skip lines that are too short or don't look like commands
            if len(line) < len(original_prompt) + 2:
                continue
            
            # If it starts with the original prompt, extract the rest
            if line.startswith(original_prompt):
                result = line[len(original_prompt):].strip()
                if result and len(result) > 1:
                    return original_prompt + result
            
            # If it's a complete new command, return it
            if ' ' in line and not line.startswith(('$', '`', '#', '//')):
                # Check if it's a command (starts with letter and has space)
                if line[0].isalpha() and len(line.split()) >= 2:
                    return line
        
        # If nothing found, try to extract from the raw completion
        # Remove markdown code blocks
        completion = completion.replace('```', '').strip()
        # Get first line that looks like a command
        for line in completion.split('\n'):
            line = line.strip()
            if line and len(line) > len(original_prompt) and ' ' in line:
                if line.startswith(original_prompt):
                    return line
                elif line[0].isalpha():
                    return line
        
        # Fallback: return cleaned version of completion
        return completion.strip()[:200]
    
    @classmethod
    def unload_model(cls):
        """Unload the model to free memory."""
        cls._model = None
        cls._tokenizer = None
        cls._model_loaded = False
        logger.info("LoRA model unloaded")


def is_lora_ready() -> bool:
    """Check if LoRA model is ready for use."""
    return LoRAInference.is_available()


def ensure_lora_ready() -> bool:
    """Ensure LoRA model is loaded and ready."""
    if not LoRAInference.is_available():
        return False
    
    if not LoRAInference._model_loaded:
        return LoRAInference.load_model()
    
    return True


def get_lora_completion(prompt: str, **kwargs) -> Optional[str]:
    """Get completion from LoRA model."""
    if not ensure_lora_ready():
        return None
    return LoRAInference.generate_completion(prompt, **kwargs)

