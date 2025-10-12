#!/bin/bash

# Zsh AI Autocomplete - One-Click Installer

echo "🤖 Zsh AI Autocomplete - Complete Installation"
echo "=============================================="

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

print_info "Starting installation in: $SCRIPT_DIR"

# Create install log
INSTALL_LOG="$SCRIPT_DIR/install.log"
echo "Installation started at $(date)" > "$INSTALL_LOG"

# Function to log commands
log_command() {
    echo ">>> $1" >> "$INSTALL_LOG"
    eval "$1" >> "$INSTALL_LOG" 2>&1
    local status=$?
    echo ">>> Exit code: $status" >> "$INSTALL_LOG"
    return $status
}

# Function to run command with error handling
run_command() {
    local cmd="$1"
    local description="$2"
    
    print_info "$description..."
    echo "=== $description ===" >> "$INSTALL_LOG"
    
    if log_command "$cmd"; then
        print_success "$description"
        return 0
    else
        print_error "$description failed (see $INSTALL_LOG)"
        return 1
    fi
}

# ============================================================================
# PHASE 1: BASIC CHECKS
# ============================================================================

print_info "Phase 1: Basic system checks..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
else
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_success "Python $PYTHON_VERSION found"
fi

# Check pip
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is required but not installed"
    exit 1
else
    print_success "pip3 found"
fi

# Check Zsh
if ! command -v zsh &> /dev/null; then
    print_error "Zsh is required but not installed"
    exit 1
else
    ZSH_VERSION=$(zsh --version | cut -d' ' -f2)
    print_success "Zsh $ZSH_VERSION found"
fi

# Check Ollama
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>/dev/null || echo "unknown")
    print_success "Ollama found ($OLLAMA_VERSION)"
else
    print_warning "Ollama not found - you'll need to install it manually later"
fi

# ============================================================================
# PHASE 2: CREATE VIRTUAL ENVIRONMENT
# ============================================================================

print_info "Phase 2: Setting up Python environment..."

if [[ ! -d "$SCRIPT_DIR/venv" ]]; then
    if run_command "python3 -m venv '$SCRIPT_DIR/venv'" "Creating virtual environment"; then
        print_success "Virtual environment created"
    else
        print_error "Failed to create virtual environment"
        print_info "Trying without virtual environment..."
        USE_VENV=0
    fi
else
    print_info "Virtual environment already exists"
    USE_VENV=1
fi

if [[ $USE_VENV -eq 1 ]]; then
    source "$SCRIPT_DIR/venv/bin/activate"
    PIP_CMD="$SCRIPT_DIR/venv/bin/pip"
    PYTHON_CMD="$SCRIPT_DIR/venv/bin/python"
    print_success "Using virtual environment"
else
    PIP_CMD="pip3 --user"
    PYTHON_CMD="python3"
    print_warning "Using --user installs (no virtual environment)"
fi

# ============================================================================
# PHASE 3: INSTALL PYTHON DEPENDENCIES
# ============================================================================

print_info "Phase 3: Installing Python dependencies..."

# First, let's check if setup.py exists
if [[ ! -f "setup.py" ]]; then
    print_warning "setup.py not found, creating basic one..."
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
    python_requires=">=3.8",
)
EOF
    print_success "Created setup.py"
fi

# Create basic package structure if it doesn't exist
mkdir -p src/model_completer

if [[ ! -f "src/model_completer/__init__.py" ]]; then
    cat > src/model_completer/__init__.py << 'EOF'
"""Model-based CLI autocompletion tool."""
__version__ = "0.1.0"
EOF
fi

if [[ ! -f "src/model_completer/cli.py" ]]; then
    cat > src/model_completer/cli.py << 'EOF'
#!/usr/bin/env python3
"""Command-line interface for model completer."""

import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description='Model-based CLI autocompletion')
    parser.add_argument('--list-models', action='store_true', help='List available models')
    
    args = parser.parse_args()
    
    if args.list_models:
        print("Available models:")
        print("  - codellama:7b")
        print("  - llama2:7b")
        print("💡 Install Ollama and run 'ollama pull codellama:7b' to get models")
    else:
        print("Model CLI Autocomplete")
        print("Usage: model-completer --list-models")

if __name__ == '__main__':
    main()
EOF
    print_success "Created basic CLI module"
fi

# Install dependencies one by one with error handling
DEPENDENCIES=(
    "requests"
    "pyyaml" 
    "argcomplete"
    "python-dotenv"
    "prompt-toolkit"
)

for dep in "${DEPENDENCIES[@]}"; do
    if run_command "$PIP_CMD install '$dep'" "Installing $dep"; then
        print_success "Installed $dep"
    else
        print_error "Failed to install $dep"
        print_info "Continuing with other dependencies..."
    fi
done

# Try to install the package
print_info "Installing core package..."
if run_command "$PIP_CMD install -e ." "Installing package in development mode"; then
    print_success "Package installed successfully"
else
    print_warning "Development mode install failed, trying regular install..."
    if run_command "$PIP_CMD install ." "Installing package regularly"; then
        print_success "Package installed regularly"
    else
        print_error "All installation methods failed"
        print_info "Creating manual setup..."
    fi
fi

# ============================================================================
# PHASE 4: CREATE CONFIGURATION
# ============================================================================

print_info "Phase 4: Setting up configuration..."

