#!/usr/bin/env python3
"""
Test smart commit message feature
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from model_completer.enhanced_completer import EnhancedCompleter
import subprocess

def test_smart_commit():
    """Test smart commit message generation."""
    print('=' * 80)
    print('Smart Commit Message Feature Test')
    print('=' * 80)
    print()
    
    completer = EnhancedCompleter(model='zsh-assistant')
    
    # Analyze git changes
    print('📊 Analyzing Git Changes:')
    print('-' * 80)
    changes = completer._analyze_git_changes()
    
    print(f'Files changed: {len(changes["files_changed"])}')
    print(f'  Modified: {len(changes["files_modified"])} - {changes["files_modified"][:3]}')
    print(f'  Added: {len(changes["files_added"])} - {changes["files_added"][:3]}')
    print(f'  Deleted: {len(changes["files_deleted"])} - {changes["files_deleted"][:3]}')
    print(f'Lines: +{changes["lines_added"]} / -{changes["lines_removed"]}')
    print()
    
    # Generate smart commit message
    print('🤖 Generating Smart Commit Message:')
    print('-' * 80)
    
    # Test 1: Direct method
    commit_msg = completer.get_smart_commit_message()
    if commit_msg:
        print(f'✅ Smart commit message: {commit_msg}')
        print()
        print('💡 Usage:')
        print(f'   git commit -m "{commit_msg}"')
    else:
        print('⚠️  No changes detected')
    print()
    
    # Test 2: Through completion
    print('📝 Testing git commit completion:')
    print('-' * 80)
    result = completer.get_completion('git comm')
    print(f'git comm -> {result}')
    print()
    
    # Show what zsh would do
    print('📋 Comparison:')
    print('-' * 80)
    print('❌ Zsh built-in: Just shows git commit options/flags')
    print('✅ Enhanced LoRA: Analyzes your changes and suggests smart commit message')
    print()
    print('✨ Benefits:')
    print('   - Follows conventional commits format')
    print('   - Context-aware based on file changes')
    print('   - Understands project structure')
    print('   - Saves time on writing commit messages')

if __name__ == '__main__':
    test_smart_commit()

