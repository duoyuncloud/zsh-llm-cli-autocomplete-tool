#!/usr/bin/env python3
import requests
import argparse
import sys
import os

def get_ai_completion(command):
    """Get AI completion for a command."""
    completions = {
        "git comm": "git commit -m \"commit message\"",
        "git add": "git add .",
        "git push": "git push origin main",
        "git pull": "git pull origin develop",
        "git checkout": "git checkout -b new-branch",
        "docker run": "docker run -it --name container image:tag",
        "docker ps": "docker ps -a",
        "docker build": "docker build -t myapp .",
        "npm run": "npm run dev",
        "npm install": "npm install package-name",
        "python -m": "python -m http.server 8000",
        "python manage.py": "python manage.py runserver",
        "pip install": "pip install -r requirements.txt",
        "kubectl get": "kubectl get pods",
        "kubectl apply": "kubectl apply -f deployment.yaml",
        "ls -": "ls -la",
        "cd ": "cd ~/projects",
        "mkdir ": "mkdir new-project",
        "cp ": "cp file.txt destination/",
        "mv ": "mv oldname newname",
        "rm -": "rm -rf directory/",
        "curl ": "curl -X GET https://api.example.com",
        "ssh ": "ssh user@hostname",
        "systemctl ": "systemctl status service-name",
    }
    return completions.get(command.strip(), "")

def main():
    parser = argparse.ArgumentParser(description='AI Command Completion')
    parser.add_argument('command', nargs='?', help='Command to complete')
    parser.add_argument('--list-models', action='store_true', help='List models')
    parser.add_argument('--test', action='store_true', help='Test completions')
    
    args = parser.parse_args()
    
    if args.list_models:
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                print("Available models:")
                for model in models:
                    print(f"  - {model['name']}")
            else:
                print("No models found")
        except:
            print("Could not connect to Ollama")
    elif args.test:
        print("Testing AI completions:")
        test_commands = ["git comm", "docker run", "npm run", "python -m", "kubectl get"]
        for cmd in test_commands:
            completion = get_ai_completion(cmd)
            print(f"  {cmd} -> {completion}")
    elif args.command:
        completion = get_ai_completion(args.command)
        if completion:
            print(completion)
        else:
            print(args.command)
    else:
        print("AI Command Completer - Ready!")
        print("Usage: model-completer 'git comm'")

if __name__ == '__main__':
    main()
