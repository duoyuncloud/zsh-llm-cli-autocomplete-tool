#!/usr/bin/env python3
"""
Upload LoRA adapter to Hugging Face Hub.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class HuggingFaceUploader:
    """Upload LoRA adapter to Hugging Face Hub."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent.parent.parent
        self.lora_output_dir = self.base_dir / "zsh-lora-output"
        
    def is_lora_ready(self) -> bool:
        """Check if LoRA adapter files exist."""
        if not self.lora_output_dir.exists():
            return False
        
        required_files = [
            "adapter_config.json",
            "adapter_model.safetensors"
        ]
        
        for file in required_files:
            if not (self.lora_output_dir / file).exists():
                logger.error(f"Missing required file: {file}")
                return False
        
        return True
    
    def get_adapter_info(self) -> Optional[Dict]:
        """Get adapter configuration information."""
        if not self.is_lora_ready():
            return None
        
        config_file = self.lora_output_dir / "adapter_config.json"
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to read adapter config: {e}")
            return None
    
    def create_model_card(self, repo_id: str, base_model: str) -> str:
        """Create a model card README.md for Hugging Face."""
        adapter_info = self.get_adapter_info()
        if not adapter_info:
            return ""
        
        lora_r = adapter_info.get('r', 'N/A')
        lora_alpha = adapter_info.get('lora_alpha', 'N/A')
        lora_dropout = adapter_info.get('lora_dropout', 'N/A')
        target_modules = adapter_info.get('target_modules', [])
        
        # Read training config if available
        training_config = {}
        training_config_file = self.lora_output_dir / "training_config.yaml"
        if training_config_file.exists():
            try:
                import yaml
                with open(training_config_file, 'r') as f:
                    training_config = yaml.safe_load(f) or {}
            except:
                pass
        
        training_args = training_config.get('training_args', {})
        epochs = training_args.get('epochs', 'N/A')
        learning_rate = training_args.get('learning_rate', 'N/A')
        batch_size = training_args.get('batch_size', 'N/A')
        
        model_card = f"""---
license: apache-2.0
base_model: {base_model}
tags:
- lora
- zsh
- cli
- autocomplete
- command-line
- peft
---

# {repo_id}

This is a LoRA (Low-Rank Adaptation) adapter for [{base_model}](https://huggingface.co/{base_model}) fine-tuned for Zsh CLI command autocomplete.

## Model Details

### Base Model
- **Base Model:** [{base_model}](https://huggingface.co/{base_model})
- **Model Type:** Causal Language Model
- **Task:** CLI Command Completion

### LoRA Configuration
- **LoRA Rank (r):** {lora_r}
- **LoRA Alpha:** {lora_alpha}
- **LoRA Dropout:** {lora_dropout}
- **Target Modules:** {', '.join(target_modules) if target_modules else 'N/A'}

### Training Configuration
- **Epochs:** {epochs}
- **Learning Rate:** {learning_rate}
- **Batch Size:** {batch_size}
- **Training Data:** 277 CLI command completion samples (Git, Docker, NPM, Python, Kubernetes, etc.)

## Usage

### Using with PEFT

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Load base model
base_model = AutoModelForCausalLM.from_pretrained("{base_model}")
tokenizer = AutoTokenizer.from_pretrained("{base_model}")

# Load LoRA adapter
model = PeftModel.from_pretrained(base_model, "{repo_id}")

# Use for inference
prompt = "Input: git comm\\nOutput:"
inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=50)
result = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(result)
```

### Using with Ollama

This adapter is designed to work with the [zsh-llm-cli-autocomplete-tool](https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool) project.

After importing to Ollama, use it as:
```bash
ollama run zsh-assistant
```

## Training Data

The model was fine-tuned on 277 command completion pairs covering:
- Git commands (status, add, commit, push, pull, etc.)
- Docker commands (run, build, ps, exec, etc.)
- NPM/Node commands (install, run, start, etc.)
- Python commands (-m, -c, pip, etc.)
- Kubernetes commands (get, apply, delete, etc.)
- System commands (ls, cd, mkdir, etc.)

## Limitations

- This adapter is specifically fine-tuned for CLI command completion tasks
- Performance may vary for other use cases
- The base model's limitations also apply

## Citation

If you use this adapter, please cite:

```bibtex
@misc{{{repo_id.replace('/', '_').replace('-', '_')}}},
  title={{Zsh CLI Autocomplete LoRA Adapter}},
  author={{Your Name}},
  year={{2024}},
  publisher={{Hugging Face}},
  howpublished={{\\url{{https://huggingface.co/{repo_id.replace('/', '/')}}}}}
}}
```

## License

This adapter inherits the license from the base model [{base_model}](https://huggingface.co/{base_model}).
"""
        return model_card
    
    def upload_to_hub(
        self,
        repo_id: str,
        token: Optional[str] = None,
        private: bool = False,
        commit_message: str = "Upload LoRA adapter"
    ) -> bool:
        """
        Upload LoRA adapter to Hugging Face Hub.
        
        Args:
            repo_id: Hugging Face repository ID (e.g., "username/model-name")
            token: Hugging Face API token (if None, will try to get from environment or login)
            private: Whether to create a private repository
            commit_message: Commit message for the upload
        
        Returns:
            True if upload successful, False otherwise
        """
        try:
            from huggingface_hub import HfApi, login, create_repo
            from huggingface_hub.utils import HfHubHTTPError
        except ImportError:
            logger.error("huggingface_hub not installed. Install it with: pip install huggingface_hub")
            return False
        
        if not self.is_lora_ready():
            logger.error("LoRA adapter files not found. Please train the model first.")
            return False
        
        # Get or set token
        if token:
            os.environ['HF_TOKEN'] = token
        elif not os.environ.get('HF_TOKEN') and not os.environ.get('HUGGING_FACE_HUB_TOKEN'):
            try:
                login()
            except Exception as e:
                logger.error(f"Failed to login to Hugging Face: {e}")
                logger.error("Please set HF_TOKEN environment variable or run: huggingface-cli login")
                return False
        
        try:
            api = HfApi()
            hf_token = token or os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN')
            
            # Validate repo_id format
            if '/' not in repo_id:
                logger.error(f"Invalid repository ID format: {repo_id}")
                logger.error("Repository ID should be in format: username/model-name")
                logger.error(f"Example: your-username/zsh-assistant-lora")
                return False
            
            # Try to get user info to verify token
            try:
                user_info = api.whoami(token=hf_token)
                username = user_info.get('name', 'unknown')
                logger.info(f"✅ Authenticated as: {username}")
                
                # Check if repo_id matches username
                repo_username = repo_id.split('/')[0]
                if repo_username != username:
                    logger.warning(f"Repository username '{repo_username}' doesn't match your username '{username}'")
                    logger.warning("You can only create repositories under your own username")
                    logger.info(f"Consider using: {username}/zsh-assistant-lora")
            except Exception as e:
                logger.warning(f"Could not verify user info: {e}")
            
            # Create repository if it doesn't exist
            try:
                create_repo(
                    repo_id=repo_id,
                    token=hf_token,
                    private=private,
                    repo_type="model",
                    exist_ok=True
                )
                logger.info(f"✅ Repository created/verified: {repo_id}")
            except HfHubHTTPError as e:
                status_code = None
                if hasattr(e, 'response') and e.response is not None:
                    status_code = e.response.status_code
                elif hasattr(e, 'status_code'):
                    status_code = e.status_code
                
                error_msg = str(e)
                
                if status_code == 401:
                    logger.error("Authentication failed. Please check your Hugging Face token.")
                    logger.error("Make sure your token has 'write' permissions.")
                    logger.error("Get a new token at: https://huggingface.co/settings/tokens")
                    return False
                elif status_code == 403:
                    logger.error("Permission denied. Possible reasons:")
                    logger.error("1. Your token doesn't have 'write' permissions")
                    logger.error("2. The repository name format is incorrect (should be: username/model-name)")
                    logger.error("3. The repository already exists and you don't have write access")
                    logger.error(f"4. Error details: {error_msg}")
                    logger.error("")
                    logger.error("Solutions:")
                    logger.error("- Get a new token with 'write' permission: https://huggingface.co/settings/tokens")
                    logger.error("- Use a different repository name")
                    logger.error("- Check if the repository exists: https://huggingface.co/" + repo_id)
                    return False
                else:
                    # Log the error message for debugging
                    if status_code:
                        logger.error(f"HTTP {status_code}: {error_msg}")
                    else:
                        logger.error(f"Hugging Face API error: {error_msg}")
                    raise
            
            # Get base model from adapter config
            adapter_info = self.get_adapter_info()
            base_model = adapter_info.get('base_model_name_or_path', 'Qwen/Qwen3-1.7B') if adapter_info else 'Qwen/Qwen3-1.7B'
            
            # Create model card
            model_card = self.create_model_card(repo_id, base_model)
            model_card_path = self.lora_output_dir / "README.md"
            with open(model_card_path, 'w', encoding='utf-8') as f:
                f.write(model_card)
            logger.info("✅ Model card created")
            
            # Upload files
            files_to_upload = [
                "adapter_config.json",
                "adapter_model.safetensors",
                "README.md"
            ]
            
            # Upload training config if exists
            if (self.lora_output_dir / "training_config.yaml").exists():
                files_to_upload.append("training_config.yaml")
            
            logger.info(f"📤 Uploading {len(files_to_upload)} files to {repo_id}...")
            
            for file_name in files_to_upload:
                file_path = self.lora_output_dir / file_name
                if file_path.exists():
                    api.upload_file(
                        path_or_fileobj=str(file_path),
                        path_in_repo=file_name,
                        repo_id=repo_id,
                        repo_type="model",
                        commit_message=commit_message if file_name == files_to_upload[0] else None,
                    )
                    logger.info(f"  ✅ Uploaded: {file_name}")
                else:
                    logger.warning(f"  ⚠️  File not found: {file_name}")
            
            logger.info(f"✅ Successfully uploaded LoRA adapter to: https://huggingface.co/{repo_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload to Hugging Face: {e}", exc_info=True)
            return False


def upload_lora_to_hf(
    repo_id: str,
    token: Optional[str] = None,
    private: bool = False,
    base_dir: Optional[Path] = None
) -> bool:
    """
    Convenience function to upload LoRA adapter to Hugging Face.
    
    Args:
        repo_id: Hugging Face repository ID (e.g., "username/model-name")
        token: Hugging Face API token (optional)
        private: Whether to create a private repository
        base_dir: Base directory of the project (optional)
    
    Returns:
        True if upload successful, False otherwise
    """
    uploader = HuggingFaceUploader(base_dir)
    return uploader.upload_to_hub(repo_id, token, private)

