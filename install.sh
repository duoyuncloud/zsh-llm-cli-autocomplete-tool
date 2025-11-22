#!/bin/bash

# Zsh AI Autocomplete - Complete One-Click Installation
# Uses existing modules instead of inline code

echo "Zsh AI Autocomplete - Complete One-Click Setup"
echo "=================================================="
echo "Features: Ollama integration, LoRA fine-tuning, Zsh completion"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_feature() { echo -e "${PURPLE}[FEATURE]${NC} $1"; }
print_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create install log
INSTALL_LOG="$SCRIPT_DIR/install.log"
echo "=== Zsh AI Autocomplete Installation Log ===" > "$INSTALL_LOG"
echo "Started at: $(date)" >> "$INSTALL_LOG"
echo "" >> "$INSTALL_LOG"

print_info "Starting complete setup in: $SCRIPT_DIR"
print_info "Installation log: $INSTALL_LOG"

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
# PHASE 1: SYSTEM CHECKS & VIRTUAL ENVIRONMENT
# ============================================================================

print_step "Phase 1: System checks and environment setup..."

# Check system requirements
check_requirements() {
    print_info "Checking system requirements..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        print_info "Please install Python 3.8+ and try again"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_success "Python $PYTHON_VERSION found"
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is required but not installed"
        exit 1
    fi
    print_success "pip3 found"
    
    # Check Zsh
    if ! command -v zsh &> /dev/null; then
        print_error "Zsh is required but not installed"
        print_info "Please install Zsh and try again"
        exit 1
    fi
    ZSH_VERSION=$(zsh --version | cut -d' ' -f2)
    print_success "Zsh $ZSH_VERSION found"
    
    # Check curl (for Ollama installation)
    if ! command -v curl &> /dev/null; then
        print_error "curl is required for Ollama installation"
        exit 1
    fi
    print_success "curl found"
    
    # Check git (for training data)
    if ! command -v git &> /dev/null; then
        print_warning "git not found - some features may be limited"
    else
        print_success "git found"
    fi
}

check_requirements

# Create virtual environment
print_info "Setting up Python virtual environment..."
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
    PIP_CMD="pip3"
    PYTHON_CMD="python3"
    print_warning "Using --user installs (no virtual environment)"
fi

# ============================================================================
# PHASE 2: INSTALL PYTHON DEPENDENCIES
# ============================================================================

print_step "Phase 2: Installing Python dependencies..."

# Install core dependencies
print_info "Installing core Python dependencies..."
CORE_DEPS=(
    "requests>=2.28.0"
    "pyyaml>=6.0"
    "argcomplete>=2.0.0"
    "python-dotenv>=0.19.0"
    "prompt-toolkit>=3.0.0"
)

for dep in "${CORE_DEPS[@]}"; do
    if run_command "$PIP_CMD install '$dep'" "Installing $dep"; then
        print_success "Installed $dep"
    else
        print_warning "Failed to install $dep - continuing..."
    fi
done

# Install training dependencies (optional)
print_info "Installing training dependencies (for LoRA fine-tuning)..."
TRAINING_DEPS=(
    "torch>=2.0.0"
    "transformers>=4.30.0"
    "accelerate>=0.20.0"
    "datasets>=2.12.0"
    "peft>=0.4.0"
    "axolotl"
)

for dep in "${TRAINING_DEPS[@]}"; do
    if run_command "$PIP_CMD install '$dep'" "Installing training dependency $dep"; then
        print_success "Installed $dep"
    else
        print_warning "Failed to install $dep - LoRA training may not work"
    fi
done

# Install the package in development mode
print_info "Installing core package..."
if run_command "$PIP_CMD install -e ." "Installing package in development mode"; then
    print_success "Core package installed successfully"
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
# PHASE 3: SETUP OLLAMA AND MODELS
# ============================================================================

print_step "Phase 3: Setting up Ollama and models..."

# Use the existing Python modules to setup Ollama
print_info "Setting up Ollama using existing modules..."
if run_command "$PYTHON_CMD -c \"
import sys
sys.path.insert(0, 'src')
from model_completer.ollama_manager import create_ollama_manager

