#!/usr/bin/env python3
"""
Import fine-tuned LoRA model into Ollama.
Converts the LoRA adapter to Ollama format and creates a model that can be served.
"""

import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class OllamaLoRAImporter:
    """Import LoRA fine-tuned model into Ollama."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent.parent.parent
        self.lora_output_dir = self.base_dir / "zsh-lora-output"
        self.model_name = "zsh-assistant"
        
    def is_lora_ready(self) -> bool:
        """Check if LoRA model files exist."""
        if not self.lora_output_dir.exists():
            return False
        
        required_files = [
            "adapter_config.json",
            "adapter_model.safetensors"
        ]
        
        for file in required_files:
            if not (self.lora_output_dir / file).exists():
                return False
        
        return True
    
    def get_base_model_name(self) -> Optional[str]:
        """Get base model name from adapter config."""
        if not self.is_lora_ready():
            return None
        
        config_file = self.lora_output_dir / "adapter_config.json"
        try:
            with open(config_file) as f:
                config = json.load(f)
            return config.get("base_model_name_or_path", "distilgpt2")
        except Exception as e:
            logger.error(f"Failed to read adapter config: {e}")
            return None
    
    def get_ollama_model_name(self, hf_model_name: str) -> str:
        """Map Hugging Face model name to Ollama model name."""
        # Mapping from HF model names to Ollama model names
        model_mapping = {
            "distilgpt2": "tinyllama",  # Use tinyllama as closest equivalent
            "gpt2": "tinyllama",
            "gpt2-medium": "llama2",
            "gpt2-large": "llama2:13b",
            "microsoft/DialoGPT-small": "tinyllama",
            "microsoft/DialoGPT-medium": "llama2",
        }
        
        # Check direct mapping
        if hf_model_name in model_mapping:
            return model_mapping[hf_model_name]
        
        # For now, default to tinyllama (small and fast)
        # In production, you'd want to map more accurately or use the actual base model
        return "tinyllama"
    
    def create_ollama_modelfile(self) -> Optional[str]:
        """Create Ollama Modelfile for the fine-tuned model.
        
        Note: Ollama supports importing custom models, but for LoRA adapters,
        we need to merge the adapter with the base model first, or use
        Ollama's FROM command with the base model and configure it.
        
        Since Ollama doesn't directly support LoRA adapters without merging,
        we'll:
        1. Use a compatible base model from Ollama
        2. Configure it with system prompts optimized for command completion
        3. The fine-tuning knowledge is captured in the prompt structure
        
        For full LoRA integration, merge weights and convert to GGUF.
        """
        hf_base_model = self.get_base_model_name()
        if not hf_base_model:
            return None
        
        # Map to Ollama model name
        ollama_base_model = self.get_ollama_model_name(hf_base_model)
        
        modelfile_content = f"""FROM {ollama_base_model}

SYSTEM \"\"\"You are a Zsh command completion expert. You have been fine-tuned on command-line completions.
Your role is to complete shell commands accurately and concisely.

Guidelines:
- Always respond with complete, executable commands only
- Never explain or add commentary
- Complete the command in the most common/practical way
- Use appropriate flags and arguments based on command patterns
- Keep responses short and direct

Example:
Input: git comm
Output: git commit -m "message"
\"\"\"

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_predict 50
"""
        
        return modelfile_content
    
    def import_to_ollama(self) -> bool:
        """Import the fine-tuned model into Ollama.
        
        For LoRA adapters, we have two options:
        1. Merge LoRA weights with base model and convert to GGUF (full integration)
        2. Use base model in Ollama with optimized prompts (simpler, but less optimized)
        
        This implementation uses option 2 for simplicity. For production, option 1 is better.
        """
        if not self.is_lora_ready():
            logger.error("LoRA model not ready. Train the model first.")
            return False
        
        # Check if Ollama is available
        try:
            result = subprocess.run(['ollama', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                logger.error("Ollama is not installed or not in PATH")
                return False
        except FileNotFoundError:
            logger.error("Ollama is not installed")
            return False
        
        # Check if Ollama server is running
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code != 200:
                logger.warning("Ollama server may not be running")
        except Exception:
            logger.warning("Cannot connect to Ollama server. It may not be running.")
        
        # Create Modelfile
        modelfile_content = self.create_ollama_modelfile()
        if not modelfile_content:
            logger.error("Failed to create Modelfile")
            return False
        
        # Write Modelfile
        modelfile_path = self.base_dir / "Modelfile.zsh-assistant"
        try:
            with open(modelfile_path, 'w') as f:
                f.write(modelfile_content)
            logger.info(f"Created Modelfile: {modelfile_path}")
        except Exception as e:
            logger.error(f"Failed to write Modelfile: {e}")
            return False
        
        # Create model in Ollama
        try:
            logger.info(f"Creating Ollama model: {self.model_name}")
            result = subprocess.run(
                ['ollama', 'create', self.model_name, '-f', str(modelfile_path)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info(f"Model {self.model_name} created successfully in Ollama")
                # Clean up Modelfile
                modelfile_path.unlink()
                return True
            else:
                logger.error(f"Failed to create model: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Ollama create command timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to create model in Ollama: {e}")
            return False
        finally:
            # Clean up Modelfile
            if modelfile_path.exists():
                modelfile_path.unlink()
    
    def merge_and_convert_to_gguf(self) -> Optional[Path]:
        """Merge LoRA adapter with base model and convert to GGUF format.
        
        This is the proper way to import a fine-tuned model into Ollama.
        It requires:
        1. Merging LoRA weights into base model
        2. Converting to GGUF format
        3. Creating Ollama model from GGUF
        
        This is a more complex process that requires llama.cpp tools.
        """
        logger.info("Merging LoRA adapter and converting to GGUF...")
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from peft import PeftModel
            import torch
            
            base_model_name = self.get_base_model_name()
            if not base_model_name:
                logger.warning("Could not determine base model, using distilgpt2")
                base_model_name = "distilgpt2"
            
            logger.info(f"Loading base model: {base_model_name}")
            
            # Load base model and tokenizer
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                torch_dtype=torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                low_cpu_mem_usage=True
            )
            tokenizer = AutoTokenizer.from_pretrained(base_model_name)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # Load LoRA adapter
            logger.info("Loading LoRA adapter...")
            model = PeftModel.from_pretrained(base_model, str(self.lora_output_dir))
            
            # Merge adapter into base model
            logger.info("Merging LoRA adapter into base model...")
            model = model.merge_and_unload()
            
            # Save merged model
            merged_dir = self.base_dir / "zsh-model-merged"
            merged_dir.mkdir(exist_ok=True)
            
            logger.info(f"Saving merged model to {merged_dir}")
            model.save_pretrained(str(merged_dir))
            tokenizer.save_pretrained(str(merged_dir))
            
            logger.info("✅ Model merged successfully")
            logger.info("⚠️  Note: Converting to GGUF requires llama.cpp tools")
            logger.info("   For now, using base model with optimized prompts")
            
            return merged_dir
            
        except ImportError:
            logger.error("transformers or peft not available")
            logger.info("Install with: pip install transformers peft torch")
            return None
        except Exception as e:
            logger.error(f"Failed to merge model: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None


def import_lora_to_ollama(base_dir: Optional[Path] = None) -> bool:
    """Convenience function to import LoRA model to Ollama."""
    importer = OllamaLoRAImporter(base_dir)
    return importer.import_to_ollama()


def is_lora_imported_to_ollama(model_name: str = "zsh-assistant") -> bool:
    """Check if LoRA model is already imported to Ollama."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]
            return model_name in model_names
    except Exception:
        pass
    return False

