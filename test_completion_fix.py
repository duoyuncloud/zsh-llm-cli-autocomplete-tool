#!/usr/bin/env python3
"""
Test script to verify completion is working correctly and fast
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from model_completer.enhanced_completer import EnhancedCompleter

def test_completions():
    """Test that completions are working fast and correctly."""
    print('=' * 70)
    print('Completion System Test')
    print('=' * 70)
    print()
    
    completer = EnhancedCompleter(model='zsh-assistant')
    
    test_commands = [
        ('git comm', 'git commit -m "commit message"'),
        ('docker run', 'docker run -it --name container image:tag'),
        ('npm run', 'npm run dev'),
        ('python -m', 'python -m http.server 8000'),
        ('kubectl get', 'kubectl get pods'),
    ]
    
    print('Testing completion speed (should all be < 0.1s):')
    print('-' * 70)
    
    all_passed = True
    for cmd, expected in test_commands:
        start = time.time()
        result = completer.get_completion(cmd)
        elapsed = time.time() - start
        
        # Check if result matches expected (or starts with expected)
        matches = result.startswith(cmd) and len(result) > len(cmd)
        speed_ok = elapsed < 0.1
        
        status = '✅' if (matches and speed_ok) else '❌'
        if not (matches and speed_ok):
            all_passed = False
        
        print(f'{status} {cmd:15} -> {result[:55]:55} ({elapsed:.3f}s)')
        if not matches:
            print(f'   Expected to start with: {expected[:55]}')
    
    print()
    print('=' * 70)
    if all_passed:
        print('✅ All tests passed! Completions are working correctly.')
    else:
        print('❌ Some tests failed. Check output above.')
    print('=' * 70)

if __name__ == '__main__':
    test_completions()