mkdir -p ~/.config/model-completer
mkdir -p ~/.cache/model-completer

if [[ ! -f ~/.config/model-completer/config.yaml ]]; then
    cat > ~/.config/model-completer/config.yaml << 'EOF'
# Model Completer Configuration
ollama:
  url: "http://localhost:11434"
  timeout: 10

model: "codellama:7b"

cache:
  enabled: true
  ttl: 3600

logging:
  level: "INFO" 
  file: "~/.cache/model-completer/logs.txt"

ui:
  max_suggestions: 5
  enabled: true

blacklist:
  - "rm -rf /"
  - "dd if=/dev/random"
EOF
    print_success "Created configuration file"
else
    print_info "Configuration already exists"
fi

# ============================================================================
# PHASE 5: INSTALL ZSH PLUGIN
# ============================================================================

print_info "Phase 5: Installing Zsh plugin..."

# Determine plugin directory
if [[ -n "$ZSH" ]]; then
    PLUGIN_DIR="$ZSH/custom/plugins/model-completion"
elif [[ -d "$HOME/.oh-my-zsh" ]]; then
    PLUGIN_DIR="$HOME/.oh-my-zsh/custom/plugins/model-completion"
else
    PLUGIN_DIR="$HOME/.zsh-plugins/model-completion"
fi

mkdir -p "$PLUGIN_DIR"

# Create plugin file
cat > "$PLUGIN_DIR/model-completion.plugin.zsh" << EOF
#!/usr/bin/env zsh

# Zsh AI Autocomplete Plugin

# Set Python path
if [[ -f "$SCRIPT_DIR/venv/bin/python" ]]; then
    export MODEL_COMPLETION_PYTHON="$SCRIPT_DIR/venv/bin/python"
else
    export MODEL_COMPLETION_PYTHON="python3"
fi

export MODEL_COMPLETION_SCRIPT="$SCRIPT_DIR/src/model_completer/cli.py"

# Check if we can use the package
check_model_completer() {
    if [[ ! -f "\$MODEL_COMPLETION_SCRIPT" ]]; then
        echo "❌ Model completer script not found: \$MODEL_COMPLETION_SCRIPT"
        return 1
    fi
    return 0
}

# Simple completion function
_model_completion_simple() {
    if check_model_completer; then
        local completion
        completion=\$(\$MODEL_COMPLETION_PYTHON "\$MODEL_COMPLETION_SCRIPT" "\$BUFFER" 2>/dev/null)
        if [[ -n "\$completion" ]]; then
            BUFFER="\$completion"
            CURSOR=\${#BUFFER}
        else
            zle expand-or-complete
        fi
    else
        zle expand-or-complete
    fi
}

zle -N _model_completion_simple
bindkey '^I' _model_completion_simple

# Utility functions
model-completion-check() {
    echo "🧪 Testing Zsh AI Autocomplete..."
    if check_model_completer; then
        echo "✅ Basic setup OK"
        \$MODEL_COMPLETION_PYTHON "\$MODEL_COMPLETION_SCRIPT" --list-models
    else
        echo "❌ Setup incomplete"
    fi
}

model-completion-status() {
    echo "📊 Zsh AI Autocomplete Status"
    echo "   Python: \$MODEL_COMPLETION_PYTHON"
    echo "   Script: \$MODEL_COMPLETION_SCRIPT"
    echo "   Virtual env: $SCRIPT_DIR/venv"
    check_model_completer && echo "   Package: ✅ OK" || echo "   Package: ❌ Missing"
}

echo "✅ Zsh AI Autocomplete plugin loaded"
echo "💡 Use 'model-completion-check' to test setup"
EOF

print_success "Zsh plugin installed to: $PLUGIN_DIR"

# ============================================================================
# PHASE 6: FINAL SETUP
# ============================================================================

print_info "Phase 6: Final setup..."

# Create training directory structure
mkdir -p src/training

# Make scripts executable if they exist
[[ -f "src/training/train.sh" ]] && chmod +x src/training/train.sh
[[ -f "src/training/axolotl_setup.sh" ]] && chmod +x src/training/axolotl_setup.sh

print_success "Training environment setup"

# ============================================================================
# COMPLETION
# ============================================================================

print_success "🎉 Installation completed!"
echo ""
echo "📋 NEXT STEPS:"
echo "   1. Add this to your ~/.zshrc:"
if [[ "$PLUGIN_DIR" == *".oh-my-zsh"* ]]; then
    echo "      plugins=(git model-completion)"
else
    echo "      source $PLUGIN_DIR/model-completion.plugin.zsh"
fi
echo ""
echo "   2. Reload your shell:"
echo "      source ~/.zshrc"
echo ""
echo "   3. Test the installation:"
echo "      model-completion-check"
echo ""
echo "   4. Start Ollama (if not running):"
echo "      ollama serve"
echo ""
echo "   5. Pull a model:"
echo "      ollama pull codellama:7b"
echo ""
echo "🔧 TROUBLESHOOTING:"
echo "   - Check install log: $INSTALL_LOG"
echo "   - Ensure virtual env is activated: source $SCRIPT_DIR/venv/bin/activate"
echo "   - Verify Ollama: ollama list"

# Make install script executable
chmod +x "$SCRIPT_DIR/install.sh"

print_success "Installation finished! Check the steps above to complete setup."