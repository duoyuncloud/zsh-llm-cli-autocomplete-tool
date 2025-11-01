#!/usr/bin/env python3
"""
Enhanced ModelCompleter with advanced developer features:
- Persistent user history tracking
- Context-aware completions (project type, files, git status)
- Personalized suggestions based on user patterns
- Developer-specific intelligence
"""

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
    """Enhanced completer with developer-focused features."""
    
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
        """Build enhanced prompt with developer context."""
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
        
        # User patterns
        if patterns['similar_commands']:
            context_parts.append(f"Recent similar: {patterns['similar_commands'][-1]}")
        
        # Recent files
        if self.project_context['files']:
            recent_files = ', '.join(self.project_context['files'][:3])
            context_parts.append(f"Recent files: {recent_files}")
        
        context_str = " | ".join(context_parts)
        
        # Build enhanced prompt
        prompt = f"""{command}"""
        
        if context_str:
            prompt += f"\n\nContext: {context_str}"
        
        # Add personalization hint
        if patterns['frequent_commands'] and command.split()[0] in patterns['frequent_commands']:
            prompt += "\n(User frequently uses this command type)"
        
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
                         check=True, capture_output=True, text=True)
            
            # Get both staged and unstaged changes
            status_result = subprocess.run(['git', 'status', '--short'],
                                         capture_output=True, text=True)
            status_output = status_result.stdout.strip()
            
            # Also check unstaged changes
            diff_unstaged = subprocess.run(['git', 'diff', '--name-only'],
                                          capture_output=True, text=True)
            unstaged_files = [f.strip() for f in diff_unstaged.stdout.strip().split('\n') if f.strip()]
            
            if not status_output and not unstaged_files:
                return changes
            
            # Parse status output
            for line in status_output.split('\n'):
                if not line.strip():
                    continue
                
                status = line[:2]
                filename = line[3:].strip()
                
                if status.startswith('A'):
                    changes['files_added'].append(filename)
                elif status.startswith('D'):
                    changes['files_deleted'].append(filename)
                elif status.startswith('M') or status.startswith('R'):
                    changes['files_modified'].append(filename)
                
                changes['files_changed'].append(filename)
            
            # Get diff stats (try staged first, then unstaged)
            diff_result = subprocess.run(['git', 'diff', '--cached', '--stat'],
                                        capture_output=True, text=True)
            diff_output = diff_result.stdout if diff_result.returncode == 0 else ""
            
            # If no staged changes, check unstaged
            if not diff_output.strip():
                diff_result = subprocess.run(['git', 'diff', '--stat'],
                                            capture_output=True, text=True)
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
            
            # Generate summary
            if changes['files_added']:
                changes['summary'] += f"Added {len(changes['files_added'])} file(s). "
            if changes['files_modified']:
                changes['summary'] += f"Modified {len(changes['files_modified'])} file(s). "
            if changes['files_deleted']:
                changes['summary'] += f"Deleted {len(changes['files_deleted'])} file(s). "
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return changes
    
    def _generate_commit_message(self, changes: Dict[str, Any]) -> str:
        """Generate smart commit message based on git changes."""
        if not changes['files_changed']:
            return 'WIP'
        
        # Build context for AI
        context_parts = []
        
        if changes['files_added']:
            context_parts.append(f"Added: {', '.join(changes['files_added'][:5])}")
        if changes['files_modified']:
            context_parts.append(f"Modified: {', '.join(changes['files_modified'][:5])}")
        if changes['files_deleted']:
            context_parts.append(f"Deleted: {', '.join(changes['files_deleted'][:5])}")
        
        if changes['lines_added'] > 0:
            context_parts.append(f"+{changes['lines_added']} lines")
        if changes['lines_removed'] > 0:
            context_parts.append(f"-{changes['lines_removed']} lines")
        
        context = " | ".join(context_parts)
        
        # Detect what kind of changes (feature, fix, refactor, etc.)
        file_types = {}
        for f in changes['files_changed']:
            ext = os.path.splitext(f)[1]
            file_types[ext] = file_types.get(ext, 0) + 1
        
        # Build prompt for commit message generation
        prompt = f"""Generate a concise, professional git commit message following conventional commits format.

Changes: {context}

Project: {self.project_context['project_type']}
File types: {', '.join(file_types.keys())}

Format: <type>(<scope>): <subject>

Examples:
- feat: add user authentication
- fix: resolve memory leak in parser
- refactor: simplify error handling
- docs: update API documentation
- test: add unit tests for utils

Generate only the commit message, no explanations:"""
        
        try:
            completion = self.client.generate_completion(
                prompt, self.model, use_cache=False
            )
            
            # Extract commit message
            lines = completion.strip().split('\n')
            for line in lines:
                line = line.strip()
                # Remove markdown formatting
                line = line.replace('```', '').strip()
                
                # Look for commit message format
                if (line and 
                    len(line) > 5 and
                    not line.startswith(('Generate', 'Format:', 'Examples:', 'Changes:', 'Project:', 'File types:')) and
                    not line.startswith(('1.', '2.', '3.', '- ', '* ', '•')) and
                    ':' in line[:50]):  # Commit messages usually have format "type: message"
                    # Clean up
                    if line.startswith('`'):
                        line = line[1:]
                    if line.endswith('`'):
                        line = line[:-1]
                    return line.strip()
            
            # Fallback: generate simple message
            if changes['summary']:
                return f"{changes['summary'].strip()}"
            return "Update files"
            
        except Exception as e:
            logger.warning(f"Failed to generate commit message: {e}")
            # Fallback to simple message
            if changes['summary']:
                return f"{changes['summary'].strip()}"
            return "WIP"
    
    def get_smart_commit_message(self, command: str = None) -> Optional[str]:
        """Get smart commit message suggestion based on current git changes."""
        changes = self._analyze_git_changes()
        
        if not changes['files_changed']:
            return None
        
        commit_message = self._generate_commit_message(changes)
        return commit_message
    
    def get_completion(self, command: str, use_cache: bool = True) -> str:
        """Get enhanced completion with smart commit message support."""
        # Update history
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
            self.history = self.history[-10:]
        
        # Refresh project context
        self.project_context = self._detect_project_context()
        
        # ALWAYS check training data first for speed
        fallback_completion = self._get_fallback_completion(command)
        
        # Special handling for git commit commands
        if (command.strip().startswith('git comm') or 'git commit' in command) and not ('-m' in command or '--message' in command):
            # If we have training data, use it immediately
            if fallback_completion:
                self._save_command(command, fallback_completion, {
                    'project_type': self.project_context['project_type'],
                    'source': 'training_data'
                })
                return fallback_completion
            
            # Try to generate smart commit message (with fast timeout)
            try:
                smart_message = self.get_smart_commit_message(command)
                if smart_message:
                    result = f'git commit -m "{smart_message}"'
                    self._save_command(command, result, {
                        'project_type': self.project_context['project_type'],
                        'source': 'smart_commit'
                    })
                    return result
            except Exception:
                pass
        
        # For all commands: use training data if available (instant)
        if fallback_completion:
            self._save_command(command, fallback_completion, {
                'project_type': self.project_context['project_type'],
                'source': 'training_data'
            })
            return fallback_completion
        
        # Try AI only if no training data match, with very short timeout
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
                completion = None
            finally:
                self.client.timeout = original_timeout
            
            # Process AI completion if we got one
            if completion:
                try:
                    lines = completion.strip().split('\n')
                    for line in lines:
                        line = line.strip().replace('```', '').strip()
                        if (line and len(line) > len(command) and ' ' in line and
                            not line.startswith(('To complete', 'This will', 'You can', 'Enter', 'Run:', 'Note:', 'Environment:', 'User:', 'Host:', 'Directory:', 'Recent:', 'Replace', 'This will launch', 'You can now', 'This will display', 'Suggestion:', 'Implement:', 'Provide', 'Git commit is', 'Remember,', 'By following', 'Start by', 'Next,', 'After that', 'The command', 'You are a', 'Complete the command', 'Command to complete', 'Sure,', 'Here', 'This flag', 'This option', 'This command', 'Context:', 'Project:', 'Git branch:', 'Recent files:', 'User frequently')) and
                            not line.startswith(('1.', '2.', '3.', '4.', '5.', '- ', '* ', '• ')) and
                            not line.endswith(':') and not line.startswith('$') and
                            not line.startswith('`') and not line.endswith('`') and
                            '|' not in line[:20]):
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
                            return result
                except Exception as e:
                    logger.warning(f"AI completion processing failed: {e}")
        except Exception as e:
            logger.warning(f"AI completion failed: {e}")
        
        # Return original command if no completion found
        return command

