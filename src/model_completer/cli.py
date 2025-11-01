#!/usr/bin/env python3
"""
Command-line interface for AI command completion.
Integrates with the existing completer, client, and UI modules.
"""

import argparse
import sys
import os
from typing import List, Dict, Optional

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from model_completer.completer import ModelCompleter
from model_completer.enhanced_completer import EnhancedCompleter
from model_completer.client import OllamaClient
from model_completer.ui import create_ui
from model_completer.utils import load_config, setup_logging
from model_completer.training import create_trainer

def get_ai_completion(command: str, config: Optional[Dict] = None, enhanced: bool = True) -> str:
    """Get AI completion using enhanced completer with developer features."""
    if config is None:
        config = load_config()
    
    # Use EnhancedCompleter for better developer experience
    if enhanced:
        completer = EnhancedCompleter(
            ollama_url=config.get('ollama', {}).get('url', 'http://localhost:11434'),
            model=config.get('model', 'zsh-assistant'),
            config=config
        )
    else:
        completer = ModelCompleter(
            ollama_url=config.get('ollama', {}).get('url', 'http://localhost:11434'),
            model=config.get('model', 'zsh-assistant'),
            config=config
        )
    
    return completer.get_completion(command)

def get_suggestions(command: str, count: int = 3, config: Optional[Dict] = None) -> List[str]:
    """Get multiple completion suggestions with personalization."""
    if config is None:
        config = load_config()
    
    completer = EnhancedCompleter(
        ollama_url=config.get('ollama', {}).get('url', 'http://localhost:11434'),
        model=config.get('model', 'zsh-assistant'),
        config=config
    )
    
    # Use personalized suggestions if available
    if hasattr(completer, 'get_personalized_suggestions'):
        return completer.get_personalized_suggestions(command, count)
    return completer.get_suggestions(command, count)

def get_advanced_completion(command: str, config: Optional[Dict] = None) -> str:
    """Get completion with confidence score using UI module."""
    if config is None:
        config = load_config()
    
    completer = EnhancedCompleter(
        ollama_url=config.get('ollama', {}).get('url', 'http://localhost:11434'),
        model=config.get('model', 'zsh-assistant'),
        config=config
    )
    
    ui = create_ui(completer, "zsh", config)
    if hasattr(ui, 'show_confidence_completion'):
        completion, confidence = ui.show_confidence_completion(command)
        return f"{completion}|{int(confidence * 100)}"
    else:
        # Fallback for ZshCompletionUI
        completion = completer.get_completion(command)
        return f"{completion}|80"

def main():
    parser = argparse.ArgumentParser(description='AI Command Completion with Navigatable UI')
    parser.add_argument('command', nargs='?', help='Command to complete')
    parser.add_argument('--list-models', action='store_true', help='List available models')
    parser.add_argument('--test', action='store_true', help='Test completions')
    parser.add_argument('--suggestions', type=int, default=1, help='Number of suggestions to return')
    parser.add_argument('--advanced', action='store_true', help='Get completion with confidence score')
    parser.add_argument('--train', action='store_true', help='Start LoRA training')
    parser.add_argument('--generate-data', action='store_true', help='Generate training data')
    parser.add_argument('--commit-message', action='store_true', help='Generate smart commit message from git changes')
    parser.add_argument('--config', help='Path to config file')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    setup_logging(config)
    
    # Initialize Ollama client for model listing
    client = OllamaClient(config.get('ollama', {}).get('url', 'http://localhost:11434'))
    
    if args.list_models:
        if client.is_server_available():
            models = client.get_available_models()
            if models:
                print("Available models:")
                for model in models:
                    print(f"  - {model}")
            else:
                print("No models found")
        else:
            print("Could not connect to Ollama server")
    elif args.train:
        print("🚀 Starting LoRA training...")
        trainer = create_trainer()
        data_file = "src/training/zsh_training_data.jsonl"
        success = trainer.train(data_file)
        if success:
            print("✅ Training completed successfully!")
        else:
            print("❌ Training failed")
            sys.exit(1)
    elif args.generate_data:
        print("📊 Generating training data...")
        from model_completer.training import TrainingDataManager
        data_manager = TrainingDataManager()
        data_file = data_manager.generate_training_data()
        print(f"✅ Training data generated: {data_file}")
    elif args.commit_message:
        completer = EnhancedCompleter(
            ollama_url=config.get('ollama', {}).get('url', 'http://localhost:11434'),
            model=config.get('model', 'zsh-assistant'),
            config=config
        )
        commit_msg = completer.get_smart_commit_message()
        if commit_msg:
            print(f"📝 Smart commit message: {commit_msg}")
            print()
            print("Use it with:")
            print(f'  git commit -m "{commit_msg}"')
        else:
            print("⚠️  No staged changes found. Stage your changes first with 'git add'")
    elif args.test:
        print("Testing AI completions:")
        test_commands = ["git comm", "docker run", "npm run", "python -m", "kubectl get"]
        for cmd in test_commands:
            completion = get_ai_completion(cmd, config)
            print(f"  {cmd} -> {completion}")
    elif args.command:
        if args.advanced:
            completion = get_advanced_completion(args.command, config)
            print(completion)
        elif args.suggestions > 1:
            suggestions = get_suggestions(args.command, args.suggestions, config)
            for i, suggestion in enumerate(suggestions, 1):
                print(f"{i}: {suggestion}")
        else:
            completion = get_ai_completion(args.command, config)
            if completion:
                print(completion)
            else:
                print(args.command)
    else:
        print("AI Command Completer with Navigatable UI - Ready!")
        print("Usage: model-completer 'git comm'")
        print("Options:")
        print("  --suggestions N    Get N suggestions")
        print("  --advanced         Get completion with confidence")
        print("  --test            Test the system")
        print("  --list-models     List available models")
        print("  --train           Start LoRA training")
        print("  --generate-data   Generate training data")

if __name__ == '__main__':
    main()
