#!/usr/bin/env python3
"""
Real LoRA training implementation using transformers and PEFT.
This provides actual LoRA fine-tuning without requiring Axolotl.
"""

import os
import json
import yaml
import torch
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import tempfile
import shutil

try:
    from transformers import (
        AutoTokenizer, AutoModelForCausalLM, 
        TrainingArguments, Trainer, DataCollatorForLanguageModeling
    )
    from peft import LoraConfig, get_peft_model, TaskType
    try:
        from datasets import Dataset
    except ImportError:
        Dataset = None  # Type hint only
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    Dataset = None

logger = logging.getLogger(__name__)

@dataclass
class LoRAConfig:
    """Configuration for LoRA training."""
    base_model: str = "Qwen/Qwen3-1.7B"  # Qwen3 1.7B quantized
    model_type: str = "AutoModelForCausalLM"
    tokenizer_type: str = "AutoTokenizer"
    
    # LoRA parameters
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.1
    lora_target_modules: List[str] = None
    
    # Training parameters
    max_length: int = 512
    batch_size: int = 1
    gradient_accumulation_steps: int = 4
    num_epochs: int = 3
    learning_rate: float = 2e-4
    warmup_steps: int = 100
    
    # Memory optimization
    fp16: bool = False  # Disable for compatibility
    load_in_4bit: bool = True  # Use 4-bit quantization for Qwen3-1.7B (auto-disabled on macOS if bitsandbytes < 0.43.1)
    load_in_8bit: bool = False
    gradient_checkpointing: bool = False  # Disable for compatibility
    
    def __post_init__(self):
        if self.lora_target_modules is None:
            # For Qwen models, use these target modules (similar to LLaMA)
            self.lora_target_modules = [
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj"
            ]

