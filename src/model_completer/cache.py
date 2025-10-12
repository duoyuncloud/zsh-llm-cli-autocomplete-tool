import json
import time
from typing import Optional, Any
import os

class CacheManager:
    """Simple cache manager for completion results."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/model-completer")
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """Get file path for cache key."""
        import hashlib
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.json")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Check if cache is expired
            if data.get('expiry', 0) < time.time():
                os.remove(cache_path)
                return None
            
            return data.get('value')
        except (json.JSONDecodeError, IOError):
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""
        cache_path = self._get_cache_path(key)
        
        data = {
            'value': value,
            'expiry': time.time() + ttl,
            'created': time.time()
        }
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            return True
        except IOError:
            return False
    
    def clear(self) -> None:
        """Clear all cached items."""
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                os.remove(os.path.join(self.cache_dir, filename))