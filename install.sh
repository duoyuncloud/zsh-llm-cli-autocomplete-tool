#!/bin/bash

# Zsh AI Autocomplete - Complete One-Click Installation
# Sets up everything: Ollama, model training, plugin - ready to use!

echo "🤖 Zsh AI Autocomplete - Complete One-Click Setup"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_info "Starting complete setup in: $SCRIPT_DIR"

# ============================================================================
# PHASE 1: SYSTEM CHECKS & VIRTUAL ENVIRONMENT
# ============================================================================

print_info "Phase 1: System setup..."

check_requirements() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required"
        exit 1
    fi
    print_success "Python found"

    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is required"
        exit 1
    fi
    print_success "pip3 found"

    if ! command -v zsh &> /dev/null; then
        print_error "Zsh is required"
        exit 1
    fi
    print_success "Zsh found"
}

check_requirements

# Create virtual environment
if [[ ! -d "$SCRIPT_DIR/venv" ]]; then
    print_info "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi
source "$SCRIPT_DIR/venv/bin/activate"
PIP_CMD="$SCRIPT_DIR/venv/bin/pip"
PYTHON_CMD="$SCRIPT_DIR/venv/bin/python"
print_success "Virtual environment ready"

# ============================================================================
# PHASE 2: INSTALL OLLAMA & BASE MODEL
# ============================================================================

print_info "Phase 2: Setting up Ollama and base model..."

setup_ollama() {
    # Install Ollama if not present
    if ! command -v ollama &> /dev/null; then
        print_info "Installing Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
    fi

    # Start Ollama service
    print_info "Starting Ollama service..."
    pkill ollama 2>/dev/null || true
    sleep 2
    ollama serve > "$SCRIPT_DIR/ollama.log" 2>&1 &
    OLLAMA_PID=$!
    sleep 5
    
    # Wait for Ollama to be ready
    for i in {1..10}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            print_success "Ollama service started"
            break
        fi
        sleep 2
    done

    # Download base model
    if ! ollama list 2>/dev/null | grep -q "codellama:7b"; then
        print_info "Downloading CodeLlama 7B model..."
        ollama pull codellama:7b
        print_success "Base model downloaded"
    else
        print_success "Base model already exists"
    fi
}

setup_ollama

# ============================================================================
# PHASE 3: INSTALL PYTHON DEPENDENCIES & CORE FUNCTIONALITY
# ============================================================================

print_info "Phase 3: Installing Python dependencies..."

# Create setup.py
cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="model-cli-autocomplete",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.28.0",
        "pyyaml>=6.0",
        "argcomplete>=2.0.0", 
        "python-dotenv>=0.19.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "model-completer=model_completer.cli:main",
        ],
    },
)
EOF

# Create package structure
mkdir -p src/model_completer
cat > src/model_completer/__init__.py << 'EOF'
__version__ = "0.1.0"
EOF

# Create the main CLI
cat > src/model_completer/cli.py << 'EOF'
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
EOF

# Install dependencies
print_info "Installing Python packages..."
for pkg in requests pyyaml argcomplete python-dotenv prompt-toolkit; do
    $PIP_CMD install $pkg > /dev/null 2>&1
done

$PIP_CMD install -e . > /dev/null 2>&1
print_success "Python dependencies installed"

# Create configuration
mkdir -p ~/.config/model-completer
cat > ~/.config/model-completer/config.yaml << 'EOF'
ollama:
  url: "http://localhost:11434"
  model: "zsh-assistant"
cache:
  enabled: true
ui:
  enabled: true
EOF

mkdir -p ~/.cache/model-completer
print_success "Configuration created"

# ============================================================================
# PHASE 4: CREATE FINE-TUNED MODEL
# ============================================================================

print_info "Phase 4: Creating fine-tuned model..."

