import requests
import json
import time
from typing import Optional, Dict, Any
from .cache import CacheManager
import logging

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for communicating with Ollama server."""
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.cache = CacheManager()
    
    def is_server_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def generate_completion(self, prompt: str, model: str, 
                          context: Optional[Dict] = None, 
                          use_cache: bool = True) -> str:
        """Generate completion using Ollama API."""
        
        # Check cache first
        cache_key = f"completion:{model}:{hash(prompt)}"
        if use_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.debug("Cache hit for prompt: %s", prompt[:50])
                return cached_result
        
        # Prepare request data
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
            }
        }
        
        if context:
            data["context"] = context
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=data,
                timeout=self.timeout
            )
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                completion = result.get("response", "").strip()
                
                # Cache the result
                if use_cache and completion:
                    self.cache.set(cache_key, completion, ttl=3600)  # Cache for 1 hour
                
                logger.debug("Completion generated in %.2fs: %s", elapsed_time, completion[:100])
                return completion
            else:
                logger.error("Ollama API error: %s - %s", response.status_code, response.text)
                return ""
                
        except requests.exceptions.Timeout:
            # Timeout is expected for interactive use - use debug level
            logger.debug("Request to Ollama timed out after %ds (expected for fast fallback)", self.timeout)
            return ""
        except requests.exceptions.RequestException as e:
            # Only log non-timeout errors as warnings
            logger.warning("Request to Ollama failed: %s", e)
            return ""
    
    def get_available_models(self) -> list:
        """Get list of available models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except requests.exceptions.RequestException:
            return []