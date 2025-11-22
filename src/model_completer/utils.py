import yaml
import os
from typing import Dict, Any, Optional

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    default_config = {
        'ollama': {
            'url': 'http://localhost:11434',
            'timeout': 30
        },
        'model': 'zsh-assistant',
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
        # Try project config first, then user config
        project_config = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'default.yaml')
        if os.path.exists(project_config):
            config_path = project_config
        else:
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

def setup_logging(config: Dict[str, Any], silent: bool = False) -> None:
    """Setup logging configuration.
    
    Args:
        config: Configuration dictionary
        silent: If True, only log to file, not to console (for Zsh plugin use)
    """
    import logging
    import sys
    
    logging_config = config.get('logging', {})
    level = getattr(logging, logging_config.get('level', 'INFO').upper())
    
    # Create log directory if it doesn't exist
    log_file = os.path.expanduser(logging_config.get('file', '~/.cache/model-completer/logs.txt'))
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    handlers = [logging.FileHandler(log_file)]
    
    # Only add console handler if not in silent mode (i.e., not called from Zsh plugin)
    if not silent:
        handlers.append(logging.StreamHandler())
    else:
        # In silent mode, set logging level to WARNING to suppress INFO/DEBUG
        level = logging.WARNING
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # Force reconfiguration if already set up
    )