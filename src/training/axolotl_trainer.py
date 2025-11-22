#!/usr/bin/env python3
"""Real LoRA fine-tuning using Axolotl with enhanced monitoring."""

import os
import subprocess
import yaml
import sys
import time
from pathlib import Path
import psutil

class AxolotlTrainer:
    def __init__(self):
        self.config_path = "src/training/axolotl_config.yml"
        self.base_dir = Path(__file__).parent.parent.parent
        self.training_start_time = None
        
    def print_banner(self):
        """Print training banner."""
        print("=" * 70)
        print("🤖 Zsh AI Autocomplete - Real LoRA Fine-tuning")
        print("=" * 70)
        print("🎯 Training a specialized model for Zsh command completion")
        print("⚡ Using Axolotl for efficient LoRA fine-tuning")
        print("=" * 70)
    
    def check_system_resources(self):
        """Check if system has enough resources for training."""
        print("🔍 Checking system resources...")
        
        # Check RAM
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        print(f"   RAM: {ram_gb:.1f} GB available")
        
        # Check disk space
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024 ** 3)
        print(f"   Disk: {disk_free_gb:.1f} GB free")
        
        if ram_gb < 8:
            print("⚠️  Warning: Less than 8GB RAM may cause issues")
        
        if disk_free_gb < 10:
            print("❌ Error: Need at least 10GB free disk space")
            return False
            
        return True
    
    def check_dependencies(self):
        """Check if all required dependencies are installed."""
        print("🔍 Checking dependencies...")
        
        required_packages = {
            'axolotl': 'axolotl',
            'torch': 'torch',
            'transformers': 'transformers',
            'accelerate': 'accelerate',
            'datasets': 'datasets',
            'peft': 'peft',
        }
        
        all_available = True
        for package, import_name in required_packages.items():
            try:
                __import__(import_name)
                print(f"   ✅ {package}")
            except ImportError:
                print(f"   ❌ {package}")
                all_available = False
        
        if not all_available:
            print("\n💡 Install missing packages with:")
            print("   pip install axolotl torch transformers accelerate datasets peft")
            return False
        
        return True
    
    def check_gpu(self):
        """Check GPU availability and capabilities."""
        print("🔍 Checking GPU...")
        
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                for i in range(gpu_count):
                    gpu_name = torch.cuda.get_device_name(i)
                    gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024 ** 3)
                    print(f"   ✅ GPU {i}: {gpu_name} ({gpu_memory:.1f} GB)")
                
                # Check if we have enough VRAM for 7B model
                if gpu_memory < 6:
                    print("⚠️  Warning: GPU memory may be insufficient for 7B model")
                    print("💡 Consider using a smaller model or --low-memory mode")
                
                return True
            else:
                print("   ⚠️  No GPU detected - will use CPU (very slow!)")
                return False
                
        except Exception as e:
            print(f"   ❌ GPU check failed: {e}")
            return False
    
    def verify_training_data(self):
        """Verify training data exists and is valid."""
        print("🔍 Verifying training data...")
        
        data_path = self.base_dir / "src/training/zsh_training_data_axolotl.jsonl"
        
        if not data_path.exists():
            print(f"   ❌ Training data not found: {data_path}")
            print("   💡 Run: python3 -m training.convert_to_axolotl_format")
            return False
        
        # Count lines in training data
        with open(data_path, 'r') as f:
            line_count = sum(1 for _ in f)
        
        print(f"   ✅ Training data: {line_count} examples")
        
        if line_count < 50:
            print("   ⚠️  Warning: Very small training dataset (< 50 examples)")
        
        return True
    
    def create_axolotl_config(self, low_memory: bool = False):
        """Create the Axolotl configuration file."""
        print("⚙️  Creating training configuration...")
        
        # Adjust configuration based on available resources
        if low_memory:
            micro_batch_size = 1
            gradient_accumulation = 8
        else:
            micro_batch_size = 2
            gradient_accumulation = 4
        
        config = {
            "base_model": "Qwen/Qwen3-1.7B",
            "model_type": "AutoModelForCausalLM",
            "tokenizer_type": "AutoTokenizer",
            "trust_remote_code": True,
            
            "datasets": [
                {
                    "path": str(self.base_dir / "src/training/zsh_training_data_axolotl.jsonl"),
                    "type": "alpaca"
                }
            ],
            "dataset_prepared_path": str(self.base_dir / "last_run_prepared"),
            "val_set_size": 0.1,
            "output_dir": str(self.base_dir / "zsh-lora-output"),
            
            # LoRA configuration
            "adapter": "lora",
            "lora_r": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.05,
            "lora_target_modules": [
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj"
            ],
            "lora_modules_to_save": ["embed_tokens", "lm_head"],
            
            # Training configuration
            "sequence_len": 1024 if low_memory else 2048,
            "sample_packing": True,
            "pad_to_sequence_len": True,
            
            "micro_batch_size": micro_batch_size,
            "gradient_accumulation_steps": gradient_accumulation,
            "num_epochs": 3,
            "optimizer": "adamw_bnb_8bit",
            "lr_scheduler": "cosine",
            "learning_rate": 0.0002,
            
            # Memory optimization
            "load_in_8bit": True,
            "load_in_4bit": False,
            "bf16": "auto",
            "fp16": False,
            "tf32": False,
            
            "gradient_checkpointing": True,
            "group_by_length": False,
            
            # Logging and saving
            "logging_steps": 10,
            "save_steps": 200,
            "eval_steps": 50,
            "save_safetensors": True,
            
            # Early stopping
            "early_stopping_patience": 3,
            "early_stopping_threshold": 0.001,
            
            # System
            "wandb_mode": "disabled"
        }
        
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"   ✅ Config created: {self.config_path}")
        return True
    
    def run_training(self):
        """Run the actual Axolotl training."""
        print("🚀 Starting LoRA fine-tuning...")
        
        # Change to project root directory
        os.chdir(self.base_dir)
        
        # Record start time
        self.training_start_time = time.time()
        
        # Run Axolotl training
        cmd = [
            "accelerate", "launch", "-m", "axolotl.cli.train",
            self.config_path
        ]
        
        try:
            print("⏳ Training in progress... This may take 30 minutes to 2 hours.")
            print("💡 You can monitor progress in the logs above.")
            print("   Look for decreasing loss values to track training progress.")
            print("-" * 50)
            
            result = subprocess.run(cmd, check=True)
            
            training_time = time.time() - self.training_start_time
            print(f"✅ Training completed in {training_time/60:.1f} minutes!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Training failed with exit code: {e.returncode}")
            return False
        except FileNotFoundError:
            print("❌ 'accelerate' command not found.")
            print("💡 Install with: pip install accelerate")
            return False
        except KeyboardInterrupt:
            print("\n⏹️  Training interrupted by user")
            return False
    
    def post_training_analysis(self):
        """Analyze training results."""
        output_dir = self.base_dir / "zsh-lora-output"
        
        if not output_dir.exists():
            print("❌ No training output found")
            return False
        
        print("\n📊 Training Results:")
        print("=" * 40)
        
        # List generated files
        files = list(output_dir.glob("*"))
        if files:
            print("📁 Generated files:")
            for file in files:
                size_mb = file.stat().st_size / (1024 * 1024)
                print(f"   {file.name} ({size_mb:.1f} MB)")
        else:
            print("   No output files found")
        
        # Check for adapter files
        adapter_files = list(output_dir.glob("*adapter*"))
        if adapter_files:
            print(f"✅ LoRA adapter files: {len(adapter_files)}")
        else:
            print("❌ No LoRA adapter files found")
        
        return len(adapter_files) > 0
    
    def train_complete_pipeline(self, low_memory: bool = False):
        """Run the complete training pipeline."""
        self.print_banner()
        
        # Step 1: System checks
        if not self.check_system_resources():
            return False
        
        if not self.check_dependencies():
            return False
        
        self.check_gpu()
        
        # Step 2: Data verification
        if not self.verify_training_data():
            return False
        
        # Step 3: Configuration
        if not self.create_axolotl_config(low_memory):
            return False
        
        # Step 4: Training
        if not self.run_training():
            return False
        
        # Step 5: Results analysis
        success = self.post_training_analysis()
        
        if success:
            print("\n🎉 LoRA Fine-tuning Completed Successfully!")
            print("=" * 50)
            print("🔧 Next steps:")
            print("   1. Your LoRA adapter is in: zsh-lora-output/")
            print("   2. You can use it with the transformers library")
            print("   3. To use with Ollama, wait for official LoRA support")
            print("   4. Test with: python3 -c \"from peft import PeftModel; print('Adapter ready!')\"")
        else:
            print("\n❌ Training completed with issues")
        
        return success

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Train LoRA adapter with Axolotl')
    parser.add_argument('--low-memory', action='store_true',
                       help='Use low memory configuration')
    
    args = parser.parse_args()
    
    trainer = AxolotlTrainer()
    success = trainer.train_complete_pipeline(low_memory=args.low_memory)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()