import os
import subprocess
from typing import List, Optional, Dict, Any
from .client import OllamaClient
import logging

logger = logging.getLogger(__name__)

class ModelCompleter:
    """Main completion class that handles command completion logic."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", 
                 model: str = "llama2", config: Optional[Dict] = None):
        self.config = config or {}
        timeout = self.config.get('ollama', {}).get('timeout', 30)
        self.client = OllamaClient(ollama_url, timeout=timeout)
        self.model = model
        self.history: List[str] = []
        
    def build_prompt(self, command: str, context: Optional[Dict] = None, 
                   for_ui: bool = False) -> str:
        """Build a context-aware prompt for completion."""
        current_dir = os.getcwd()
        username = os.getenv('USER', '')
        hostname = os.getenv('HOSTNAME', '')
        
        # Get git status if available
        git_info = self._get_git_info()
        
        # Get recent command history (last 5 commands)
        recent_commands = self.history[-5:] if self.history else []
        
        if for_ui:
            prompt_template = """As a command line expert, please provide 3-5 diverse completion suggestions for:

Environment:
- User: {username}
- Host: {hostname}
- Directory: {current_dir}
{git_info}
- Recent: {recent_commands}

Input: {command}

Provide only the completion commands, one per line, without numbers or explanations."""
        else:
            prompt_template = """Complete this command:

{command}

Provide only the completed command, nothing else."""
        
        prompt = prompt_template.format(
            username=username,
            hostname=hostname,
            current_dir=current_dir,
            git_info=git_info,
            recent_commands=", ".join(recent_commands),
            command=command
        )
        
        return prompt
    
    def _get_git_info(self) -> str:
        """Get git repository information."""
        try:
            # Check if we're in a git repo
            subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], 
                         check=True, capture_output=True, text=True)
            
            # Get current branch
            branch_result = subprocess.run(['git', 'branch', '--show-current'],
                                         capture_output=True, text=True)
            branch = branch_result.stdout.strip()
            
            # Get status
            status_result = subprocess.run(['git', 'status', '--short'],
                                         capture_output=True, text=True)
            status = status_result.stdout.strip()
            
            git_info = f"- Git Branch: {branch}\n- Git Status: {status}" if status else f"- Git Branch: {branch}"
            return git_info
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""
    
    def get_completion(self, command: str, use_cache: bool = True) -> str:
        """Get completion for the given command."""
        # Update history
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
            # Keep only last 10 commands
            self.history = self.history[-10:]
        
        prompt = self.build_prompt(command)
        completion = self.client.generate_completion(
            prompt, self.model, use_cache=use_cache
        )
        
        # Basic sanitization
        completion = completion.strip()
        if completion and not completion.startswith(command):
            # If the completion doesn't start with the command, prepend it
            completion = command + completion
        
        return completion
    
    def get_suggestions(self, command: str, max_suggestions: int = 3) -> List[str]:
        """Get multiple completion suggestions optimized for UI."""
        # Update history
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
            self.history = self.history[-10:]
        
        prompt = self.build_prompt(command, for_ui=True)
        completion = self.client.generate_completion(
            prompt, self.model, use_cache=False
        )
        
        # Parse multiple suggestions from response
        suggestions = []
        lines = completion.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('1.', '2.', '3.', '4.', '5.', '- ')):
                # Clean up the suggestion
                suggestion = line
                if not suggestion.startswith(command):
                    suggestion = command + suggestion
                
                # Remove any explanatory text after the command
                if '#' in suggestion:
                    suggestion = suggestion.split('#')[0].strip()
                if '//' in suggestion:
                    suggestion = suggestion.split('//')[0].strip()
                
                if suggestion and suggestion not in suggestions:
                    suggestions.append(suggestion)
                
                if len(suggestions) >= max_suggestions:
                    break
        
        # If we didn't get enough suggestions, generate more
        if len(suggestions) < max_suggestions:
            for i in range(max_suggestions - len(suggestions)):
                alt_completion = self.client.generate_completion(
                    prompt + f"\n\nProvide another different suggestion:",
                    self.model, 
                    use_cache=False
                )
                alt_suggestion = alt_completion.strip()
                if alt_suggestion and alt_suggestion not in suggestions:
                    if not alt_suggestion.startswith(command):
                        alt_suggestion = command + alt_suggestion
                    suggestions.append(alt_suggestion)
        
        return suggestions[:max_suggestions]