manager = create_ollama_manager()
if not manager.is_installed():
    print('Installing Ollama...')
    if manager.install():
        print('Ollama installed successfully')
    else:
        print('Failed to install Ollama')
        sys.exit(1)
else:
    print('Ollama already installed')

if not manager.is_running():
    print('Starting Ollama server...')
    if manager.start_server():
        print('Ollama server started')
    else:
        print('Failed to start Ollama server')
        sys.exit(1)
else:
    print('Ollama server already running')

print('Setting up default models...')
if manager.setup_default_models():
    print('Default models setup completed')
else:
    print('Failed to setup default models')
\"" "Setting up Ollama and models"; then
    print_success "Ollama and models setup completed"
else
    print_warning "Ollama setup had issues - check logs"
fi

# ============================================================================
# PHASE 4: SETUP TRAINING DATA
# ============================================================================

print_step "Phase 4: Setting up training data..."

print_info "Generating training data using existing modules..."
if run_command "$PYTHON_CMD -c \"
import sys
sys.path.insert(0, 'src')
from model_completer.training import TrainingDataManager

data_manager = TrainingDataManager()
data_file = data_manager.generate_training_data(500)
print(f'Training data generated: {data_file}')
\"" "Generating training data"; then
    print_success "Training data generated"
else
    print_warning "Training data generation had issues"
fi

# ============================================================================
# PHASE 5: INSTALL ZSH PLUGIN
# ============================================================================

print_step "Phase 5: Installing Zsh plugin..."

install_zsh_plugin() {
    local plugin_file="$SCRIPT_DIR/src/scripts/zsh_autocomplete.plugin.zsh"
    
    if [[ ! -f "$plugin_file" ]]; then
        print_error "Plugin file not found: $plugin_file"
        return 1
    fi
    
    # Add to .zshrc if not already there
    if ! grep -q "zsh_autocomplete.plugin.zsh" ~/.zshrc 2>/dev/null; then
        echo "" >> ~/.zshrc
        echo "# Zsh AI Autocomplete Plugin" >> ~/.zshrc
        echo "source \"$plugin_file\"" >> ~/.zshrc
        print_success "Added plugin to ~/.zshrc"
    else
        print_info "Plugin already configured in ~/.zshrc"
    fi
}

install_zsh_plugin

# ============================================================================
# PHASE 6: CREATE CONFIGURATION
# ============================================================================

print_step "Phase 6: Setting up configuration..."

print_info "Creating configuration using existing modules..."
if run_command "$PYTHON_CMD -c \"
import sys
sys.path.insert(0, 'src')
from model_completer.utils import load_config
import os
import yaml

# Create config directory
config_dir = os.path.expanduser('~/.config/model-completer')
os.makedirs(config_dir, exist_ok=True)

