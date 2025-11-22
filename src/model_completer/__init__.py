"""
Model CLI Autocomplete - AI-powered command completion for Zsh
Simple Tab completion with personalized predictions using LoRA fine-tuned models
"""

__version__ = "0.1.0"
__author__ = "Model CLI Autocomplete Team"

# Import main classes for easy access
from .completer import ModelCompleter
from .enhanced_completer import EnhancedCompleter
from .client import OllamaClient
from .ollama_manager import OllamaManager, create_ollama_manager
from .training import create_trainer, TrainingConfig, TrainingDataManager, LoRATrainer
from .utils import load_config, setup_logging
from .cache import CacheManager

# Main CLI function
from .cli import main

__all__ = [
    'ModelCompleter',
    'EnhancedCompleter',
    'OllamaClient', 
    'OllamaManager',
    'create_ollama_manager',
    'create_trainer',
    'TrainingConfig',
    'TrainingDataManager', 
    'LoRATrainer',
    'load_config',
    'setup_logging',
    'CacheManager',
    'main'
]
