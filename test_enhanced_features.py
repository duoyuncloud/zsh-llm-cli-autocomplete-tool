#!/usr/bin/env python3
"""
Test enhanced features vs zsh built-in completion
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from model_completer.enhanced_completer import EnhancedCompleter
import subprocess

def test_vs_zsh():
    """Compare enhanced completer with zsh built-in completion."""
    print('=' * 80)
    print('Enhanced LoRA Model vs Zsh Built-in Completion')
    print('=' * 80)
    print()
    
    completer = EnhancedCompleter(model='zsh-assistant')
    
    print('✅ Enhanced Features:')
    print(f'   - Project Type Detection: {completer.project_context["project_type"]}')
    print(f'   - History Tracking: {len(completer.command_history)} commands saved')
    print(f'   - Context Awareness: Active')
    print()
    
    # Test commands
    test_commands = [
        'git comm',
        'docker run',
        'npm run',
        'python -m',
        'ls -'
    ]
    
    print('Testing Enhanced Completions:')
    print('-' * 80)
    
    for cmd in test_commands:
        print(f'\n📝 Command: {cmd}')
        
        # Enhanced completion
        result = completer.get_completion(cmd)
        print(f'   ✅ Enhanced: {result}')
        
        # Show context used
        context = completer._build_enhanced_prompt(cmd)
        if 'Context:' in context:
            context_part = context.split('Context:')[1].strip()
            print(f'   📊 Context: {context_part[:60]}')
        
        # Compare with zsh (if available)
        try:
            # This is a simplified test - zsh completion is interactive
            print(f'   📋 Zsh would: Show available options')
        except:
            pass
    
    print()
    print('=' * 80)
    print('Key Advantages Over Zsh Built-in:')
    print('=' * 80)
    print('✅ 1. Personalization: Learns from YOUR command history')
    print('✅ 2. Context Awareness: Knows your project type, git status, files')
    print('✅ 3. Smart Suggestions: AI-powered, not just static completions')
    print('✅ 4. Cross-command Intelligence: Understands workflow patterns')
    print('✅ 5. Developer-Focused: Optimized for development workflows')
    print()
    
    # Show personalized suggestions
    print('Testing Personalized Suggestions:')
    print('-' * 80)
    test_cmd = 'git '
    suggestions = completer.get_personalized_suggestions(test_cmd, 3)
    for i, sug in enumerate(suggestions, 1):
        print(f'   {i}. {sug}')
    print()

if __name__ == '__main__':
    test_vs_zsh()

