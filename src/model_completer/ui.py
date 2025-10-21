#!/usr/bin/env python3
"""
Navigatable UI module for AI command completion.
Provides interactive UI components for command suggestions.
"""

import os
import sys
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json

try:
    from prompt_toolkit import PromptSession, HTML
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.shortcuts import confirm, prompt
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout.containers import HSplit, VSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.layout.layout import Layout
    from prompt_toolkit.styles import Style
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

@dataclass
class CompletionSuggestion:
    """Represents a completion suggestion with metadata."""
    text: str
    confidence: float = 0.0
    description: str = ""
    category: str = "general"

class CompletionUI:
    """Navigatable UI for command completion suggestions."""
    
    def __init__(self, completer, config: Optional[Dict] = None):
        self.completer = completer
        self.config = config or {}
        self.session = None
        self._setup_prompt_toolkit()
    
    def _setup_prompt_toolkit(self):
        """Setup prompt toolkit session if available."""
        if not PROMPT_TOOLKIT_AVAILABLE:
            return
        
        try:
            self.session = PromptSession()
        except Exception as e:
            print(f"Warning: Could not initialize prompt toolkit: {e}")
            self.session = None
    
    def show_suggestions(self, command: str, max_suggestions: int = 5) -> Optional[str]:
        """Show interactive suggestions for a command."""
        if not PROMPT_TOOLKIT_AVAILABLE or not self.session:
            return self._fallback_suggestions(command, max_suggestions)
        
        try:
            suggestions = self._get_suggestions_with_metadata(command, max_suggestions)
            if not suggestions:
                return None
            
            return self._interactive_selection(suggestions, command)
        except Exception as e:
            print(f"UI Error: {e}")
            return self._fallback_suggestions(command, max_suggestions)
    
    def _get_suggestions_with_metadata(self, command: str, max_suggestions: int) -> List[CompletionSuggestion]:
        """Get suggestions with confidence scores and metadata."""
        suggestions = []
        
        # Get basic suggestions
        basic_suggestions = self.completer.get_suggestions(command, max_suggestions)
        
        for i, suggestion in enumerate(basic_suggestions):
            # Calculate confidence based on position and similarity
            confidence = max(0.5, 1.0 - (i * 0.1))
            
            # Determine category
            category = self._categorize_suggestion(suggestion)
            
            # Generate description
            description = self._generate_description(suggestion, command)
            
            suggestions.append(CompletionSuggestion(
                text=suggestion,
                confidence=confidence,
                description=description,
                category=category
            ))
        
        return suggestions
    
    def _categorize_suggestion(self, suggestion: str) -> str:
        """Categorize a suggestion based on its content."""
        if suggestion.startswith('git '):
            return 'git'
        elif suggestion.startswith('docker '):
            return 'docker'
        elif suggestion.startswith('npm ') or suggestion.startswith('yarn '):
            return 'node'
        elif suggestion.startswith('python ') or suggestion.startswith('pip '):
            return 'python'
        elif suggestion.startswith('kubectl '):
            return 'kubernetes'
        elif suggestion.startswith('ls ') or suggestion.startswith('cd ') or suggestion.startswith('mkdir '):
            return 'filesystem'
        else:
            return 'general'
    
    def _generate_description(self, suggestion: str, original_command: str) -> str:
        """Generate a human-readable description for a suggestion."""
        if suggestion.startswith('git commit'):
            return "Commit changes with message"
        elif suggestion.startswith('git push'):
            return "Push changes to remote"
        elif suggestion.startswith('docker run'):
            return "Run a Docker container"
        elif suggestion.startswith('npm run'):
            return "Run npm script"
        elif suggestion.startswith('python -m'):
            return "Run Python module"
        elif suggestion.startswith('kubectl get'):
            return "List Kubernetes resources"
        else:
            return f"Complete: {original_command}"
    
    def _interactive_selection(self, suggestions: List[CompletionSuggestion], command: str) -> Optional[str]:
        """Show interactive selection menu."""
        if not self.session:
            return None
        
        # Create a simple selection interface
        print(f"\n🎯 AI Suggestions for: {command}")
        print("=" * 50)
        
        for i, suggestion in enumerate(suggestions, 1):
            confidence_bar = "█" * int(suggestion.confidence * 10)
            print(f"{i}. {suggestion.text}")
            print(f"   📊 Confidence: {suggestion.confidence:.1%} {confidence_bar}")
            print(f"   📝 {suggestion.description}")
            print(f"   🏷️  Category: {suggestion.category}")
            print()
        
        # Get user selection
        try:
            choice = input("Select suggestion (1-{}), or press Enter to skip: ".format(len(suggestions)))
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(suggestions):
                    return suggestions[idx].text
        except (KeyboardInterrupt, EOFError):
            pass
        
        return None
    
    def _fallback_suggestions(self, command: str, max_suggestions: int) -> Optional[str]:
        """Fallback method when prompt toolkit is not available."""
        suggestions = self.completer.get_suggestions(command, max_suggestions)
        
        if not suggestions:
            return None
        
        print(f"\n🎯 AI Suggestions for: {command}")
        print("=" * 40)
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
        
        try:
            choice = input(f"\nSelect (1-{len(suggestions)}) or Enter to skip: ")
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(suggestions):
                    return suggestions[idx]
        except (KeyboardInterrupt, EOFError):
            pass
        
        return None
    
    def show_confidence_completion(self, command: str) -> Tuple[str, float]:
        """Show completion with confidence score."""
        completion = self.completer.get_completion(command)
        
        if not completion:
            return command, 0.0
        
        # Calculate confidence based on various factors
        confidence = self._calculate_confidence(completion, command)
        
        return completion, confidence
    
    def _calculate_confidence(self, completion: str, original_command: str) -> float:
        """Calculate confidence score for a completion."""
        # Base confidence
        confidence = 0.7
        
        # Increase confidence for common patterns
        if completion.startswith('git commit'):
            confidence += 0.1
        elif completion.startswith('docker run'):
            confidence += 0.1
        elif completion.startswith('npm run'):
            confidence += 0.1
        
        # Increase confidence if completion is significantly longer than input
        if len(completion) > len(original_command) * 1.5:
            confidence += 0.1
        
        # Decrease confidence for very short completions
        if len(completion) < len(original_command) + 5:
            confidence -= 0.1
        
        return min(1.0, max(0.0, confidence))

class ZshCompletionUI:
    """Zsh-specific completion UI that integrates with shell completion."""
    
    def __init__(self, completer):
        self.completer = completer
    
    def generate_completion_menu(self, command: str, max_suggestions: int = 5) -> str:
        """Generate Zsh completion menu format."""
        suggestions = self.completer.get_suggestions(command, max_suggestions)
        
        if not suggestions:
            return ""
        
        # Format for Zsh completion
        menu_items = []
        for i, suggestion in enumerate(suggestions, 1):
            menu_items.append(f"{i}:{suggestion}")
        
        return "\n".join(menu_items)
    
    def generate_completion_with_confidence(self, command: str) -> str:
        """Generate completion with confidence for Zsh."""
        completion, confidence = self.completer.get_completion(command), 0.8
        
        if not completion:
            return command
        
        # Format: completion|confidence
        return f"{completion}|{int(confidence * 100)}"

def create_ui(completer, ui_type: str = "interactive", config: Optional[Dict] = None):
    """Factory function to create appropriate UI."""
    if ui_type == "zsh":
        return ZshCompletionUI(completer)
    else:
        return CompletionUI(completer, config)