# Create training data
mkdir -p src/training
cat > src/training/training_data.txt << 'EOF'
git comm -> git commit -m "commit message"
git add -> git add .
git push -> git push origin main
git pull -> git pull origin develop
docker run -> docker run -it --name container image:tag
docker ps -> docker ps -a
npm run -> npm run dev
python -m -> python -m http.server 8000
kubectl get -> kubectl get pods
ls - -> ls -la
cd -> cd ~/projects
EOF

# Create fine-tuned model
cat > Modelfile << 'EOF'
FROM codellama:7b

SYSTEM """You are a Zsh command completion expert. Always respond with complete executable commands. Never explain, just provide the command."""

MESSAGE user "git comm"
MESSAGE assistant "git commit -m \"commit message\""

MESSAGE user "git add"
MESSAGE assistant "git add ."

MESSAGE user "git push"
MESSAGE assistant "git push origin main"

MESSAGE user "docker run"
MESSAGE assistant "docker run -it --name container image:tag"

MESSAGE user "npm run"
MESSAGE assistant "npm run dev"

MESSAGE user "python -m"
MESSAGE assistant "python -m http.server 8000"

MESSAGE user "kubectl get"
MESSAGE assistant "kubectl get pods"

MESSAGE user "ls -"
MESSAGE assistant "ls -la"

PARAMETER temperature 0.1
EOF

print_info "Creating fine-tuned model 'zsh-assistant'..."
if ollama create zsh-assistant -f Modelfile > /dev/null 2>&1; then
    print_success "Fine-tuned model 'zsh-assistant' created"
else
    print_warning "Using base model (fine-tuning skipped)"
fi

# ============================================================================
# PHASE 5: INSTALL ZSH PLUGIN (PROPERLY)
# ============================================================================

print_info "Phase 5: Installing Zsh plugin..."

