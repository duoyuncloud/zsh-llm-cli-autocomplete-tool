#!/usr/bin/env python3
"""
LoRA fine-tuning module for CLI autocomplete models.
Handles training data preparation, model fine-tuning, and adapter management.
"""

import os
import json
import yaml
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Configuration for LoRA training."""
    base_model: str = "Qwen/Qwen3-1.7B"
    model_type: str = "AutoModelForCausalLM"
    tokenizer_type: str = "AutoTokenizer"
    trust_remote_code: bool = True
    
    # LoRA parameters
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = None
    
    # Training parameters
    sequence_len: int = 2048
    micro_batch_size: int = 2
    gradient_accumulation_steps: int = 4
    num_epochs: int = 3
    learning_rate: float = 0.0002
    optimizer: str = "adamw_bnb_8bit"
    lr_scheduler: str = "cosine"
    
    # Memory optimization
    load_in_8bit: bool = False
    load_in_4bit: bool = True
    bf16: str = "auto"
    gradient_checkpointing: bool = True
    
    # Logging and saving
    logging_steps: int = 10
    save_steps: int = 200
    eval_steps: int = 50
    save_safetensors: bool = True
    
    def __post_init__(self):
        if self.lora_target_modules is None:
            self.lora_target_modules = [
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj"
            ]

class TrainingDataManager:
    """Manages training data preparation and validation."""
    
    def __init__(self, data_dir: str = "src/training"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_training_data(self, max_examples: int = 500) -> str:
        """Generate comprehensive training data for CLI autocomplete."""
        data_file = self.data_dir / "zsh_training_data.jsonl"
        
        if data_file.exists():
            logger.info(f"Training data already exists: {data_file}")
            return str(data_file)
        
        # Generate training data using the existing script
        try:
            result = subprocess.run([
                "python3", "-m", "training.prepare_zsh_data",
                "--max-examples", str(max_examples),
                "--output", str(data_file)
            ], capture_output=True, text=True, check=True)
            
            logger.info(f"Generated training data: {data_file}")
            return str(data_file)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate training data: {e}")
            # Create basic training data as fallback
            return self._create_basic_training_data(data_file)
    
    def _create_basic_training_data(self, data_file: Path) -> str:
        """Create basic training data as fallback."""
        basic_data = [
            {"input": "git comm", "output": "git commit -m \"commit message\""},
            {"input": "git add", "output": "git add ."},
            {"input": "git push", "output": "git push origin main"},
            {"input": "git pull", "output": "git pull origin develop"},
            {"input": "docker run", "output": "docker run -it --name container image:tag"},
            {"input": "docker ps", "output": "docker ps -a"},
            {"input": "npm run", "output": "npm run dev"},
            {"input": "python -m", "output": "python -m http.server 8000"},
            {"input": "kubectl get", "output": "kubectl get pods"},
            {"input": "ls -", "output": "ls -la"},
        ]
        
        with open(data_file, 'w') as f:
            for item in basic_data:
                f.write(json.dumps(item) + '\n')
        
        logger.info(f"Created basic training data: {data_file}")
        return str(data_file)
    
    def convert_to_axolotl_format(self, input_file: str, output_file: str) -> bool:
        """Convert training data to Axolotl format."""
        try:
            import json
            
            # Read input file
            input_path = Path(input_file)
            if not input_path.exists():
                logger.error(f"Input file not found: {input_file}")
                return False
            
            data = []
            with open(input_path, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            
            # Convert to Axolotl format
            axolotl_data = []
            for item in data:
                axolotl_item = {
                    "instruction": "Complete this Zsh command. Provide only the full command without explanations.",
                    "input": item.get("input", ""),
                    "output": item.get("output", ""),
                    "system": "You are a Zsh shell expert. Always respond with complete, executable Zsh commands. Never explain your reasoning."
                }
                axolotl_data.append(axolotl_item)
            
            # Write output file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                for item in axolotl_data:
                    f.write(json.dumps(item) + '\n')
            
            logger.info(f"Converted {len(axolotl_data)} examples to Axolotl format: {output_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to convert training data: {e}")
            return False
    
    def validate_training_data(self, data_file: str) -> Tuple[bool, int]:
        """Validate training data and return count of examples."""
        try:
            with open(data_file, 'r') as f:
                lines = f.readlines()
            
            valid_count = 0
            for line in lines:
                try:
                    data = json.loads(line.strip())
                    if 'input' in data and 'output' in data:
                        valid_count += 1
                except json.JSONDecodeError:
                    continue
            
            return valid_count > 0, valid_count
        except FileNotFoundError:
            return False, 0

class LoRATrainer:
    """Handles LoRA fine-tuning using Axolotl."""
    
    def __init__(self, config: TrainingConfig, output_dir: str = "zsh-lora-output"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_manager = TrainingDataManager()
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are available."""
        required_packages = [
            'torch', 'transformers', 'accelerate', 
            'datasets', 'peft', 'axolotl'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            logger.error(f"Missing required packages: {missing_packages}")
            logger.info("Install with: pip install " + " ".join(missing_packages))
            return False
        
        return True
    
    def check_system_resources(self) -> Tuple[bool, Dict[str, any]]:
        """Check system resources for training."""
        import psutil
        
        # Check RAM
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        
        # Check disk space
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024 ** 3)
        
        # Check GPU
        gpu_available = False
        gpu_memory = 0
        try:
            import torch
            if torch.cuda.is_available():
                gpu_available = True
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        except ImportError:
            pass
        
        resources = {
            'ram_gb': ram_gb,
            'disk_free_gb': disk_free_gb,
            'gpu_available': gpu_available,
            'gpu_memory_gb': gpu_memory
        }
        
        # Check if resources are sufficient
        sufficient = (
            ram_gb >= 8 and  # At least 8GB RAM
            disk_free_gb >= 10 and  # At least 10GB free disk
            (gpu_available or ram_gb >= 16)  # GPU or 16GB+ RAM
        )
        
        return sufficient, resources
    
    def create_axolotl_config(self, data_file: str, low_memory: bool = False) -> str:
        """Create Axolotl configuration file."""
        config_file = self.data_manager.data_dir / "axolotl_config.yml"
        
        # Adjust configuration based on resources
        if low_memory:
            self.config.micro_batch_size = 1
            self.config.gradient_accumulation_steps = 8
            self.config.sequence_len = 1024
        
        config_dict = {
            "base_model": self.config.base_model,
            "model_type": self.config.model_type,
            "tokenizer_type": self.config.tokenizer_type,
            "trust_remote_code": self.config.trust_remote_code,
            
            "datasets": [
                {
                    "path": data_file,
                    "type": "alpaca"
                }
            ],
            "dataset_prepared_path": str(self.data_manager.data_dir / "last_run_prepared"),
            "val_set_size": 0.1,
            "output_dir": str(self.output_dir),
            
            # LoRA configuration
            "adapter": "lora",
            "lora_r": self.config.lora_r,
            "lora_alpha": self.config.lora_alpha,
            "lora_dropout": self.config.lora_dropout,
            "lora_target_modules": self.config.lora_target_modules,
            "lora_modules_to_save": ["embed_tokens", "lm_head"],
            
            # Training configuration
            "sequence_len": self.config.sequence_len,
            "sample_packing": True,
            "pad_to_sequence_len": True,
            
            "micro_batch_size": self.config.micro_batch_size,
            "gradient_accumulation_steps": self.config.gradient_accumulation_steps,
            "num_epochs": self.config.num_epochs,
            "optimizer": self.config.optimizer,
            "lr_scheduler": self.config.lr_scheduler,
            "learning_rate": self.config.learning_rate,
            
            # Memory optimization
            "load_in_8bit": self.config.load_in_8bit,
            "load_in_4bit": self.config.load_in_4bit,
            "bf16": self.config.bf16,
            "fp16": False,
            "tf32": False,
            
            "gradient_checkpointing": self.config.gradient_checkpointing,
            "group_by_length": False,
            
            # Logging and saving
            "logging_steps": self.config.logging_steps,
            "save_steps": self.config.save_steps,
            "eval_steps": self.config.eval_steps,
            "save_safetensors": self.config.save_safetensors,
            
            # Early stopping
            "early_stopping_patience": 3,
            "early_stopping_threshold": 0.001,
            
            # System
            "wandb_mode": "disabled"
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Created Axolotl config: {config_file}")
        return str(config_file)
    
    def train(self, data_file: str, low_memory: bool = False) -> bool:
        """Run LoRA training."""
        logger.info("Starting LoRA fine-tuning...")
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Check system resources
        sufficient, resources = self.check_system_resources()
        if not sufficient:
            logger.warning("System resources may be insufficient for training")
            if not low_memory:
                logger.info("Consider using --low-memory flag")
        
        # Validate training data
        valid, count = self.data_manager.validate_training_data(data_file)
        if not valid:
            logger.error("Invalid training data")
            return False
        
        logger.info(f"Training data validated: {count} examples")
        
        # Convert to Axolotl format if needed
        axolotl_data_file = data_file.replace('.jsonl', '_axolotl.jsonl')
        if not Path(axolotl_data_file).exists():
            if not self.data_manager.convert_to_axolotl_format(data_file, axolotl_data_file):
                logger.error("Failed to convert training data")
                return False
        else:
            logger.info(f"Using existing Axolotl format file: {axolotl_data_file}")
        
        # Create Axolotl config
        config_file = self.create_axolotl_config(axolotl_data_file, low_memory)
        
        # Run training
        try:
            cmd = [
                "accelerate", "launch", "-m", "axolotl.cli.train",
                config_file
            ]
            
            logger.info("Starting training process...")
            result = subprocess.run(cmd, check=True)
            
            logger.info("Training completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Training failed: {e}")
            return False
        except FileNotFoundError:
            logger.error("accelerate command not found. Install with: pip install accelerate")
            return False
    
    def test_adapter(self, adapter_path: str) -> bool:
        """Test the trained adapter."""
        try:
            from peft import PeftModel
            from transformers import AutoModel, AutoTokenizer
            
            # Load base model and adapter
            model = AutoModel.from_pretrained(self.config.base_model)
            model = PeftModel.from_pretrained(model, adapter_path)
            
            # Test with a simple prompt
            tokenizer = AutoTokenizer.from_pretrained(self.config.base_model)
            test_prompt = "Complete this command: git comm"
            
            inputs = tokenizer(test_prompt, return_tensors="pt")
            outputs = model.generate(**inputs, max_length=50, temperature=0.1)
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            logger.info(f"Adapter test response: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Adapter test failed: {e}")
            return False

def create_trainer(config: Optional[TrainingConfig] = None):
    """Factory function to create a LoRA trainer."""
    # Try real LoRA trainer with transformers/PEFT first
    try:
        from .real_lora_trainer import create_real_lora_trainer
        from .real_lora_trainer import LoRAConfig
        if config is None:
            lora_config = LoRAConfig()
        else:
            lora_config = LoRAConfig(
                base_model=config.base_model,
                lora_r=config.lora_r,
                lora_alpha=config.lora_alpha,
                lora_dropout=config.lora_dropout,
                lora_target_modules=config.lora_target_modules,
                num_epochs=config.num_epochs,
                learning_rate=config.learning_rate
            )
        return create_real_lora_trainer(lora_config)
    except ImportError:
        # Try to import Axolotl as fallback
        try:
            import axolotl
            if config is None:
                config = TrainingConfig()
            return LoRATrainer(config)
        except ImportError:
            logger.error("No training backend available. Install transformers/peft or axolotl")
            raise ImportError("Training dependencies not available")

def train_cli_model(data_file: str, output_dir: str = "zsh-lora-output", 
                   low_memory: bool = False) -> bool:
    """Convenience function to train a CLI model."""
    trainer = create_trainer()
    return trainer.train(data_file, low_memory)
