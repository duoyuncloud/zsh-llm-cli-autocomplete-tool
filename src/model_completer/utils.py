import yaml
import os
from typing import Dict, Any

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    default_config = {
        'ollama': {
            'url': 'http://localhost:11434',
            'timeout': 10
        },
        'model': 'llama2',
        'cache': {
            'enabled': True,
            'ttl': 3600
        },
        'logging': {
            'level': 'INFO',
            'file': '~/.cache/model-completer/logs.txt'
        }
    }
    
    if config_path is None:
        config_path = os.path.expanduser('~/.config/model-completer/config.yaml')
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f) or {}
            
            # Deep merge
            def deep_merge(base, update):
                for key, value in update.items():
                    if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                        deep_merge(base[key], value)
                    else:
                        base[key] = value
                return base
            
            return deep_merge(default_config, user_config)
        except (yaml.YAMLError, IOError):
            return default_config
    
    return default_config

def setup_logging(config: Dict[str, Any]) -> None:
    """Setup logging configuration."""
    import logging
    logging_config = config.get('logging', {})
    level = getattr(logging, logging_config.get('level', 'INFO').upper())
    
    # Create log directory if it doesn't exist
    log_file = os.path.expanduser(logging_config.get('file', '~/.cache/model-completer/logs.txt'))
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )