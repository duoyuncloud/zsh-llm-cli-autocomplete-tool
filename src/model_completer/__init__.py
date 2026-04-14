"""
Zsh LLM CLI Autocomplete Plugin — Python runtime

This package is the on-device side of the plugin: a completion daemon (Unix socket),
model download/merge helpers, and optional training utilities. The Zsh layer shows grey ghost suggestions while you type; you press Tab to accept. Inference uses a
local base model plus a LoRA adapter; nothing is sent to the cloud unless you
opt in to optional cloud routes.
"""

__version__ = "0.1.0"
__author__ = "duoyuncloud"

# Lightweight imports only (used by CLI fast path). Heavy modules (EnhancedCompleter,
# training, ollama_lora_import) are imported lazily where needed so Tab completion
# stays fast (~0.3s instead of ~5s).
from .utils import load_config, setup_logging
from .client import OllamaClient

# Lazy access to heavy modules (avoids loading on "from model_completer.client import ...")
def __getattr__(name):
    if name == "ModelCompleter":
        from .completer import ModelCompleter
        return ModelCompleter
    if name == "EnhancedCompleter":
        from .enhanced_completer import EnhancedCompleter
        return EnhancedCompleter
    if name in ("OllamaManager", "create_ollama_manager"):
        from .ollama_manager import OllamaManager, create_ollama_manager
        return OllamaManager if name == "OllamaManager" else create_ollama_manager
    if name in ("create_trainer", "TrainingConfig", "TrainingDataManager", "LoRATrainer"):
        from .training import create_trainer, TrainingConfig, TrainingDataManager, LoRATrainer
        return { "create_trainer": create_trainer, "TrainingConfig": TrainingConfig,
                 "TrainingDataManager": TrainingDataManager, "LoRATrainer": LoRATrainer }[name]
    if name == "CacheManager":
        from .cache import CacheManager
        return CacheManager
    if name == "main":
        from .cli import main
        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ModelCompleter",
    "EnhancedCompleter",
    "OllamaClient",
    "OllamaManager",
    "create_ollama_manager",
    "create_trainer",
    "TrainingConfig",
    "TrainingDataManager",
    "LoRATrainer",
    "load_config",
    "setup_logging",
    "CacheManager",
    "main",
]