class RealLoRATrainer:
    """Real LoRA trainer using transformers and PEFT."""
    
    def __init__(self, config: Optional[LoRAConfig] = None):
        self.config = config or LoRAConfig()
        self.base_dir = Path(__file__).parent.parent.parent
        self.output_dir = self.base_dir / "zsh-lora-output"
        self.training_data_path = self.base_dir / "src" / "training" / "zsh_training_data.jsonl"
        
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        if not TRANSFORMERS_AVAILABLE:
            logger.error("Transformers and PEFT not available. Install with: pip install transformers peft")
            return False
        return True
    
    def prepare_data(self):
        """Prepare training data from JSONL file."""
        if not self.training_data_path.exists():
            logger.error(f"Training data not found: {self.training_data_path}")
            return None
        
        data = []
        with open(self.training_data_path, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        item = json.loads(line)
                        # Format for causal language modeling
                        text = f"Input: {item.get('input', '')}\nOutput: {item.get('output', '')}\n"
                        data.append({"text": text})
                    except json.JSONDecodeError:
                        continue
        
        if not data:
            logger.error("No valid training data found")
            return None
        
        logger.info(f"Prepared {len(data)} training examples")
        return Dataset.from_list(data)
    
    def setup_model_and_tokenizer(self):
        """Setup model and tokenizer for LoRA training."""
        logger.info(f"Loading model: {self.config.base_model}")
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.config.base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Load model with quantization
        import platform
        is_macos = platform.system() == "Darwin"
        is_apple_silicon = platform.machine() == "arm64"
        
        quantization_config = None
        if self.config.load_in_4bit or self.config.load_in_8bit:
            try:
                from transformers import BitsAndBytesConfig
                import bitsandbytes as bnb
                
                # Check if bitsandbytes supports this platform
                bnb_version = getattr(bnb, '__version__', '0.0.0')
                bnb_supports_apple = False
                try:
                    # Try to check if it's a version that supports Apple Silicon
                    from packaging import version
                    bnb_supports_apple = version.parse(bnb_version) >= version.parse("0.43.1")
                except:
                    # If packaging not available, try simple check
                    bnb_supports_apple = int(bnb_version.split('.')[0]) > 0 or (int(bnb_version.split('.')[0]) == 0 and int(bnb_version.split('.')[1]) >= 43)
                
                # On macOS/Apple Silicon, only use quantization if bitsandbytes >= 0.43.1
                if is_macos and is_apple_silicon and not bnb_supports_apple:
                    logger.warning(f"bitsandbytes {bnb_version} doesn't support Apple Silicon. Loading model without quantization.")
                    quantization_config = None
                elif self.config.load_in_4bit:
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                elif self.config.load_in_8bit:
                    quantization_config = BitsAndBytesConfig(load_in_8bit=True)
            except ImportError:
                logger.warning("bitsandbytes not available, loading model without quantization")
                quantization_config = None
            except Exception as e:
                logger.warning(f"Failed to setup quantization: {e}. Loading model without quantization.")
                quantization_config = None
        
        # Determine device and dtype
        if torch.cuda.is_available():
            device_map = "auto"
            torch_dtype = torch.float16
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            # Apple Silicon GPU (Metal Performance Shaders)
            device_map = None
            torch_dtype = torch.float16
            logger.info("Using Apple Silicon GPU (MPS)")
        else:
            # CPU fallback
            device_map = None
            torch_dtype = torch.float32
            logger.info("Using CPU (no quantization on CPU)")
            quantization_config = None  # Disable quantization on CPU
        
        load_kwargs = {
            "low_cpu_mem_usage": True,
            "trust_remote_code": True,
            "torch_dtype": torch_dtype,
        }
        
        if device_map:
            load_kwargs["device_map"] = device_map
        if quantization_config:
            load_kwargs["quantization_config"] = quantization_config
        
        model = AutoModelForCausalLM.from_pretrained(
            self.config.base_model,
            **load_kwargs
        )
        
        # Configure LoRA
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            target_modules=self.config.lora_target_modules,
        )
        
        # Apply LoRA to model
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()
        
        # Ensure model is in training mode
        model.train()
        
        # Verify that some parameters require gradients
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        logger.info(f"Trainable parameters: {trainable_params}")
        
        if trainable_params == 0:
            raise ValueError("No trainable parameters found. LoRA configuration may be incorrect.")
        
        return model, tokenizer
    
    def tokenize_data(self, dataset: Dataset, tokenizer) -> Dataset:
        """Tokenize the dataset."""
        def tokenize_function(examples):
            # Handle both single examples and batches
            if isinstance(examples["text"], list):
                texts = examples["text"]
            else:
                texts = [examples["text"]]
            
            return tokenizer(
                texts,
                truncation=True,
                padding=True,
                max_length=self.config.max_length,
                return_tensors=None  # Don't return tensors yet
            )
        
        return dataset.map(tokenize_function, batched=True, remove_columns=["text"])
    
    def train(self, data_file: str = None) -> bool:
        """Execute real LoRA training."""
        if not self.check_dependencies():
            return False
        
        logger.info("🚀 Starting real LoRA training...")
        
        # Prepare data
        dataset = self.prepare_data()
        if dataset is None:
            return False
        
        # Setup model and tokenizer
        model, tokenizer = self.setup_model_and_tokenizer()
        
        # Tokenize data
        tokenized_dataset = self.tokenize_data(dataset, tokenizer)
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            per_device_train_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            num_train_epochs=self.config.num_epochs,
            learning_rate=self.config.learning_rate,
            warmup_steps=self.config.warmup_steps,
            fp16=self.config.fp16,
            gradient_checkpointing=self.config.gradient_checkpointing,
            logging_steps=10,
            save_steps=500,
            save_total_limit=2,
            remove_unused_columns=False,
            dataloader_pin_memory=False,
        )
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,
        )
        
        # Create trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
            data_collator=data_collator,
        )
        
        # Start training
        logger.info("Starting training...")
        trainer.train()
        
        # Save the model
        trainer.save_model()
        tokenizer.save_pretrained(self.output_dir)
        
        # Save training config
        config_file = self.output_dir / "training_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump({
                'base_model': self.config.base_model,
                'lora_config': {
                    'r': self.config.lora_r,
                    'alpha': self.config.lora_alpha,
                    'dropout': self.config.lora_dropout,
                    'target_modules': self.config.lora_target_modules
                },
                'training_args': {
                    'batch_size': self.config.batch_size,
                    'epochs': self.config.num_epochs,
                    'learning_rate': self.config.learning_rate
                },
                'status': 'completed'
            }, f)
        
        logger.info(f"✅ Training completed! Model saved to: {self.output_dir}")
        
        # Import to Ollama after training
        logger.info("Importing fine-tuned model to Ollama...")
        try:
            from .ollama_lora_import import import_lora_to_ollama
            if import_lora_to_ollama(self.base_dir):
                logger.info("✅ Model imported to Ollama successfully")
            else:
                logger.warning("⚠️  Failed to import model to Ollama. You can run it manually later.")
        except Exception as e:
            logger.warning(f"⚠️  Failed to import to Ollama: {e}. Model is still saved locally.")
        
        return True
    
    def test_model(self) -> bool:
        """Test the trained model."""
        if not self.output_dir.exists():
            logger.error("No trained model found")
            return False
        
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            from peft import PeftModel
            
            # Load base model
            base_model = AutoModelForCausalLM.from_pretrained(self.config.base_model)
            tokenizer = AutoTokenizer.from_pretrained(self.output_dir)
            
            # Load LoRA weights
            model = PeftModel.from_pretrained(base_model, self.output_dir)
            
            # Test generation
            test_input = "Input: git comm\nOutput:"
            inputs = tokenizer(test_input, return_tensors="pt")
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=50,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            result = tokenizer.decode(outputs[0], skip_special_tokens=True)
            logger.info(f"Test generation: {result}")
            return True
            
        except Exception as e:
            logger.error(f"Model test failed: {e}")
            return False

def create_real_lora_trainer(config: Optional[LoRAConfig] = None) -> RealLoRATrainer:
    """Create a real LoRA trainer instance."""
    return RealLoRATrainer(config)
