"""
Model CLI Autocomplete - AI-powered command completion for Zsh
"""

__version__ = "0.1.0"
__author__ = "Model CLI Autocomplete Team"

# Import main classes for easy access
from .completer import ModelCompleter
from .client import OllamaClient
from .ollama_manager import OllamaManager, create_ollama_manager
from .training import create_trainer, TrainingConfig, TrainingDataManager, LoRATrainer
from .ui import create_ui, CompletionUI, ZshCompletionUI
from .utils import load_config, setup_logging
from .cache import CacheManager

# Main CLI function
from .cli import main

__all__ = [
    'ModelCompleter',
    'OllamaClient', 
    'OllamaManager',
    'create_ollama_manager',
    'create_trainer',
    'TrainingConfig',
    'TrainingDataManager', 
    'LoRATrainer',
    'create_ui',
    'CompletionUI',
    'ZshCompletionUI',
    'load_config',
    'setup_logging',
    'CacheManager',
    'main'
]
