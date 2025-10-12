#!/usr/bin/env python3
"""Prepare comprehensive Zsh training data for LoRA fine-tuning."""

import json
import os
from typing import List, Dict
import argparse

class ZshDataPreparer:
    def __init__(self):
        self.training_data = []
    
    def generate_git_commands(self) -> List[Dict[str, str]]:
        """Generate Git command patterns."""
        return [
            {"input": "git status", "output": "git status"},
            {"input": "git add ", "output": "git add ."},
            {"input": "git commit -m ", "output": "git commit -m \"feat: initial commit\""},
            {"input": "git push ", "output": "git push origin main"},
            {"input": "git pull ", "output": "git pull origin develop"},
            {"input": "git checkout ", "output": "git checkout -b feature-branch"},
            {"input": "git branch ", "output": "git branch -a"},
            {"input": "git log ", "output": "git log --oneline -10"},
            {"input": "git diff ", "output": "git diff HEAD~1"},
            {"input": "git merge ", "output": "git merge feature-branch"},
            {"input": "git rebase ", "output": "git rebase main"},
            {"input": "git stash ", "output": "git stash push -m \"wip\""},
            {"input": "git remote ", "output": "git remote -v"},
            {"input": "git clone ", "output": "git clone https://github.com/user/repo.git"},
            {"input": "git fetch ", "output": "git fetch --all"},
        ]
    
    def generate_docker_commands(self) -> List[Dict[str, str]]:
        """Generate Docker command patterns."""
        return [
            {"input": "docker ps ", "output": "docker ps -a"},
            {"input": "docker run ", "output": "docker run -it --name container image:tag"},
            {"input": "docker build ", "output": "docker build -t myapp:latest ."},
            {"input": "docker exec ", "output": "docker exec -it container /bin/bash"},
            {"input": "docker logs ", "output": "docker logs -f container"},
            {"input": "docker stop ", "output": "docker stop container"},
            {"input": "docker rm ", "output": "docker rm container"},
            {"input": "docker images ", "output": "docker images"},
            {"input": "docker pull ", "output": "docker pull nginx:latest"},
            {"input": "docker push ", "output": "docker push myrepo/image:tag"},
            {"input": "docker-compose up ", "output": "docker-compose up -d"},
            {"input": "docker-compose down ", "output": "docker-compose down"},
            {"input": "docker network ", "output": "docker network ls"},
        ]
    
    def generate_npm_commands(self) -> List[Dict[str, str]]:
        """Generate NPM/Node.js command patterns."""
        return [
            {"input": "npm install ", "output": "npm install package-name"},
            {"input": "npm run ", "output": "npm run dev"},
            {"input": "npm start", "output": "npm start"},
            {"input": "npm test", "output": "npm test"},
            {"input": "npm init ", "output": "npm init -y"},
            {"input": "npm publish", "output": "npm publish"},
            {"input": "npm audit ", "output": "npm audit fix"},
            {"input": "npm uninstall ", "output": "npm uninstall package-name"},
            {"input": "yarn add ", "output": "yarn add package-name"},
            {"input": "yarn remove ", "output": "yarn remove package-name"},
            {"input": "yarn run ", "output": "yarn run build"},
        ]
    
    def generate_python_commands(self) -> List[Dict[str, str]]:
        """Generate Python command patterns."""
        return [
            {"input": "python -m ", "output": "python -m http.server 8000"},
            {"input": "python script.py", "output": "python script.py"},
            {"input": "pip install ", "output": "pip install -r requirements.txt"},
            {"input": "pip freeze ", "output": "pip freeze > requirements.txt"},
            {"input": "pip list", "output": "pip list"},
            {"input": "pip show ", "output": "pip show package-name"},
            {"input": "python -c ", "output": "python -c \"print('hello')\""},
            {"input": "python manage.py ", "output": "python manage.py runserver"},
            {"input": "python -i ", "output": "python -i script.py"},
        ]
    
    def generate_system_commands(self) -> List[Dict[str, str]]:
        """Generate system command patterns."""
        return [
            {"input": "ls ", "output": "ls -la"},
            {"input": "cd ", "output": "cd ~/projects"},
            {"input": "cp ", "output": "cp file.txt destination/"},
            {"input": "mv ", "output": "mv oldname newname"},
            {"input": "rm ", "output": "rm -rf directory/"},
            {"input": "mkdir ", "output": "mkdir new-project"},
            {"input": "find ", "output": "find . -name \"*.py\""},
            {"input": "grep ", "output": "grep -r \"pattern\" ."},
            {"input": "chmod ", "output": "chmod +x script.sh"},
            {"input": "chown ", "output": "chown user:group file.txt"},
            {"input": "ps aux", "output": "ps aux | grep process-name"},
            {"input": "kill ", "output": "kill -9 pid"},
            {"input": "top", "output": "top"},
            {"input": "df ", "output": "df -h"},
            {"input": "du ", "output": "du -sh directory/"},
        ]
    
    def generate_kubernetes_commands(self) -> List[Dict[str, str]]:
        """Generate Kubernetes command patterns."""
        return [
            {"input": "kubectl get ", "output": "kubectl get pods"},
            {"input": "kubectl describe ", "output": "kubectl describe pod pod-name"},
            {"input": "kubectl apply ", "output": "kubectl apply -f deployment.yaml"},
            {"input": "kubectl delete ", "output": "kubectl delete pod pod-name"},
            {"input": "kubectl logs ", "output": "kubectl logs pod-name"},
            {"input": "kubectl exec ", "output": "kubectl exec -it pod-name -- /bin/bash"},
            {"input": "kubectl scale ", "output": "kubectl scale deployment my-deployment --replicas=3"},
            {"input": "kubectl port-forward ", "output": "kubectl port-forward pod-name 8080:80"},
            {"input": "kubectl config ", "output": "kubectl config get-contexts"},
        ]
    
    def generate_zsh_specific_commands(self) -> List[Dict[str, str]]:
        """Generate Zsh-specific command patterns."""
        return [
            {"input": "source ", "output": "source ~/.zshrc"},
            {"input": "autoload ", "output": "autoload -Uz compinit && compinit"},
            {"input": "compdef ", "output": "compdef _git git"},
            {"input": "zstyle ", "output": "zstyle ':completion:*' menu select"},
            {"input": "bindkey ", "output": "bindkey '^I' complete-word"},
            {"input": "history", "output": "history | grep pattern"},
            {"input": "fc -l", "output": "fc -l 1"},
            {"input": "alias ", "output": "alias ll='ls -la'"},
        ]
    
    def generate_curl_commands(self) -> List[Dict[str, str]]:
        """Generate curl and HTTP command patterns."""
        return [
            {"input": "curl ", "output": "curl -X GET https://api.example.com"},
            {"input": "curl -H ", "output": "curl -H \"Content-Type: application/json\" -X POST https://api.example.com"},
            {"input": "curl -d ", "output": "curl -d '{\"key\":\"value\"}' https://api.example.com"},
            {"input": "wget ", "output": "wget https://example.com/file.zip"},
            {"input": "ssh ", "output": "ssh user@hostname"},
            {"input": "scp ", "output": "scp file.txt user@remote:/path/"},
            {"input": "rsync ", "output": "rsync -av source/ destination/"},
        ]
    
    def create_training_pairs(self) -> List[Dict[str, str]]:
        """Create comprehensive training pairs."""
        all_commands = []
        
        # Add commands from all categories
        all_commands.extend(self.generate_git_commands())
        all_commands.extend(self.generate_docker_commands())
        all_commands.extend(self.generate_npm_commands())
        all_commands.extend(self.generate_python_commands())
        all_commands.extend(self.generate_system_commands())
        all_commands.extend(self.generate_kubernetes_commands())
        all_commands.extend(self.generate_zsh_specific_commands())
        all_commands.extend(self.generate_curl_commands())
        
        # Add variations for common patterns
        variations = self.generate_variations(all_commands)
        all_commands.extend(variations)
        
        return all_commands
    
    def generate_variations(self, base_commands: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Generate variations of commands for better training."""
        variations = []
        
        for cmd in base_commands:
            # Add partial command variations
            if len(cmd["input"]) > 5:
                partial_input = cmd["input"][:-1]  # Remove last character
                variations.append({
                    "input": partial_input,
                    "output": cmd["output"]
                })
        
        return variations
    
    def save_training_data(self, output_path: str, max_examples: int = 500):
        """Save training data in JSONL format."""
        data = self.create_training_pairs()
        
        # Limit to max examples if specified
        if max_examples and len(data) > max_examples:
            data = data[:max_examples]
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            for item in data:
                f.write(json.dumps(item) + '\n')
        
        print(f"✅ Generated {len(data)} Zsh training examples")
        print(f"📁 Saved to: {output_path}")
        
        # Print some statistics
        categories = {
            "Git": len(self.generate_git_commands()),
            "Docker": len(self.generate_docker_commands()),
            "NPM/Node": len(self.generate_npm_commands()),
            "Python": len(self.generate_python_commands()),
            "System": len(self.generate_system_commands()),
            "Kubernetes": len(self.generate_kubernetes_commands()),
            "Zsh Specific": len(self.generate_zsh_specific_commands()),
            "HTTP/Tools": len(self.generate_curl_commands()),
        }
        
        print("\n📊 Training Data Breakdown:")
        for category, count in categories.items():
            print(f"   {category}: {count} examples")

def main():
    parser = argparse.ArgumentParser(description='Prepare Zsh training data for LoRA fine-tuning')
    parser.add_argument('--output', '-o', default='src/training/zsh_training_data.jsonl', 
                       help='Output file path')
    parser.add_argument('--max-examples', '-m', type=int, default=500,
                       help='Maximum number of training examples')
    
    args = parser.parse_args()
    
    preparer = ZshDataPreparer()
    preparer.save_training_data(args.output, args.max_examples)

if __name__ == '__main__':
    main()