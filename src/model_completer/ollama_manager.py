#!/usr/bin/env python3
"""
Ollama server management module.
Handles Ollama installation, model management, and server operations.
"""

import os
import subprocess
import time
import requests
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class OllamaManager:
    """Manages Ollama server and models."""
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.pid_file = "ollama.pid"
        self.log_file = "ollama.log"
    
    def is_installed(self) -> bool:
        """Check if Ollama is installed."""
        try:
            result = subprocess.run(['ollama', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def install(self) -> bool:
        """Install Ollama if not present."""
        if self.is_installed():
            logger.info("Ollama is already installed")
            return True
        
        logger.info("Installing Ollama...")
        try:
            # Download and run Ollama installer
            result = subprocess.run([
                'curl', '-fsSL', 'https://ollama.ai/install.sh'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error("Failed to download Ollama installer")
                return False
            
            # Run the installer
            install_result = subprocess.run(['sh'], 
                                          input=result.stdout, 
                                          text=True, 
                                          timeout=60)
            
            if install_result.returncode == 0:
                logger.info("Ollama installed successfully")
                return True
            else:
                logger.error("Ollama installation failed")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Ollama installation timed out")
            return False
        except Exception as e:
            logger.error(f"Ollama installation failed: {e}")
            return False
    
    def is_running(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def start_server(self) -> bool:
        """Start Ollama server."""
        if self.is_running():
            logger.info("Ollama server is already running")
            return True
        
        logger.info("Starting Ollama server...")
        try:
            # Start Ollama in background
            with open(self.log_file, 'w') as log_f:
                process = subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )
            
            # Save PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Wait for server to start
            for i in range(self.timeout):
                if self.is_running():
                    logger.info(f"Ollama server started (PID: {process.pid})")
                    return True
                time.sleep(1)
            
            logger.error("Ollama server failed to start within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start Ollama server: {e}")
            return False
    
    def stop_server(self) -> bool:
        """Stop Ollama server."""
        if not self.is_running():
            logger.info("Ollama server is not running")
            return True
        
        logger.info("Stopping Ollama server...")
        try:
            # Try to stop using PID file
            if os.path.exists(self.pid_file):
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                try:
                    os.kill(pid, 15)  # SIGTERM
                    time.sleep(2)
                    
                    # Check if still running
                    try:
                        os.kill(pid, 0)  # Check if process exists
                        os.kill(pid, 9)  # SIGKILL if still running
                    except ProcessLookupError:
                        pass  # Process already dead
                    
                    logger.info("Ollama server stopped")
                    os.remove(self.pid_file)
                    return True
                except ProcessLookupError:
                    logger.info("Ollama server was not running")
                    os.remove(self.pid_file)
                    return True
            
            # Fallback: kill all ollama processes
            subprocess.run(['pkill', 'ollama'], capture_output=True)
            logger.info("Ollama server stopped (via pkill)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop Ollama server: {e}")
            return False
    
    def get_models(self) -> List[Dict[str, any]]:
        """Get list of available models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get models: {e}")
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        logger.info(f"Pulling model: {model_name}")
        try:
            result = subprocess.run(
                ['ollama', 'pull', model_name],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Model {model_name} pulled successfully")
                return True
            else:
                logger.error(f"Failed to pull model {model_name}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Model pull timed out: {model_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False
    
    def create_model(self, model_name: str, modelfile_content: str) -> bool:
        """Create a custom model from Modelfile."""
        logger.info(f"Creating model: {model_name}")
        try:
            # Write Modelfile
            with open('Modelfile', 'w') as f:
                f.write(modelfile_content)
            
            # Create model
            result = subprocess.run(
                ['ollama', 'create', model_name, '-f', 'Modelfile'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info(f"Model {model_name} created successfully")
                return True
            else:
                logger.error(f"Failed to create model {model_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create model {model_name}: {e}")
            return False
        finally:
            # Clean up Modelfile
            if os.path.exists('Modelfile'):
                os.remove('Modelfile')
    
    def test_model(self, model_name: str, prompt: str = "Hello") -> Tuple[bool, str]:
        """Test a model with a simple prompt."""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return True, result.get('response', '')
            else:
                return False, f"API error: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Request failed: {e}"
    
    def setup_default_models(self) -> bool:
        """Setup default models for CLI autocomplete."""
        logger.info("Setting up default models...")
        
        # List of models to install
        models = [
            "codellama:7b",  # Primary model for code completion
            "llama2:7b",     # Fallback model
        ]
        
        success_count = 0
        for model in models:
            if self.pull_model(model):
                success_count += 1
            else:
                logger.warning(f"Failed to pull {model}")
        
        # Create custom zsh-assistant model
        modelfile_content = """FROM qwen3:1.7b

SYSTEM \"\"\"You are a Zsh command completion expert. Always respond with complete executable commands. Never explain, just provide the command.\"\"\"

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_predict 30
PARAMETER num_ctx 512
PARAMETER repeat_penalty 1.1
"""
        
        if self.create_model("zsh-assistant", modelfile_content):
            success_count += 1
        
        logger.info(f"Setup completed: {success_count}/{len(models) + 1} models ready")
        return success_count > 0
    
    def get_server_info(self) -> Dict[str, any]:
        """Get Ollama server information."""
        info = {
            'running': self.is_running(),
            'url': self.base_url,
            'models': [],
            'version': None
        }
        
        if self.is_running():
            try:
                # Get models
                info['models'] = self.get_models()
                
                # Get version
                result = subprocess.run(['ollama', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info['version'] = result.stdout.strip()
                    
            except Exception as e:
                logger.error(f"Failed to get server info: {e}")
        
        return info

def create_ollama_manager(base_url: str = "http://localhost:11434") -> OllamaManager:
    """Factory function to create Ollama manager."""
    return OllamaManager(base_url)
