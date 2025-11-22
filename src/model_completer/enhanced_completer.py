#!/usr/bin/env python3
"""Enhanced completer with personalization and history tracking."""

import os
import json
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import Counter
from .client import OllamaClient
from .completer import ModelCompleter
import logging

logger = logging.getLogger(__name__)

class EnhancedCompleter(ModelCompleter):
    """Completer with personalization and workflow learning."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", 
                 model: str = "zsh-assistant", config: Optional[Dict] = None):
        super().__init__(ollama_url, model, config)
        self.history_file = self._get_history_file()
        self.command_history = self._load_history()
        self.project_context = self._detect_project_context()
        
    def _get_history_file(self) -> Path:
        """Get path to history file."""
        history_dir = Path.home() / '.cache' / 'model-completer'
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir / 'command_history.jsonl'
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Load command history from file."""
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            history.append(json.loads(line))
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")
        return history[-100:]  # Keep last 100 commands
    
    def _save_command(self, command: str, completion: str, context: Dict[str, Any]):
        """Save command to history."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'completion': completion,
            'context': context,
            'working_dir': os.getcwd()
        }
        try:
            with open(self.history_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            self.command_history.append(entry)
            # Keep history manageable
            if len(self.command_history) > 100:
                self.command_history = self.command_history[-100:]
        except Exception as e:
            logger.warning(f"Failed to save history: {e}")
    
    def _detect_project_context(self) -> Dict[str, Any]:
        """Detect project type and context."""
        context = {
            'project_type': 'unknown',
            'languages': [],
            'frameworks': [],
            'has_docker': False,
            'has_k8s': False,
            'has_python': False,
            'has_node': False,
            'files': []
        }
        
        current_dir = Path(os.getcwd())
        
        # Check for project files
        if (current_dir / 'package.json').exists():
            context['project_type'] = 'node'
            context['has_node'] = True
            try:
                with open(current_dir / 'package.json') as f:
                    pkg = json.load(f)
                    if 'dependencies' in pkg or 'devDependencies' in pkg:
                        deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                        if 'react' in deps:
                            context['frameworks'].append('react')
                        if 'vue' in deps:
                            context['frameworks'].append('vue')
                        if 'express' in deps:
                            context['frameworks'].append('express')
            except:
                pass
        
        if (current_dir / 'requirements.txt').exists() or (current_dir / 'pyproject.toml').exists() or (current_dir / 'setup.py').exists():
            context['project_type'] = 'python'
            context['has_python'] = True
            context['languages'].append('python')
        
        if (current_dir / 'Dockerfile').exists() or (current_dir / 'docker-compose.yml').exists():
            context['has_docker'] = True
        
        if (current_dir / 'k8s').exists() or (current_dir / 'kubernetes').exists() or list(current_dir.glob('*.yaml')):
            context['has_k8s'] = True
        
        if (current_dir / 'pom.xml').exists() or (current_dir / 'build.gradle').exists():
            context['project_type'] = 'java'
            context['languages'].append('java')
        
        if (current_dir / 'Cargo.toml').exists():
            context['project_type'] = 'rust'
            context['languages'].append('rust')
        
        if (current_dir / 'go.mod').exists():
            context['project_type'] = 'go'
            context['languages'].append('go')
        
        # Get recent files
        try:
            recent_files = sorted(
                [f for f in current_dir.iterdir() if f.is_file()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:10]
            context['files'] = [f.name for f in recent_files]
        except:
            pass
        
        return context
    
    def _get_user_patterns(self, command: str) -> Dict[str, Any]:
        """Analyze user patterns from history."""
        patterns = {
            'frequent_commands': [],
            'common_flags': [],
            'recent_workflow': [],
            'similar_commands': []
        }
        
        # Find similar commands in history
        cmd_base = command.split()[0] if command.split() else command
        similar = [
            h['command'] for h in self.command_history[-50:]
            if h['command'].split()[0] == cmd_base
        ]
        patterns['similar_commands'] = similar[-5:]
        
        # Get frequent commands
        all_commands = [h['command'].split()[0] for h in self.command_history[-100:]]
        counter = Counter(all_commands)
        patterns['frequent_commands'] = [cmd for cmd, _ in counter.most_common(5)]
        
        # Get recent workflow (sequence of commands)
        if len(self.command_history) >= 2:
            patterns['recent_workflow'] = [
                h['command'] for h in self.command_history[-3:]
            ]
        
        return patterns
    
    def _build_enhanced_prompt(self, command: str) -> str:
        """Build enhanced prompt with developer context and command sequences."""
        current_dir = os.getcwd()
        dir_name = os.path.basename(current_dir)
        
        # Get git info
        git_info = self._get_git_info()
        git_branch = ""
        git_status = ""
        if git_info:
            lines = git_info.split('\n')
            for line in lines:
                if 'Branch:' in line:
                    git_branch = line.split('Branch:')[1].strip()
                if 'Status:' in line:
                    git_status = line.split('Status:')[1].strip()
        
        # Get user patterns
        patterns = self._get_user_patterns(command)
        
        # Get recent command history for sequence awareness
        # Since CLI creates new instance each time, we rely on persisted history
        recent_commands = []
        
        # First try in-memory history (same session - works if completer is reused)
        if self.history and len(self.history) > 1:
            # Get last 3 commands before current one
            recent_commands = self.history[-4:-1] if len(self.history) > 4 else self.history[:-1]
        
        # Check persisted history for recent commands (including completions that were executed)
        if not recent_commands and self.command_history:
            # Look at the last few commands/completions - use the completion as that's what was actually executed
            recent_entries = self.command_history[-5:]
            # Get actual executed commands (use completion if it's a full command)
            executed_commands = []
            for entry in recent_entries:
                # Prefer completion as that's what user actually executed
                exec_cmd = entry.get('completion', entry.get('command', ''))
                if exec_cmd and exec_cmd.strip():
                    executed_commands.append(exec_cmd)
            if executed_commands:
                # Get last 2-3 commands for context
                recent_commands = executed_commands[-3:]
        
        # Build context string
        context_parts = []
        
        # Project context
        if self.project_context['project_type'] != 'unknown':
            context_parts.append(f"Project: {self.project_context['project_type']}")
        if self.project_context['frameworks']:
            context_parts.append(f"Frameworks: {', '.join(self.project_context['frameworks'])}")
        if self.project_context['has_docker']:
            context_parts.append("Has Docker")
        if self.project_context['has_k8s']:
            context_parts.append("Has Kubernetes")
        
        # Git context
        if git_branch:
            context_parts.append(f"Git branch: {git_branch}")
        if git_status and 'M' in git_status:
            context_parts.append("Has uncommitted changes")
        
        # Add detailed git status for "git" command (informational only, let AI decide)
        if command.strip() == "git":
            if self.project_context.get('git_unstaged', 0) > 0:
                context_parts.append(f"Has {self.project_context.get('git_unstaged')} unstaged file(s)")
            if self.project_context.get('git_staged', 0) > 0:
                context_parts.append(f"Has {self.project_context.get('git_staged')} staged file(s)")
            if self.project_context.get('git_unstaged', 0) == 0 and self.project_context.get('git_staged', 0) == 0:
                context_parts.append("No uncommitted changes")
        
        # User patterns
        if patterns['similar_commands']:
            context_parts.append(f"Recent similar: {patterns['similar_commands'][-1]}")
        
        # Recent files
        if self.project_context['files']:
            recent_files = ', '.join(self.project_context['files'][:3])
            context_parts.append(f"Recent files: {recent_files}")
        
        context_str = " | ".join(context_parts)
        
        # Build enhanced prompt with command sequence awareness
        prompt_parts = [f"Complete this command: {command}"]
        
        # Add command sequence context - informative only, don't force specific suggestions
        if recent_commands:
            sequence_str = " -> ".join(recent_commands)
            prompt_parts.append(f"\nRecent command sequence: {sequence_str}")
            prompt_parts.append("Based on the current state and context, suggest the most appropriate completion.")
            
            # Don't add explicit workflow hints - let AI decide based on actual state
            # The git status context below will provide enough information
        
        if context_str:
            prompt_parts.append(f"\nContext: {context_str}")
        
        # Add personalization hint
        if patterns['frequent_commands'] and command.split()[0] in patterns['frequent_commands']:
            prompt_parts.append("\n(User frequently uses this command type)")
        
        prompt = "\n".join(prompt_parts)
        
        # Add explicit instruction to output ONLY the command, no explanations
        prompt += "\n\nOutput ONLY the complete command, nothing else. No explanations, no prefixes like 'Complete command:' or 'The command is:'. Just the command itself."
        
        return prompt
    
    def get_completion(self, command: str, use_cache: bool = True) -> str:
        """Get enhanced completion with developer context."""
        # Update history
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
            self.history = self.history[-10:]
        
        # Refresh project context
        self.project_context = self._detect_project_context()
        
        # Try AI completion with enhanced prompt (with fast timeout)
        # For interactive use, prioritize speed over AI quality
        # Try training data first for instant results
        fallback_completion = self._get_fallback_completion(command)
        
        # Try AI only if no training data match, with very short timeout
        if not fallback_completion:
            try:
                prompt = self._build_enhanced_prompt(command)
                
                # Use very short timeout for interactive use (3 seconds)
                original_timeout = self.client.timeout
                self.client.timeout = 3
                
                try:
                    completion = self.client.generate_completion(
                        prompt, self.model, use_cache=use_cache
                    )
                except Exception:
                    # Timeout or error - return None to use fallback
                    completion = None
                finally:
                    self.client.timeout = original_timeout
            except Exception:
                completion = None
        else:
            # Use training data immediately
            self._save_command(command, fallback_completion, {
                'project_type': self.project_context['project_type'],
                'source': 'training_data'
            })
            return fallback_completion
        
        # If we got an AI completion, process it
        if completion:
            try:
                # Extract the completion from the response
                lines = completion.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    # Clean markdown
                    line = line.replace('```', '').strip()
                    
                    # Look for lines that look like actual commands
                    if (line and 
                        len(line) > len(command) and
                        ' ' in line and
                        not line.startswith(('To complete', 'This will', 'You can', 'Enter', 'Run:', 'Note:', 'Environment:', 'User:', 'Host:', 'Directory:', 'Recent:', 'Replace', 'This will launch', 'You can now', 'This will display', 'Suggestion:', 'Implement:', 'Provide', 'Git commit is', 'Remember,', 'By following', 'Start by', 'Next,', 'After that', 'The command', 'You are a', 'Complete the command', 'Command to complete', 'Sure,', 'Here', 'This flag', 'This option', 'This command', 'Context:', 'Project:', 'Git branch:', 'Recent files:', 'User frequently')) and
                        not line.startswith(('1.', '2.', '3.', '4.', '5.', '- ', '* ', '• ')) and
                        not line.endswith(':') and
                        not line.startswith('$') and
                        not line.startswith('`') and
                        not line.endswith('`') and
                        '|' not in line[:20]):  # Skip context lines
                        result = line
                        
                        # Save to history
                        git_info = self._get_git_info()
                        git_branch = None
                        if git_info and 'Branch:' in git_info:
                            try:
                                git_branch = git_info.split('Branch:')[1].strip().split('\n')[0]
                            except:
                                pass
                        
                        self._save_command(command, result, {
                            'project_type': self.project_context['project_type'],
                            'git_branch': git_branch,
                            'source': 'ai'
                        })
                        return result
            except Exception as e:
                logger.warning(f"AI completion processing failed: {e}")
        
        # Fall back to training data (already checked above, but check again in case)
        fallback_completion = self._get_fallback_completion(command)
        if fallback_completion:
            # Save to history even for fallbacks
            self._save_command(command, fallback_completion, {
                'project_type': self.project_context['project_type'],
                'source': 'training_data'
            })
            return fallback_completion
        
        # Return original command if no completion found
        return command
    
    def get_personalized_suggestions(self, command: str, max_suggestions: int = 5) -> List[str]:
        """Get personalized suggestions based on user history."""
        suggestions = []
        
        # Get similar commands from history
        patterns = self._get_user_patterns(command)
        
        # Get base suggestions
        base_suggestions = self.get_suggestions(command, max_suggestions)
        suggestions.extend(base_suggestions)
        
        # Add personalized suggestions based on history
        if patterns['similar_commands']:
            for similar_cmd in patterns['similar_commands'][:2]:
                if similar_cmd not in suggestions:
                    # Get completion for similar command
                    try:
                        similar_completion = self.get_completion(similar_cmd)
                        if similar_completion and similar_completion not in suggestions:
                            suggestions.append(similar_completion)
                    except:
                        pass
        
        return suggestions[:max_suggestions]
    
    def _get_git_diff_context(self) -> str:
        """Get git diff content to understand actual code changes."""
        try:
            # Try staged changes first
            diff_result = subprocess.run(['git', 'diff', '--cached'],
                                       capture_output=True, text=True, timeout=5)
            diff_content = diff_result.stdout if diff_result.returncode == 0 else ""
            
            # If no staged changes, check unstaged
            if not diff_content.strip():
                diff_result = subprocess.run(['git', 'diff'],
                                           capture_output=True, text=True, timeout=5)
                diff_content = diff_result.stdout if diff_result.returncode == 0 else ""
            
            if not diff_content:
                return ""
            
            # Extract meaningful functionality from diff
            lines = diff_content.split('\n')
            key_changes = {
                'functions': [],
                'classes': [],
                'imports': [],
                'features': [],
                'files': []
            }
            current_file = None
            
            # Track context across multiple lines for better understanding
            in_function = False
            function_context = []
            
            for line in lines[:500]:  # Increased limit for better context
                # Track file changes (but don't include in output)
                if line.startswith('diff --git'):
                    parts = line.split()
                    if len(parts) >= 3:
                        current_file = parts[2].split('/', 1)[-1]
                        if current_file not in key_changes['files']:
                            key_changes['files'].append(current_file)
                elif line.startswith('+++'):
                    parts = line.split()
                    if len(parts) >= 2:
                        filename = parts[1].split('/', 1)[-1] if '/' in parts[1] else parts[1]
                        current_file = filename
                elif line.startswith('@@'):
                    # New function/block context
                    in_function = False
                    function_context = []
                
                # Look for added code (functionality)
                if line.startswith('+') and not line.startswith('+++'):
                    stripped = line[1:].strip()
                    # Skip comments and blank lines
                    if stripped.startswith('#') or stripped.startswith('//') or not stripped:
                        continue
                    
                    # Extract function definitions with parameters
                    if stripped.startswith('def '):
                        func_def = stripped.split('#')[0].strip()  # Remove comments
                        func_name = func_def.split('(')[0].replace('def ', '').strip()
                        # Extract parameters to understand what the function does
                        if '(' in func_def and ')' in func_def:
                            params = func_def.split('(')[1].split(')')[0]
                            key_changes['functions'].append(f"{func_name}({params})")
                        else:
                            key_changes['functions'].append(func_name)
                        # Extract docstring if present
                        if '"""' in stripped or "'''" in stripped:
                            doc_start = stripped.find('"""') if '"""' in stripped else stripped.find("'''")
                            doc_end = stripped.find('"""', doc_start + 3) if '"""' in stripped else stripped.find("'''", doc_start + 3)
                            if doc_end > doc_start:
                                docstring = stripped[doc_start+3:doc_end].strip()
                                if len(docstring) > 10 and len(docstring) < 200:
                                    key_changes['features'].append(f"{func_name}: {docstring[:100]}")
                    
                    # Extract class definitions with inheritance
                    elif stripped.startswith('class '):
                        class_def = stripped.split('#')[0].strip()
                        class_name = class_def.split('(')[0].split(':')[0].replace('class ', '').strip()
                        # Extract parent class if present
                        if '(' in class_def:
                            parent = class_def.split('(')[1].split(')')[0].split(',')[0].strip()
                            key_changes['classes'].append(f"{class_name}({parent})")
                        else:
                            key_changes['classes'].append(class_name)
                    
                    # Extract imports (new dependencies/features)
                    elif stripped.startswith('import ') or stripped.startswith('from '):
                        import_part = stripped.split('#')[0].strip()
                        if len(import_part) < 150:
                            key_changes['imports'].append(import_part)
                    
                        # Extract method calls and key operations
                    elif len(stripped) > 10:
                        # Track context for better understanding
                        if stripped.startswith('def ') or stripped.startswith('class '):
                            in_function = True
                            function_context = [stripped]
                        elif in_function and not stripped.startswith(' '):
                            in_function = False
                        
                        # Look for method calls that indicate functionality
                        if '.' in stripped and '(' in stripped:
                            method_match = stripped.split('(')[0] if '(' in stripped else stripped
                            if '.' in method_match:
                                method_name = method_match.split('.')[-1].strip()
                                obj_name = method_match.split('.')[0].strip()
                                # More specific method extraction
                                if any(keyword in method_name.lower() for keyword in ['generate', 'create', 'process', 'handle', 'analyze', 'extract', 'parse', 'build', 'setup', 'init', 'train', 'complete', 'fix', 'add', 'implement', 'improve', 'enhance', 'refactor', 'update', 'delete', 'remove', 'save', 'load', 'get', 'set', 'send', 'receive', 'validate', 'check', 'verify']):
                                    # Extract parameters if meaningful
                                    if '(' in stripped and ')' in stripped:
                                        params = stripped.split('(')[1].split(')')[0]
                                        if len(params) < 80 and params.strip():
                                            key_changes['features'].append(f"{obj_name}.{method_name}({params[:60]})")
                                    else:
                                        key_changes['features'].append(f"{obj_name}.{method_name}()")
                        
                        # Extract return statements with meaningful values
                        elif stripped.startswith('return ') and len(stripped) > 15:
                            return_val = stripped.replace('return', '').strip()
                            if len(return_val) < 100 and '/' not in return_val and not any(ext in return_val for ext in ['.py', '.js', '.log', '.txt', '.yaml', '.json']):
                                # Extract meaningful return value
                                if return_val.startswith(('f"', "f'", '"', "'")):
                                    return_val = return_val[1:-1] if len(return_val) > 2 else return_val
                                key_changes['features'].append(f"returns {return_val[:80]}")
                        
                        # Extract meaningful assignments and operations
                        elif '=' in stripped and not stripped.startswith(' '):
                            left = stripped.split('=')[0].strip()
                            right = stripped.split('=')[1].strip().split('#')[0].strip()
                            # Look for meaningful variable names or operations
                            meaningful_vars = ['result', 'output', 'data', 'config', 'model', 'client', 'handler', 'manager', 'service', 'api', 'response', 'request', 'error', 'exception', 'value', 'item', 'obj', 'instance', 'completion', 'prediction', 'message', 'commit', 'diff', 'context', 'prompt', 'feature', 'functionality']
                            if any(keyword in left.lower() for keyword in meaningful_vars):
                                if len(right) < 100 and '/' not in right and not any(ext in right for ext in ['.py', '.js', '.log', '.txt']):
                                    # Clean up right side
                                    if right.startswith(('f"', "f'", '"', "'")):
                                        right = right[1:-1] if len(right) > 2 else right
                                    key_changes['features'].append(f"{left} = {right[:60]}")
                        
                        # Extract if/elif conditions that indicate logic
                        elif stripped.startswith(('if ', 'elif ', 'while ', 'for ')) and len(stripped) > 15:
                            condition = stripped.split(':')[0] if ':' in stripped else stripped
                            # Extract meaningful condition
                            if any(keyword in condition.lower() for keyword in ['error', 'exception', 'none', 'empty', 'valid', 'check', 'verify', 'exists', 'available', 'found']):
                                key_changes['features'].append(f"condition: {condition[:80]}")
            
            # Build descriptive context (functionality only, no file names)
            context_parts = []
            
            # Prioritize features (actual functionality)
            if key_changes['features']:
                # Filter out file-related features, duplicates, and generic code fragments
                features = []
                seen = set()
                generic_patterns = ['function_context', 'key_changes', 'seen.add', 'capture_output', 'diff_result', 'prompt_parts', 'context_parts', 'if diff_result', 'if len(', 'if not ', 'if any(', 'if stripped', 'for f in', 'for line in', 'for imp in', 'parts =', 'line =', 'f_lower =', 'module =']
                
                for f in key_changes['features']:
                    f_lower = f.lower()
                    # Skip if it's a generic code fragment
                    is_generic = any(pattern in f_lower for pattern in generic_patterns)
                    # Skip if it's just a variable assignment without meaning
                    is_just_assignment = '=' in f and len(f.split('=')) == 2 and len(f.split('=')[0].strip()) < 15
                    
                    if (not is_generic and not is_just_assignment and
                        not any(ext in f_lower for ext in ['.py', '.js', '.ts', '.log', '.txt', '.md', '.yaml', '.yml', '.json', '/']) and
                        f_lower not in seen and len(f) > 8 and
                        not f_lower.startswith(('if ', 'for ', 'while ', 'def ', 'class ', 'import ', 'from '))):
                        features.append(f)
                        seen.add(f_lower)
                
                if features:
                    context_parts.append(f"Key functionality:\n" + '\n'.join(f"  - {f}" for f in features[:12]))
            
            # Add function signatures
            if key_changes['functions']:
                unique_funcs = []
                seen = set()
                for f in key_changes['functions']:
                    if f.lower() not in seen:
                        unique_funcs.append(f)
                        seen.add(f.lower())
                if unique_funcs:
                    context_parts.append(f"Functions: {', '.join(unique_funcs[:6])}")
            
            # Add class information
            if key_changes['classes']:
                unique_classes = list(set(key_changes['classes']))[:5]
                context_parts.append(f"Classes: {', '.join(unique_classes)}")
            
            # Add imports (new dependencies)
            if key_changes['imports']:
                unique_imports = []
                seen = set()
                for imp in key_changes['imports']:
                    # Extract module name
                    module = imp.split('import')[1].strip().split()[0].split('.')[0] if 'import' in imp else imp.split('from')[1].strip().split()[0].split('.')[0] if 'from' in imp else imp
                    if module not in seen:
                        unique_imports.append(module)
                        seen.add(module)
                if unique_imports:
                    context_parts.append(f"New dependencies: {', '.join(unique_imports[:5])}")
            
            return '\n'.join(context_parts) if context_parts else ""
            
        except Exception as e:
            logger.debug(f"Failed to get git diff: {e}")
            return ""
    
    def _analyze_git_changes(self) -> Dict[str, Any]:
        """Analyze git changes to generate commit message context."""
        changes = {
            'files_changed': [],
            'files_added': [],
            'files_deleted': [],
            'files_modified': [],
            'lines_added': 0,
            'lines_removed': 0,
            'summary': ''
        }
        
        try:
            # Check if we're in a git repo
            subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], 
                         check=True, capture_output=True, text=True, timeout=2)
            
            # Get both staged and unstaged changes
            status_result = subprocess.run(['git', 'status', '--short'],
                                         capture_output=True, text=True, timeout=2)
            status_output = status_result.stdout.strip()
            
            # Also check unstaged changes
            diff_unstaged = subprocess.run(['git', 'diff', '--name-only'],
                                          capture_output=True, text=True, timeout=2)
            unstaged_files = [f.strip() for f in diff_unstaged.stdout.strip().split('\n') if f.strip()]
            
            # Also check staged changes specifically
            diff_staged = subprocess.run(['git', 'diff', '--cached', '--name-only'],
                                       capture_output=True, text=True, timeout=2)
            staged_files = [f.strip() for f in diff_staged.stdout.strip().split('\n') if f.strip()]
            
            # Use staged changes if available, otherwise use unstaged
            if not status_output and not unstaged_files and not staged_files:
                return changes
            
            # Prefer staged changes for commit message generation (for commits, we want staged)
            # If no staged changes, use unstaged
            if staged_files:
                # Get detailed status of staged files
                status_staged = subprocess.run(['git', 'diff', '--cached', '--name-status'],
                                             capture_output=True, text=True, timeout=2)
                if status_staged.returncode == 0:
                    for line in status_staged.stdout.strip().split('\n'):
                        if not line.strip():
                            continue
                        status = line[0]
                        filename = line[1:].strip()
                        if filename not in changes['files_changed']:
                            if status == 'A':
                                changes['files_added'].append(filename)
                            elif status == 'D':
                                changes['files_deleted'].append(filename)
                            else:  # M, R, etc
                                changes['files_modified'].append(filename)
                            changes['files_changed'].append(filename)
            elif unstaged_files:
                # No staged changes, but have unstaged - analyze those
                status_unstaged = subprocess.run(['git', 'diff', '--name-status'],
                                               capture_output=True, text=True, timeout=2)
                if status_unstaged.returncode == 0:
                    for line in status_unstaged.stdout.strip().split('\n'):
                        if not line.strip():
                            continue
                        status = line[0]
                        filename = line[1:].strip()
                        if filename not in changes['files_changed']:
                            if status == 'A':
                                changes['files_added'].append(filename)
                            elif status == 'D':
                                changes['files_deleted'].append(filename)
                            else:  # M, R, etc
                                changes['files_modified'].append(filename)
                            changes['files_changed'].append(filename)
            else:
                # Fallback to parsing status output
                for line in status_output.split('\n'):
                    if not line.strip():
                        continue
                    
                    status = line[:2]
                    filename = line[3:].strip()
                    
                    if filename not in changes['files_changed']:
                        if status.startswith('A'):
                            changes['files_added'].append(filename)
                        elif status.startswith('D'):
                            changes['files_deleted'].append(filename)
                        elif status.startswith('M') or status.startswith('R'):
                            changes['files_modified'].append(filename)
                        
                        changes['files_changed'].append(filename)
            
            # Get diff stats (try staged first, then unstaged)
            diff_result = subprocess.run(['git', 'diff', '--cached', '--stat'],
                                        capture_output=True, text=True, timeout=3)
            diff_output = diff_result.stdout if diff_result.returncode == 0 else ""
            
            # If no staged changes, check unstaged
            if not diff_output.strip():
                diff_result = subprocess.run(['git', 'diff', '--stat'],
                                            capture_output=True, text=True, timeout=3)
                diff_output = diff_result.stdout if diff_result.returncode == 0 else ""
            
            if diff_output:
                # Extract line counts from diff stat
                for line in diff_output.split('\n'):
                    if '|' in line and ('file changed' in line.lower() or 'files changed' in line.lower()):
                        # Extract numbers from stat line
                        parts = line.split('|')
                        if len(parts) >= 2:
                            numbers = parts[1].strip().split(',')
                            for num in numbers:
                                num = num.strip()
                                if '+' in num:
                                    try:
                                        changes['lines_added'] += int(num.replace('+', '').split()[0])
                                    except:
                                        pass
                                elif '-' in num:
                                    try:
                                        changes['lines_removed'] += int(num.replace('-', '').split()[0])
                                    except:
                                        pass
            
            # Generate concise summary
            summary_parts = []
            if changes['files_added']:
                file_list = changes['files_added'][:3]  # Show first 3 files
                if len(changes['files_added']) > 3:
                    summary_parts.append(f"add {', '.join(file_list)} and {len(changes['files_added'])-3} more")
                else:
                    summary_parts.append(f"add {', '.join(file_list)}")
            if changes['files_modified']:
                file_list = changes['files_modified'][:3]
                if len(changes['files_modified']) > 3:
                    summary_parts.append(f"update {', '.join(file_list)} and {len(changes['files_modified'])-3} more")
                else:
                    summary_parts.append(f"update {', '.join(file_list)}")
            if changes['files_deleted']:
                file_list = changes['files_deleted'][:3]
                if len(changes['files_deleted']) > 3:
                    summary_parts.append(f"remove {', '.join(file_list)} and {len(changes['files_deleted'])-3} more")
                else:
                    summary_parts.append(f"remove {', '.join(file_list)}")
            
            changes['summary'] = '; '.join(summary_parts)
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return changes
    
    def _generate_commit_message(self, changes: Dict[str, Any]) -> str:
        """Generate smart commit message based on git changes."""
        if not changes['files_changed']:
            return 'WIP'
        
        # Build context for AI (functionality only, no file names)
        context_parts = []
        
        # Don't include file names - focus on functionality
        if changes['lines_added'] > 0:
            context_parts.append(f"+{changes['lines_added']} lines added")
        if changes['lines_removed'] > 0:
            context_parts.append(f"-{changes['lines_removed']} lines removed")
        
        context = " | ".join(context_parts) if context_parts else ""
        
        # Detect what kind of changes (feature, fix, refactor, etc.)
        file_types = {}
        for f in changes['files_changed']:
            ext = os.path.splitext(f)[1]
            file_types[ext] = file_types.get(ext, 0) + 1
        
        # Get actual diff content to understand functionality
        diff_context = self._get_git_diff_context()
        
        # Determine likely commit type from changes and diff
        commit_type_hint = "chore"
        diff_lower = diff_context.lower()
        files_lower = ' '.join(changes['files_changed']).lower()
        
        if changes['files_added'] or 'add' in diff_lower or 'new' in diff_lower or 'implement' in diff_lower:
            commit_type_hint = "feat"
        elif any(word in files_lower or word in diff_lower for word in ['fix', 'bug', 'error', 'issue', 'resolve', 'repair']):
            commit_type_hint = "fix"
        elif any(word in diff_lower for word in ['test', 'spec', 'expect']):
            commit_type_hint = "test"
        elif any(word in files_lower or word in diff_lower for word in ['doc', 'readme', '.md']):
            commit_type_hint = "docs"
        elif any(word in diff_lower for word in ['refactor', 'simplify', 'clean', 'restructure']):
            commit_type_hint = "refactor"
        
        # Build descriptive prompt - focus on functionality, not files
        prompt_parts = []
        
        # Code diff context (if available) - prioritize functionality over file names
        if diff_context and len(diff_context) > 20:
            # Use the full diff context (it's already filtered for functionality)
            prompt_parts.append(f"Code changes:\n{diff_context}")
        elif context:
            # Remove file names from context
            context_clean = context
            # Remove lines that mention files
            context_clean = '\n'.join([line for line in context_clean.split('\n') if 'Files' not in line and 'files' not in line.lower()])
            if context_clean.strip():
                prompt_parts.append(f"Changes: {context_clean}")
        
        # If we have no context, try to get raw diff for analysis
        if not prompt_parts:
            try:
                diff_result = subprocess.run(['git', 'diff', '--cached', '-U3'],
                                           capture_output=True, text=True, timeout=3)
                if diff_result.returncode == 0 and diff_result.stdout:
                    raw_diff = diff_result.stdout
                    # Extract just the code changes (skip file headers)
                    code_lines = []
                    for line in raw_diff.split('\n')[:200]:
                        if line.startswith('+') and not line.startswith('+++') and not line.startswith('+@@'):
                            code = line[1:].strip()
                            if code and not code.startswith('#') and len(code) > 5:
                                # Skip file paths
                                if '/' not in code and not any(ext in code for ext in ['.py', '.js', '.log', '.txt', '.md']):
                                    code_lines.append(code[:100])
                    if code_lines:
                        prompt_parts.append(f"Code changes:\n" + '\n'.join(f"  + {line}" for line in code_lines[:15]))
            except:
                pass
        
        prompt_body = '\n'.join(prompt_parts) if prompt_parts else "No code changes detected"
        
        prompt = f"""Write a SPECIFIC commit message:

{prompt_body}

CRITICAL: The message MUST be SPECIFIC. Generic messages like "enhance functionality" or "add new feature" are REJECTED.

Format: "type: specific description"
- type: feat/fix/refactor/docs/test/chore
- description: MUST describe WHAT was actually implemented/fixed

REQUIREMENTS:
1. Look at the functions, classes, and operations listed above
2. Identify the SPECIFIC functionality - what does the code DO?
3. Use function names, method calls, and operations to understand purpose
4. Write a message describing the ACTUAL feature or fix

GOOD (SPECIFIC):
- "feat: add context-aware command completion with workflow learning"
- "fix: resolve model loading errors when Ollama server is unavailable"
- "refactor: improve error handling in completion pipeline with exception catching"
- "feat: implement smart commit message generation from git diff analysis"
- "fix: prevent traceback errors in Zsh plugin by adding error handling"

BAD (TOO GENERIC - REJECTED):
- "feat: add new functionality" ❌
- "feat: enhance completion functionality" ❌
- "feat: improve code" ❌
- "fix: fix bug" ❌
- "chore: update code" ❌

If the changes are about improving commit message generation, write: "feat: improve commit message generation with better diff analysis"
If the changes are about error handling, write: "fix: add error handling to prevent tracebacks"
If the changes are about functionality extraction, write: "feat: enhance diff analysis to extract meaningful functionality"

Write ONLY the commit message:"""
        
        try:
            # Use longer timeout for commit message generation (needs more time for quality)
            original_timeout = self.client.timeout
            self.client.timeout = 15  # Give more time for commit message generation
            
            try:
                # Ensure we use the fine-tuned model
                available_models = self.client.get_available_models()
                zsh_model = None
                for model in available_models:
                    if model.startswith("zsh-assistant"):
                        zsh_model = model
                        break
                model_to_use = zsh_model if zsh_model else self.model
                completion = self.client.generate_completion(
                    prompt, model_to_use, use_cache=False
                )
            finally:
                self.client.timeout = original_timeout
            
            # Extract commit message - clean and parse AI response
            import re
            completion_text = completion.strip()
            
            # Remove common prefixes
            completion_text = re.sub(r'^(Input|Output|input|output):\s*', '', completion_text, flags=re.IGNORECASE)
            
            # Split into lines and process
            lines = completion_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Remove markdown formatting
                line = line.replace('```', '').replace('`', '').strip()
                
                # Remove "Conventional Commit Message:" labels
                line = re.sub(r'^\s*Conventional Commit Message:\s*', '', line, flags=re.IGNORECASE)
                line = re.sub(r'^\s*Commit Message:\s*', '', line, flags=re.IGNORECASE)
                
                # Skip explanatory lines
                if (line.startswith(('Generate', 'Format:', 'Examples:', 'Changes:', 'Project:', 'File types:', 'Here', 'Sure', 'This')) or
                    line.startswith(('1.', '2.', '3.', '- ', '* ', '•')) or
                    len(line) < 5):
                    continue
                
                # Look for commit message format (type: subject)
                if ':' in line[:80]:
                    line = line.strip()
                    line = re.sub(r'\s*\([^)]*\)\s*$', '', line)
                    line = re.sub(r'\s*\(Added by[^)]*\)', '', line)
                    if len(line) > 8 and line.count(':') >= 1:
                        if ':' in line:
                            parts = line.split(':', 1)
                            commit_type = parts[0].strip().lower()
                            subject = parts[1].strip() if len(parts) > 1 else ""
                            
                            # Reject generic messages
                            subject_lower = subject.lower().strip()
                            generic_patterns = [
                                'add new functionality', 'enhance functionality', 'improve functionality',
                                'update functionality', 'add functionality', 'enhance completion functionality',
                                'improve code', 'update code', 'add feature', 'new feature', 'update feature',
                                'enhance completion', 'improve completion', 'update completion'
                            ]
                            if any(pattern in subject_lower for pattern in generic_patterns):
                                logger.warning(f"Rejected generic commit message: {subject}")
                                continue  # Skip this message and try next line
                            
                            # Validate commit type
                            valid_types = ['feat', 'fix', 'refactor', 'docs', 'test', 'chore', 'perf', 'style', 'build', 'ci']
                            if commit_type not in valid_types:
                                # Try to infer from subject
                                subject_lower = subject.lower()
                                if any(word in subject_lower for word in ['add', 'new', 'feature', 'implement', 'create']):
                                    commit_type = "feat"
                                elif any(word in subject_lower for word in ['fix', 'bug', 'error', 'issue', 'resolve']):
                                    commit_type = "fix"
                                elif any(word in subject_lower for word in ['refactor', 'simplify', 'restructure']):
                                    commit_type = "refactor"
                                else:
                                    commit_type = "feat"  # Default to feat if seems like new functionality
                            
                            # Clean subject - remove quotes, extra spaces
                            subject = subject.strip('"').strip("'").strip()
                            
                            # Validate subject has meaningful content
                            if len(subject) >= 5:
                                # Reject generic messages
                                subject_lower = subject.lower().strip()
                                rejected_exact = ['message', 'commit message', 'commit']
                                # Check for generic patterns (both exact and partial matches)
                                generic_keywords = ['enhance functionality', 'improve functionality', 'add functionality', 'update functionality', 'add new functionality', 'enhance completion', 'improve completion', 'update completion', 'add feature', 'new feature', 'update feature', 'improve code', 'update code']
                                generic_words = ['enhance', 'improve', 'update', 'add']  # If these are the main verbs without specifics
                                
                                is_generic = any(pattern in subject_lower for pattern in generic_keywords)
                                # Also check if it's just "verb + generic noun" without specifics
                                if not is_generic and len(subject_lower.split()) <= 3:
                                    words = subject_lower.split()
                                    if len(words) >= 2 and words[0] in generic_words and words[1] in ['functionality', 'feature', 'code', 'completion', 'code', 'implementation']:
                                        is_generic = True
                                
                                is_placeholder = subject_lower in rejected_exact or 'commit message' in subject_lower
                                
                                if (not is_generic and not is_placeholder and
                                    len(subject.strip()) >= 10):  # Require at least 10 chars for specificity
                                    if len(subject) > 72:
                                        subject = subject[:69] + '...'
                                    return f"{commit_type}: {subject}"
                                else:
                                    logger.warning(f"Rejected generic/placeholder commit message: {subject}")
                            # Continue searching if validation failed
            
            # Fallback: generate descriptive message from diff context
            if diff_context and len(diff_context) > 20:
                # Extract key_changes from diff_context string
                diff_lower = diff_context.lower()
                
                # Determine type and create message based on functionality
                commit_type = "feat"
                subject_parts = []
                
                # Check for specific functionality indicators
                if '_get_git_diff' in diff_context or 'get_git_diff' in diff_context:
                    commit_type = "feat"
                    subject_parts.append("add git diff parsing to extract code changes")
                
                if 'commit message' in diff_lower or 'generate_commit' in diff_context or 'generate commit' in diff_lower:
                    subject_parts.append("improve commit message generation")
                    if 'diff' in diff_lower or 'context' in diff_lower:
                        subject_parts.append("enhance commit messages with diff analysis")
                
                # Extract functionality from diff context
                if ('function' in diff_lower or 'def ' in diff_lower) and not subject_parts:
                    if 'diff' in diff_lower or 'git' in diff_lower or 'context' in diff_lower:
                        subject_parts.append("enhance git diff analysis")
                    elif 'commit' in diff_lower:
                        subject_parts.append("improve commit message generation")
                    else:
                        subject_parts.append("add new functionality")
                
                if 'class' in diff_lower or 'extract' in diff_lower:
                    if commit_type != "feat":
                        commit_type = "refactor"
                        subject_parts.append("refactor code structure")
                
                if ('parse' in diff_lower or 'extract' in diff_lower or 'analyze' in diff_lower) and not subject_parts:
                    subject_parts.append("improve code analysis and extraction")
                
                # Check for function names mentioned
                if 'Functions:' in diff_context:
                    # Extract function names from the context
                    func_section = diff_context.split('Functions:')
                    if len(func_section) > 1:
                        func_names = func_section[1].split(',')[0].strip()
                        if func_names and len(func_names) < 50:
                            if 'diff' in func_names.lower() or 'git' in func_names.lower():
                                subject_parts.append(f"add {func_names.replace('_', ' ')} functionality")
                            elif 'commit' in func_names.lower():
                                subject_parts.append("enhance commit message generation")
                
                # Create final message - use most specific one
                if subject_parts:
                    # Prefer messages with "git diff" or "commit message" keywords
                    preferred = [s for s in subject_parts if 'diff' in s.lower() or 'commit' in s.lower()]
                    subject = preferred[0] if preferred else subject_parts[0]
                    
                    # Ensure it's descriptive and not too short
                    if len(subject) < 15:
                        # Make it more descriptive
                        if 'git' in subject.lower():
                            subject = "enhance git diff analysis for commit messages"
                        elif 'commit' in subject.lower():
                            subject = "improve commit message generation from code changes"
                        else:
                            subject = f"add {subject} functionality"
                    
                    # Limit to 72 chars
                    if len(subject) > 72:
                        subject = subject[:69] + '...'
                    return f"{commit_type}: {subject}"
            
            # Fallback: generate from file changes (avoid file counts)
            if changes['files_changed']:
                # Try to infer functionality from file names
                file_names = [os.path.basename(f) for f in changes['files_changed']]
                file_names_lower = ' '.join(file_names).lower()
                
                commit_type = "feat"
                if any(word in file_names_lower for word in ['fix', 'bug', 'error']):
                    commit_type = "fix"
                elif any(word in file_names_lower for word in ['refactor', 'clean']):
                    commit_type = "refactor"
                elif any(word in file_names_lower for word in ['test']):
                    commit_type = "test"
                elif any(word in file_names_lower for word in ['doc', 'readme']):
                    commit_type = "docs"
                
                # Create message based on primary file - but be more specific
                primary_file = file_names[0] if file_names else "code"
                file_base = primary_file.replace('.py', '').replace('_', ' ')
                
                # Try to infer functionality from file name
                if 'completer' in primary_file.lower():
                    return f"{commit_type}: improve command completion with better context analysis"
                elif 'train' in primary_file.lower():
                    return f"{commit_type}: improve training process with better data handling"
                elif 'lora' in primary_file.lower():
                    return f"{commit_type}: update LoRA training workflow with improved configuration"
                elif 'enhanced' in primary_file.lower():
                    return f"{commit_type}: enhance completion logic with improved functionality extraction"
                else:
                    # Don't use generic "update functionality" - return None to use original command
                    logger.warning(f"Could not generate specific commit message for {primary_file}")
                    return None
            
            return None  # Don't return generic message
            
        except Exception as e:
            logger.warning(f"Failed to generate commit message: {e}")
            # Fallback to simple message
            if changes['summary']:
                return f"{changes['summary'].strip()}"
            return "WIP"
    
    def get_smart_commit_message(self, command: str = None) -> Optional[str]:
        """Get smart commit message suggestion based on current git changes."""
        try:
            changes = self._analyze_git_changes()
            
            if not changes['files_changed']:
                logger.debug("No git changes found for smart commit message")
                return None
            
            logger.info(f"Generating smart commit message for {len(changes['files_changed'])} changed files")
            commit_message = self._generate_commit_message(changes)
            
            # Clean up the message - remove any unwanted prefixes/suffixes
            if commit_message:
                import re
                # Remove any "Input:" or "Output:" labels
                commit_message = re.sub(r'^(Input|Output|input|output):\s*', '', commit_message, flags=re.IGNORECASE)
                commit_message = commit_message.strip()
                
                # Only reject obvious placeholders
                rejected_exact = ['wip', 'commit message', 'message']
                if commit_message.lower().strip() in rejected_exact:
                    logger.debug(f"Rejected generic commit message: {commit_message}")
                    return None
                
                # If it's just a type without subject, reject
                if ':' not in commit_message:
                    # If it's just "update", "changes", etc without colon, reject
                    if commit_message.lower().strip() in ['update', 'changes', 'fix', 'feat', 'chore']:
                        logger.debug(f"Rejected too generic commit message (no subject): {commit_message}")
                        return None
                
                # Validate subject if it has colon
                if ':' in commit_message:
                    subject = commit_message.split(':', 1)[1].strip()
                    if len(subject) < 3:  # Reduced from 5 to be less strict
                        logger.debug(f"Rejected commit message with too short subject: {commit_message}")
                        return None
                    # Only reject obvious placeholders in subject
                    if subject.lower().strip() in ['message', 'commit message']:
                        logger.debug(f"Rejected commit message with placeholder subject: {commit_message}")
                        return None
                
                logger.info(f"✅ Generated smart commit message: {commit_message}")
                return commit_message
            else:
                logger.warning("_generate_commit_message returned empty result")
        except Exception as e:
            logger.warning(f"Failed to generate commit message: {e}", exc_info=True)
            return None
        
        return None
    
    def get_completion(self, command: str, use_cache: bool = True) -> str:
        """Get enhanced completion using fine-tuned model."""
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
            self.history = self.history[-10:]
        
        self.project_context = self._detect_project_context()
        
        # Prioritize fine-tuned zsh-assistant model
        model_to_use = self.model
        try:
            available_models = self.client.get_available_models()
            # Check for zsh-assistant with or without :latest tag
            zsh_assistant_model = None
            for model in available_models:
                if model.startswith("zsh-assistant"):
                    zsh_assistant_model = model
                    break
            
            if zsh_assistant_model:
                model_to_use = zsh_assistant_model
                logger.debug(f"Using fine-tuned model: {model_to_use}")
        except Exception:
            pass
        
        if command.strip() == "git":
            try:
                # Check if we're in a git repo and get status
                subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], 
                             check=True, capture_output=True, text=True, timeout=2)
                
                # Check for unstaged changes
                diff_result = subprocess.run(['git', 'diff', '--name-only'],
                                           capture_output=True, text=True, timeout=2)
                unstaged_files = [f.strip() for f in diff_result.stdout.strip().split('\n') if f.strip()]
                
                # Check for staged changes
                staged_result = subprocess.run(['git', 'diff', '--cached', '--name-only'],
                                             capture_output=True, text=True, timeout=2)
                staged_files = [f.strip() for f in staged_result.stdout.strip().split('\n') if f.strip()]
                
                # Store git context in project_context for prompt building
                if unstaged_files:
                    self.project_context['git_unstaged'] = len(unstaged_files)
                if staged_files:
                    self.project_context['git_staged'] = len(staged_files)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        # Special handling for git commit commands - ALWAYS prioritize smart commit messages
        # Skip training data check for git commit commands to ensure smart commit runs
        if (command.strip().startswith('git comm') or 'git commit' in command) and not ('-m' in command or '--message' in command):
            # Try to generate smart commit message FIRST (contextual and better)
            smart_message = None
            try:
                smart_message = self.get_smart_commit_message(command)
                logger.info(f"Smart commit returned: {smart_message}")
            except Exception as e:
                logger.warning(f"Smart commit message generation failed: {e}", exc_info=True)
            
            # Use smart message if we got something useful
            if smart_message and smart_message.strip():
                # Reject only actual placeholder messages
                smart_lower = smart_message.lower().strip()
                # Reject if it's exactly a placeholder or contains "commit message" as placeholder
                rejected_exact = ['commit message', 'message', 'wip']
                # Also reject if it's just "commit message" in quotes or as a standalone phrase
                is_placeholder = (smart_lower in rejected_exact or 
                                'commit message' in smart_lower or
                                smart_message.strip() == '"commit message"' or
                                smart_message.strip() == "'commit message'")
                
                if (not is_placeholder and
                    len(smart_lower) > 8 and
                    ':' in smart_message and
                    not smart_lower.startswith('commit message')):
                    result = f'git commit -m "{smart_message}"'
                    self._save_command(command, result, {
                        'project_type': self.project_context['project_type'],
                        'source': 'smart_commit'
                    })
                    logger.info(f"Using smart commit: {smart_message}")
                    return result
                else:
                    logger.warning(f"Rejected placeholder commit message: {smart_message}")
            
            # If smart commit didn't work, try AI completion as fallback (not training data)
            logger.info("Smart commit failed, trying AI completion fallback...")
            try:
                prompt = self._build_enhanced_prompt(command)
                original_timeout = self.client.timeout
                self.client.timeout = 10
                try:
                    # Use fine-tuned model
                    available_models = self.client.get_available_models()
                    zsh_model = None
                    for model in available_models:
                        if model.startswith("zsh-assistant"):
                            zsh_model = model
                            break
                    model_to_use = zsh_model if zsh_model else self.model
                    ai_completion = self.client.generate_completion(prompt, model_to_use, use_cache=False)
                    if ai_completion:
                        # Extract commit message from AI response
                        import re
                        lines = ai_completion.strip().split('\n')
                        for line in lines:
                            line = line.strip()
                            line_lower = line.lower()
                            # REJECT placeholder commit messages - be very strict
                            if ('commit message' in line_lower or
                                line_lower.strip() == 'message' or
                                line_lower.strip() == '"commit message"' or
                                line_lower.strip() == "'commit message'" or
                                line_lower.startswith('commit message')):
                                logger.warning(f"Rejected placeholder in AI fallback: {line}")
                                continue
                            if ':' in line and len(line) > 10 and not line.startswith(('To', 'Here', 'Sure', 'Format', 'Complete', 'The command')):
                                commit_msg = line.split('\n')[0].strip()
                                # Clean up
                                commit_msg = re.sub(r'^(feat|fix|chore|docs|refactor|test|style|perf|build|ci):\s*', '', commit_msg, count=1, flags=re.IGNORECASE)
                                commit_msg_lower = commit_msg.lower()
                                # Reject if it's still a placeholder
                                if (len(commit_msg) > 5 and 
                                    'commit message' not in commit_msg_lower and
                                    commit_msg_lower.strip() != 'message' and
                                    not commit_msg_lower.startswith('commit message')):
                                    result = f'git commit -m "{commit_msg}"'
                                    self._save_command(command, result, {
                                        'project_type': self.project_context['project_type'],
                                        'source': 'ai_fallback'
                                    })
                                    return result
                                else:
                                    logger.warning(f"Rejected placeholder commit message in fallback: {commit_msg}")
                finally:
                    self.client.timeout = original_timeout
            except Exception as e:
                logger.debug(f"AI fallback failed: {e}")
            
            # Don't fallback to training data for git commit - it has "commit message" placeholder
            # Return original command if all AI attempts failed (better than placeholder)
            logger.warning("All commit message generation attempts failed, returning original command")
            return command
        
        try:
            prompt = self._build_enhanced_prompt(command)
            original_timeout = self.client.timeout
            self.client.timeout = 5
            
            try:
                completion = self.client.generate_completion(
                    prompt, model_to_use, use_cache=use_cache
                )
            except Exception as e:
                logger.debug(f"AI completion error: {e}")
                completion = None
            finally:
                self.client.timeout = original_timeout
            
            # Process AI completion if we got one
            if completion:
                try:
                    lines = completion.strip().split('\n')
                    for line in lines:
                        line = line.strip().replace('```', '').strip()
                        
                        # Reject any line containing "commit message" as placeholder
                        line_lower = line.lower()
                        if ('commit message' in line_lower or 
                            line_lower.strip() == 'message' or
                            line_lower.strip() == '"commit message"' or
                            line_lower.strip() == "'commit message'"):
                            continue
                        
                        reject_prefixes = ('Complete command:', 'The command', 'You should', 'Run:', 'To complete', 'This will', 'You can', 'Enter', 'Note:', 'Suggestion:', 'Output:', 'Context:', 'Project:')
                        if line.startswith(reject_prefixes) or any(phrase in line.lower() for phrase in ('the logical', 'next step', 'you should', 'complete command:')):
                            continue
                        
                        if (line and len(line) > len(command) and 
                            not line.startswith(('To complete', 'This will', 'You can', 'Run:', 'Note:', 'Suggestion:', 'Output:', 'Context:', 'Project:')) and
                            not line.startswith(('1.', '2.', '3.', '- ', '* ')) and
                            not line.endswith(':') and not line.startswith('$') and
                            not line.startswith('`') and not line.endswith('`') and
                            '|' not in line[:20] and
                            (command.lower() in line.lower() or line.startswith(command.split()[0] if command.split() else command)) and
                            (line[0].isalpha() or line[0] in './')):
                            result = line
                            git_info = self._get_git_info()
                            git_branch = None
                            if git_info and 'Branch:' in git_info:
                                try:
                                    git_branch = git_info.split('Branch:')[1].strip().split('\n')[0]
                                except:
                                    pass
                            self._save_command(command, result, {
                                'project_type': self.project_context['project_type'],
                                'git_branch': git_branch,
                                'source': 'ai'
                            })
                            logger.debug(f"AI completion: {command} -> {result}")
                            return result
                except Exception as e:
                    logger.warning(f"AI completion processing failed: {e}")
        except Exception as e:
            logger.warning(f"AI completion failed: {e}")
        
        # Don't use training data fallback for git commit - it likely has "commit message" placeholder
        if not (command.strip().startswith('git comm') or 'git commit' in command):
            fallback_completion = self._get_fallback_completion(command)
            if fallback_completion:
                # Double-check for "commit message" placeholder
                if 'commit message' in fallback_completion.lower() and '"commit message"' in fallback_completion:
                    logger.warning(f"Rejected placeholder from fallback: {fallback_completion}")
                else:
                    logger.debug(f"AI failed, using training data fallback: {command} -> {fallback_completion}")
                    self._save_command(command, fallback_completion, {
                        'project_type': self.project_context['project_type'],
                        'source': 'training_data'
                    })
                    return fallback_completion
        
        # Return original command if no completion found (better than placeholder)
        return command

