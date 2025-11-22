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
            prompt_template = """Complete: {command}

Suggestions:"""
        else:
            prompt_template = """Complete this command:

{command}

Output:"""
        
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
        """Get completion using fine-tuned zsh-assistant model."""
        # Update history
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
            # Keep only last 10 commands
            self.history = self.history[-10:]
        
        model_to_use = self.model
        if self.model != "zsh-assistant":
            try:
                available_models = self.client.get_available_models()
                if "zsh-assistant" in available_models:
                    model_to_use = "zsh-assistant"
                    logger.debug("Using fine-tuned zsh-assistant model")
            except Exception:
                pass
        
        try:
            prompt = f"{command}"
            
            completion = self.client.generate_completion(
                prompt, model_to_use, use_cache=use_cache
            )
            
            # Extract the completion from the response
            import re
            
            # First, clean up common prefixes/suffixes
            completion_text = completion.strip()
            
            # Handle multiline responses - look for Output: line first
            lines = completion_text.split('\n')
            output_line = None
            
            for line in lines:
                line_stripped = line.strip()
                # Look for Output: line
                if re.match(r'^(Output|output):', line_stripped, re.IGNORECASE):
                    output_line = re.sub(r'^(Output|output):\s*', '', line_stripped, flags=re.IGNORECASE).strip()
                    break
            
            # Use Output line if found, otherwise process all lines
            if output_line:
                candidate_lines = [output_line]
            else:
                candidate_lines = [l.strip() for l in lines]
            
            # Process each candidate line
            for line in candidate_lines:
                if not line or len(line) <= len(command):
                    continue
                
                # Remove Input:/Output: labels
                line = re.sub(r'^(Input|Output|input|output):\s*', '', line, flags=re.IGNORECASE).strip()
                
                # Remove "(Added by...)" suffixes
                if '"' in line:
                    parts = line.split('"')
                    if len(parts) >= 3:
                        parts[1] = re.sub(r'\s*\(Added by[^)]*\)', '', parts[1])
                        parts[1] = re.sub(r'^\s*Conventional Commit Message:\s*', '', parts[1], flags=re.IGNORECASE).strip()
                        if not parts[1]:
                            parts[1] = "commit message"
                        line = '"'.join(parts)
                else:
                    line = re.sub(r'\s*\(Added by[^)]*\)', '', line)
                    line = re.sub(r'\s*Conventional Commit Message:.*$', '', line, flags=re.IGNORECASE)
                
                line = line.strip()
                
                # Look for lines that look like actual commands
                if (line and 
                    len(line) > len(command) and
                    ' ' in line and
                    not line.startswith(('To complete', 'This will', 'You can', 'Enter', 'Run:', 'Note:', '```', 'Environment:', 'User:', 'Host:', 'Directory:', 'Recent:', 'Replace', 'This will launch', 'You can now', 'This will display', 'Suggestion:', 'Implement:', 'Provide', 'Git commit is', 'Remember,', 'By following', 'Start by', 'Next,', 'After that', 'The command', 'You are a', 'Complete the command', 'Command to complete', 'Sure,', 'Here', 'This flag', 'This option', 'This command', 'Input:', 'Output:', 'input:', 'output:')) and
                    not line.startswith(('1.', '2.', '3.', '4.', '5.', '- ', '* ', '• ', '6.', '7.', '8.', '9.', '10.')) and
                    not line.endswith(':') and
                    not line.startswith('$') and
                    not line.startswith('`') and
                    not line.endswith('`')):
                    logger.debug(f"Using fine-tuned model ({model_to_use}): {line}")
                    return line
                    
        except Exception as e:
            logger.debug(f"Model completion failed: {e}")
        
        fallback_completion = self._get_fallback_completion(command)
        if fallback_completion:
            logger.debug(f"Using training data fallback: {fallback_completion}")
            return fallback_completion
        
        return command
    
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
            # Skip empty lines, numbered lists, and explanatory text
            if (line and 
                not line.startswith(('1.', '2.', '3.', '4.', '5.', '- ', '* ', '• ')) and
                not line.startswith(('To complete', 'This will', 'You can', 'Enter', 'Run:', 'Note:', '```', 'Environment:', 'User:', 'Host:', 'Directory:', 'Recent:', 'Replace', 'This will launch', 'You can now', 'This will display')) and
                len(line) > len(command) and
                not line.endswith(':')):
                
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
    
    def _get_fallback_completion(self, command: str) -> Optional[str]:
        """Get completion from training data as fallback."""
        try:
            import json
            training_file = os.path.join(os.path.dirname(__file__), '..', 'training', 'zsh_training_data.jsonl')
            if os.path.exists(training_file):
                with open(training_file, 'r') as f:
                    for line in f:
                        data = json.loads(line.strip())
                        # Try exact match first
                        if data['input'].lower() == command.lower():
                            output = data['output']
                            # Clean up output - remove any "Output:" labels
                            output = output.replace("Output:", "").replace("output:", "").strip()
                            return output
                        # Try prefix match (but skip "git" and "git comm" - they're handled specially in EnhancedCompleter)
                        elif (command.strip().lower() not in ("git", "git comm") and 
                              (command.lower() in data['input'].lower() or data['input'].lower().startswith(command.lower()))):
                            output = data['output']
                            output = output.replace("Output:", "").replace("output:", "").strip()
                            return output
        except Exception:
            pass
        return None