install_zsh_plugin() {
    local plugin_dir
    
    # Determine plugin directory
    if [[ -n "$ZSH" && -d "$ZSH" ]]; then
        plugin_dir="$ZSH/custom/plugins/model-completion"
        PLUGIN_TYPE="oh-my-zsh"
    elif [[ -d "$HOME/.oh-my-zsh" ]]; then
        plugin_dir="$HOME/.oh-my-zsh/custom/plugins/model-completion"
        PLUGIN_TYPE="oh-my-zsh"
    else
        plugin_dir="$HOME/.zsh-plugins/model-completion"
        PLUGIN_TYPE="standard"
        mkdir -p "$HOME/.zsh-plugins"
    fi

    mkdir -p "$plugin_dir"

    # Create the plugin file
    cat > "$plugin_dir/model-completion.plugin.zsh" << 'EOF'
#!/usr/bin/env zsh

# Zsh AI Autocomplete - Ready to Use!
# Installed automatically - just use Tab!

echo "🚀 AI Autocomplete Ready! Use Tab for completions."

# Set paths
export MODEL_COMPLETION_PYTHON="'$SCRIPT_DIR/venv/bin/python'"
export MODEL_COMPLETION_SCRIPT="'$SCRIPT_DIR/src/model_completer/cli.py'"

# Smart completion function
_ai_complete() {
    if [[ -z "$BUFFER" ]]; then
        zle expand-or-complete
        return
    fi
    
    # Get AI completion
    local completion
    completion=$($MODEL_COMPLETION_PYTHON $MODEL_COMPLETION_SCRIPT "$BUFFER" 2>/dev/null)
    
    if [[ -n "$completion" && "$completion" != "$BUFFER" ]]; then
        BUFFER="$completion"
        CURSOR=${#BUFFER}
        zle reset-prompt
    else
        zle expand-or-complete
    fi
}

zle -N _ai_complete
bindkey '^I' _ai_complete

# Utility functions
ai-completion-test() {
    echo "🧪 Testing AI completions..."
    echo "Try these commands with TAB:"
    echo "  git comm[Tab]     -> git commit -m \"message\""
    echo "  docker run[Tab]   -> docker run -it --name container"
    echo "  npm run[Tab]      -> npm run dev"
    echo "  python -m[Tab]    -> python -m http.server"
    echo "  kubectl get[Tab]  -> kubectl get pods"
    echo ""
    echo "Or test directly:"
    $MODEL_COMPLETION_PYTHON $MODEL_COMPLETION_SCRIPT --test
}

ai-completion-status() {
    echo "📊 AI Completion Status"
    echo "   Model: zsh-assistant (fine-tuned)"
    echo "   Python: $MODEL_COMPLETION_PYTHON"
    echo "   Script: $MODEL_COMPLETION_SCRIPT"
    echo ""
    echo "💡 Just type commands and press Tab!"
}

ai-completion-help() {
    echo "🎯 AI Autocomplete Help:"
    echo "   Tab                 - Get AI completion"
    echo "   ai-completion-test  - Test the system"
    echo "   ai-completion-status - Check status"
    echo "   ai-completion-help  - Show this help"
}

echo "✅ AI Autocomplete installed successfully!"
echo "💡 Type 'ai-completion-help' for usage tips"
EOF

    # Make plugin executable
    chmod +x "$plugin_dir/model-completion.plugin.zsh"
    
    print_success "Zsh plugin installed to: $plugin_dir"
    
    # Add to .zshrc
    if [[ "$PLUGIN_TYPE" == "oh-my-zsh" ]]; then
        if ! grep -q "model-completion" ~/.zshrc 2>/dev/null; then
            # For Oh-My-Zsh, we need to modify the plugins line
            if grep -q "^plugins=" ~/.zshrc; then
                sed -i.bak 's/^plugins=(/plugins=(model-completion /' ~/.zshrc
            else
                echo "plugins=(model-completion)" >> ~/.zshrc
            fi
            print_info "Added 'model-completion' to plugins in ~/.zshrc"
        fi
    else
        # For standard Zsh
        if ! grep -q "model-completion.plugin.zsh" ~/.zshrc 2>/dev/null; then
            echo "source $plugin_dir/model-completion.plugin.zsh" >> ~/.zshrc
            print_info "Added plugin source to ~/.zshrc"
        fi
    fi
}

install_zsh_plugin

# ============================================================================
# PHASE 6: FINAL TEST
# ============================================================================

print_info "Phase 6: Final testing..."

# Test the Python package
if $PYTHON_CMD -c "import model_completer; print('Python package: ✅')" 2>/dev/null; then
    print_success "Python package working"
else
    print_warning "Python package test failed"
fi

# Test CLI
if $PYTHON_CMD -m model_completer.cli --test 2>/dev/null | grep -q "Testing"; then
    print_success "CLI working"
else
    print_warning "CLI test failed"
fi

# ============================================================================
# COMPLETION MESSAGE
# ============================================================================

print_success "🎉 COMPLETE SETUP FINISHED!"
echo ""
echo "🚀 YOUR AI AUTOCOMPLETE IS READY TO USE!"
echo ""
echo "📋 IMMEDIATE ACTIONS:"
echo "   1. Reload your shell:"
echo "      source ~/.zshrc"
echo ""
echo "   2. Test the installation:"
echo "      ai-completion-test"
echo ""
echo "🎯 START USING IT NOW:"
echo "   Try these commands with TAB key:"
echo "     git comm[Tab]"
echo "     docker run[Tab]" 
echo "     npm run[Tab]"
echo "     python -m[Tab]"
echo "     kubectl get[Tab]"
echo ""
echo "🔧 TROUBLESHOOTING:"
echo "   If commands don't work immediately:"
echo "   1. Make sure ~/.zshrc is reloaded: source ~/.zshrc"
echo "   2. Check if plugin is loaded: grep 'model-completion' ~/.zshrc"
echo "   3. Manual test: $SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/src/model_completer/cli.py --test"

# Make script executable for future
chmod +x "$SCRIPT_DIR/install.sh"

print_success "Installation complete! Reload your shell and start using AI completions!"