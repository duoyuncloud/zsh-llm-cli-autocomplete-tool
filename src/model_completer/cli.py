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
    parser.add_argument('--import-to-ollama', action='store_true', help='Import fine-tuned LoRA model to Ollama')
    parser.add_argument('--commit-message', action='store_true', help='Generate smart commit message from git changes')
    parser.add_argument('--config', help='Path to config file')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    # Silent mode if called with a command (from Zsh plugin)
    silent = args.command is not None
    setup_logging(config, silent=silent)
    
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
    elif args.import_to_ollama:
        print("📦 Importing fine-tuned LoRA model to Ollama...")
        from model_completer.ollama_lora_import import import_lora_to_ollama
        if import_lora_to_ollama():
            print("✅ Model imported to Ollama successfully!")
            print("   You can now use 'zsh-assistant' model for completions")
        else:
            print("❌ Failed to import model to Ollama")
            print("   Make sure:")
            print("   1. LoRA training is completed (run --train first)")
            print("   2. Ollama is installed and running")
            sys.exit(1)
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
            print(completion, flush=True)
        elif args.suggestions > 1:
            suggestions = get_suggestions(args.command, args.suggestions, config)
            for i, suggestion in enumerate(suggestions, 1):
                print(f"{i}: {suggestion}", flush=True)
        else:
            completion = get_ai_completion(args.command, config)
            if completion and completion != args.command:
                # Clean up completion - remove any Input:/Output: labels and extra text
                import re
                original_completion = completion
                completion = completion.strip()
                
                # Handle multiline completions - look for Output: line
                lines = completion.split('\n')
                output_line = None
                for line in lines:
                    line = line.strip()
                    # Look for Output: line
                    if re.match(r'^(Output|output):', line, re.IGNORECASE):
                        output_line = re.sub(r'^(Output|output):\s*', '', line, flags=re.IGNORECASE).strip()
                        break
                
                # If we found an Output line, use it; otherwise use first line
                if output_line:
                    completion = output_line
                else:
                    # Remove Input:/Output: labels from the beginning
                    completion = re.sub(r'^(Input|Output|input|output):\s*', '', completion, flags=re.IGNORECASE).strip()
                    # Extract only the command (before any newlines)
                    completion = completion.split('\n')[0].strip()
                
                # Remove unwanted suffixes like "(Added by Troubleshooting)" but keep the commit message
                if '"' in completion:
                    # Handle quoted strings carefully - remove "(Added by...)" from inside quotes
                    parts = completion.split('"')
                    if len(parts) >= 3:
                        # Remove "(Added by...)" from the message part (parts[1])
                        parts[1] = re.sub(r'\s*\(Added by[^)]*\)', '', parts[1])
                        # Remove "Conventional Commit Message:" prefix if present
                        parts[1] = re.sub(r'^\s*Conventional Commit Message:\s*', '', parts[1], flags=re.IGNORECASE)
                        parts[1] = parts[1].strip()
                        # If message is now empty or only whitespace, reject the completion entirely
                        # Don't use placeholder - let AI model generate a proper message
                        if not parts[1] or parts[1].isspace():
                            # Reject this completion - it has invalid commit message
                            completion = args.command
                        else:
                            completion = '"'.join(parts)
                else:
                    # No quotes, safe to remove from end
                    completion = re.sub(r'\s*\(Added by[^)]*\)\s*$', '', completion)
                    completion = re.sub(r'\s*Conventional Commit Message:.*$', '', completion, flags=re.IGNORECASE)
                
                completion = completion.strip()
                
                # REMOVED: Don't add hardcode fallback - let AI model decide or return original
                # If completion is too similar to input, just return original command
                if completion == args.command or len(completion) <= len(args.command):
                    completion = args.command
                
                print(completion, flush=True)
            else:
                # Return original command if no completion found
                print(args.command, flush=True)
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