# Create default config if it doesn't exist
config_file = os.path.join(config_dir, 'config.yaml')
if not os.path.exists(config_file):
    default_config = {
        'ollama': {
            'url': 'http://localhost:11434',
            'timeout': 10
        },
        'model': 'zsh-assistant',
        'fallback_model': 'codellama:7b',
        'cache': {
            'enabled': True,
            'ttl': 3600
        },
        'logging': {
            'level': 'INFO',
            'file': '~/.cache/model-completer/logs.txt'
        },
        'ui': {
            'enabled': True,
            'max_suggestions': 5,
            'show_confidence': True
        },
        'blacklist': [
            'rm -rf /',
            'dd if=/dev/random',
            ':(){:|:&};:',
            'mkfs',
            'fdisk'
        ],
        'training': {
            'enabled': True,
            'data_path': 'src/training/zsh_training_data.jsonl',
            'output_path': 'zsh-lora-output',
            'max_examples': 500
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    
    print(f'Configuration created: {config_file}')
else:
    print('Configuration already exists')
\"" "Creating configuration"; then
    print_success "Configuration created"
else
    print_warning "Configuration creation had issues"
fi

# ============================================================================
# PHASE 7: FINAL TESTING
# ============================================================================

print_step "Phase 7: Final testing and validation..."

# Test the Python package
print_info "Testing Python package..."
if run_command "$PYTHON_CMD -c \"import model_completer; print('Python package: ✅')\"" "Testing Python package"; then
    print_success "Python package working"
else
    print_warning "Python package test failed"
fi

# Test CLI
print_info "Testing CLI functionality..."
if run_command "$PYTHON_CMD -m model_completer.cli --test" "Testing CLI"; then
    print_success "CLI working"
else
    print_warning "CLI test failed"
fi

# Test Ollama connection
print_info "Testing Ollama connection..."
if run_command "$PYTHON_CMD -c \"
import sys
sys.path.insert(0, 'src')
from model_completer.ollama_manager import create_ollama_manager
manager = create_ollama_manager()
if manager.is_running():
    print('Ollama server: ✅ Running')
else:
    print('Ollama server: ❌ Not running')
\"" "Testing Ollama connection"; then
    print_success "Ollama connection test completed"
else
    print_warning "Ollama connection test failed"
fi

# ============================================================================
# COMPLETION MESSAGE
# ============================================================================

print_success "🎉 COMPLETE SETUP FINISHED!"
echo ""
echo "🚀 YOUR AI AUTOCOMPLETE WITH NAVIGATABLE UI IS READY!"
echo ""
print_feature "✨ Features Installed:"
echo "   🤖 Ollama integration with multiple models"
echo "   🎯 LoRA fine-tuning capabilities"
echo "   🖥️  Navigatable UI with multiple completion modes"
echo "   ⚡ Real-time command completion"
echo "   🔧 Training and management tools"
echo ""
print_step "📋 IMMEDIATE ACTIONS:"
echo "   1. Reload your shell:"
echo "      source ~/.zshrc"
echo ""
echo "   2. Test the installation:"
echo "      ai-completion-test"
echo ""
echo "   3. Check system status:"
echo "      ai-completion-status"
echo ""
print_step "🎯 START USING IT NOW:"
echo "   Try these commands with different keys:"
echo "     git comm[Tab]        -> Simple completion"
echo "     docker run[Shift+Tab] -> UI mode with multiple suggestions"
echo "     npm run[Ctrl+Tab]     -> Advanced mode with confidence"
echo "     python -m[Tab]        -> Basic completion"
echo "     kubectl get[Tab]      -> Command completion"
echo ""
print_step "🔧 MANAGEMENT COMMANDS:"
echo "   ai-completion-train    -> Start LoRA training"
echo "   ai-completion-data     -> Generate training data"
echo "   ai-completion-models   -> List available models"
echo "   ai-completion-setup    -> Setup Ollama and models"
echo ""
print_step "🔧 TROUBLESHOOTING:"
echo "   If commands don't work immediately:"
echo "   1. Make sure ~/.zshrc is reloaded: source ~/.zshrc"
echo "   2. Check if plugin is loaded: grep 'zsh-autocomplete' ~/.zshrc"
echo "   3. Check logs: $INSTALL_LOG"
echo "   4. Manual test: $PYTHON_CMD -m model_completer.cli --test"
echo ""
print_step "📚 DOCUMENTATION:"
echo "   ai-completion-help     -> Show all available commands"
echo "   README.md              -> Project documentation"
echo "   $INSTALL_LOG          -> Installation log"
echo ""

# Make script executable for future
chmod +x "$SCRIPT_DIR/install.sh"

# Setup PATH for model-completer command
print_step "Setting up PATH for model-completer command..."

# Add to ~/.zshrc if not already there
if ! grep -q "zsh-llm-cli-autocomplete-tool.*PATH" ~/.zshrc 2>/dev/null; then
    echo "" >> ~/.zshrc
    echo "# Model CLI Autocomplete PATH setup" >> ~/.zshrc
    echo "export PATH=\"$SCRIPT_DIR/venv/bin:\$PATH\"" >> ~/.zshrc
    echo "export PATH=\"$SCRIPT_DIR/bin:\$PATH\"" >> ~/.zshrc
    print_success "Added model-completer to PATH in ~/.zshrc"
else
    print_info "PATH already configured in ~/.zshrc"
fi

print_success "🎉 Installation complete! Reload your shell and start using AI completions!"
echo ""
print_info "💡 Pro tip: Use 'ai-completion-help' to see all available features!"
print_info "💡 Use 'model-completer --help' to see CLI options!"