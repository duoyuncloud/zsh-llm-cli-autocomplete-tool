#!/usr/bin/env zsh
# Enhanced Zsh AI Autocomplete Plugin
# Integrates with the existing Python modules for real functionality.

# Plugin configuration
# Auto-detect installation directory (works from plugin dir or project root)
MODEL_COMPLETION_PROJECT_DIR=""

# First, try to find the project from the plugin location
if [[ -f "${0:A:h}/../../src/model_completer/cli.py" ]]; then
    # Running from src/scripts/
    MODEL_COMPLETION_PROJECT_DIR="${0:A:h}/../.."
elif [[ -f "${0:A:h}/src/model_completer/cli.py" ]]; then
    # Running from project root
    MODEL_COMPLETION_PROJECT_DIR="${0:A:h}"
elif [[ -f "$HOME/.local/share/model-completer/src/model_completer/cli.py" ]]; then
    # Installed system-wide
    MODEL_COMPLETION_PROJECT_DIR="$HOME/.local/share/model-completer"
else
    # Try common project locations
    for dir in "$HOME/Desktop/model-cli-autocomplete" "$HOME/model-cli-autocomplete" "$HOME/.model-cli-autocomplete" "/opt/model-cli-autocomplete" "/Users/duoyun/Desktop/model-cli-autocomplete"; do
        if [[ -f "$dir/src/model_completer/cli.py" ]]; then
            MODEL_COMPLETION_PROJECT_DIR="$dir"
            break
        fi
    done
fi

# If still not found, try to find from current directory or any recent location
if [[ -z "$MODEL_COMPLETION_PROJECT_DIR" ]]; then
    # Try to find by searching common paths
    for dir in "$HOME/Desktop" "$HOME"; do
        if [[ -d "$dir" ]]; then
            found=$(find "$dir" -maxdepth 3 -name "model_completer" -type d -path "*/src/model_completer" 2>/dev/null | head -1)
            if [[ -n "$found" ]]; then
                MODEL_COMPLETION_PROJECT_DIR="$(dirname "$(dirname "$found")")"
                break
            fi
        fi
    done
fi

export MODEL_COMPLETION_DIR="${MODEL_COMPLETION_PROJECT_DIR}"

# Set script path first (needed to determine project dir)
if [[ -n "$MODEL_COMPLETION_PROJECT_DIR" ]]; then
    export MODEL_COMPLETION_SCRIPT="${MODEL_COMPLETION_PROJECT_DIR}/src/model_completer/cli.py"
else
    # Fallback: try to find it
    export MODEL_COMPLETION_SCRIPT=""
    for script_path in "$HOME/Desktop/model-cli-autocomplete/src/model_completer/cli.py" \
                       "$HOME/model-cli-autocomplete/src/model_completer/cli.py" \
                       "/Users/duoyun/Desktop/model-cli-autocomplete/src/model_completer/cli.py"; do
        if [[ -f "$script_path" ]]; then
            export MODEL_COMPLETION_SCRIPT="$script_path"
            # Set project dir from script path (go up two levels: cli.py -> model_completer -> src -> project_root)
            # Use realpath or readlink if available, otherwise use dirname
            if command -v realpath &> /dev/null; then
                export MODEL_COMPLETION_PROJECT_DIR="$(realpath "$(dirname "$(dirname "$script_path")")")"
            elif command -v readlink &> /dev/null; then
                export MODEL_COMPLETION_PROJECT_DIR="$(readlink -f "$(dirname "$(dirname "$script_path")")")"
            else
                # Fallback: use dirname (works for absolute paths)
                export MODEL_COMPLETION_PROJECT_DIR="$(dirname "$(dirname "$script_path")")"
            fi
            break
        fi
    done
fi

# Set Python path (now that we have PROJECT_DIR or SCRIPT)
if [[ -n "$MODEL_COMPLETION_PROJECT_DIR" ]]; then
    # Try venv python from project dir
    if [[ -f "${MODEL_COMPLETION_PROJECT_DIR}/venv/bin/python" ]]; then
        export MODEL_COMPLETION_PYTHON="${MODEL_COMPLETION_PROJECT_DIR}/venv/bin/python"
    elif [[ -f "${MODEL_COMPLETION_PROJECT_DIR}/venv/bin/python3" ]]; then
        export MODEL_COMPLETION_PYTHON="${MODEL_COMPLETION_PROJECT_DIR}/venv/bin/python3"
    fi
fi

# If still not set, derive from script path
if [[ -z "$MODEL_COMPLETION_PYTHON" && -n "$MODEL_COMPLETION_SCRIPT" ]]; then
    # Extract project dir from script path: .../project/src/model_completer/cli.py -> .../project
    script_dir="$(dirname "$MODEL_COMPLETION_SCRIPT")"  # src/model_completer
    src_dir="$(dirname "$script_dir")"  # src
    proj_dir="$(dirname "$src_dir")"  # project root
    
    if [[ -f "${proj_dir}/venv/bin/python" ]]; then
        export MODEL_COMPLETION_PYTHON="${proj_dir}/venv/bin/python"
        export MODEL_COMPLETION_PROJECT_DIR="$proj_dir"
    elif [[ -f "${proj_dir}/venv/bin/python3" ]]; then
        export MODEL_COMPLETION_PYTHON="${proj_dir}/venv/bin/python3"
        export MODEL_COMPLETION_PROJECT_DIR="$proj_dir"
    fi
fi

# Final fallback to system python
if [[ -z "$MODEL_COMPLETION_PYTHON" ]]; then
    if command -v python3 &> /dev/null; then
        export MODEL_COMPLETION_PYTHON="$(command -v python3)"
    else
        export MODEL_COMPLETION_PYTHON="python3"
    fi
fi

export MODEL_COMPLETION_CONFIG="${MODEL_COMPLETION_CONFIG:-~/.config/model-completer/config.yaml}"

# Check if the completer script exists
if [[ -z "$MODEL_COMPLETION_SCRIPT" || ! -f "$MODEL_COMPLETION_SCRIPT" ]]; then
    echo "❌ Error: model completer not found" >&2
    echo "   Please set MODEL_COMPLETION_PROJECT_DIR or ensure the project is installed" >&2
    return 1
fi

# Verify Python exists
if ! command -v "$MODEL_COMPLETION_PYTHON" &> /dev/null; then
    echo "⚠️  Warning: Python not found at $MODEL_COMPLETION_PYTHON" >&2
    if command -v python3 &> /dev/null; then
        export MODEL_COMPLETION_PYTHON="$(command -v python3)"
        echo "   Using system python3 instead" >&2
    else
        echo "❌ Error: No Python found" >&2
        return 1
    fi
fi

# Function to auto-start Ollama if not running
_model_completion_start_ollama() {
    # Check if already running
    if curl -s --max-time 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
        return 0
    fi
    
    # Check if ollama command exists
    if ! command -v ollama &> /dev/null; then
        return 1
    fi
    
    # Check if Ollama process already exists (might be starting)
    if pgrep -x ollama > /dev/null 2>&1; then
        # Wait for it to be ready (max 10 seconds)
        local wait_time=0
        while [[ $wait_time -lt 10 ]]; do
            if curl -s --max-time 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
                return 0
            fi
            sleep 1
            wait_time=$((wait_time + 1))
        done
    fi
    
    # Start Ollama in background
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    local ollama_pid=$!
    
    # Wait for server to be ready (max 15 seconds)
    local max_wait=15
    local waited=0
    while [[ $waited -lt $max_wait ]]; do
        if curl -s --max-time 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
            return 0
        fi
        
        # Check if process is still running
        if ! kill -0 $ollama_pid > /dev/null 2>&1; then
            # Process died
            return 1
        fi
        
        sleep 1
        waited=$((waited + 1))
    done
    
    # Timeout
    return 1
}

# Function to check if Ollama is available
_model_completion_check_ollama() {
    if curl -s --max-time 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Function to check if zsh-assistant model is available
_model_completion_check_zsh_assistant() {
    local models
    models=$(curl -s --max-time 3 http://localhost:11434/api/tags 2>/dev/null)
    if [[ -z "$models" ]]; then
        return 1
    fi
    # Try proper JSON parsing if Python available
    if command -v python3 &> /dev/null; then
        if echo "$models" | python3 -c "import sys, json; data = json.load(sys.stdin); exit(0 if any('zsh-assistant' in str(m.get('name', '')) for m in data.get('models', [])) else 1)" 2>/dev/null; then
            return 0
        fi
    fi
    # Fallback to grep
    if echo "$models" | grep -q '"name"[[:space:]]*:[[:space:]]*"zsh-assistant"'; then
        return 0
    fi
    return 1
}

# Function to check if models are available
_model_completion_check_models() {
    local models
    models=$($MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" --list-models 2>/dev/null)
    if [[ -z "$models" || "$models" == *"No models found"* ]]; then
        return 1
    fi
    return 0
}

# Function to ensure fine-tuned model is ready (silent)
_model_completion_ensure_ready() {
    # Try to start Ollama if not running (silently)
    if ! _model_completion_check_ollama; then
        _model_completion_start_ollama > /dev/null 2>&1
    fi
    
    # Check if zsh-assistant model exists
    if _model_completion_check_ollama && ! _model_completion_check_zsh_assistant; then
        # Model doesn't exist, but don't show error on startup
        # User can run ai-completion-setup manually
        return 1
    fi
    
    return 0
}


# Utility functions
ai-completion-test() {
    echo "🧪 Testing AI completions..."
    echo "Direct test:"
    $MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" "git comm"
}

ai-completion-status() {
    echo "📊 AI Completion Status"
    echo "   Python: $MODEL_COMPLETION_PYTHON"
    echo "   Script: $MODEL_COMPLETION_SCRIPT"
    echo "   Config: $MODEL_COMPLETION_CONFIG"
    echo ""
    
    # Check Ollama status
    if _model_completion_check_ollama; then
        echo "   Ollama: ✅ Running"
        # Check fine-tuned model
        if _model_completion_check_zsh_assistant; then
            echo "   Fine-tuned Model (zsh-assistant): ✅ Ready"
        else
            echo "   Fine-tuned Model (zsh-assistant): ⚠️  Not found"
            echo "      Run: ai-completion-setup"
        fi
    else
        echo "   Ollama: ❌ Not running"
        echo "      Auto-start will attempt to start on next terminal open"
    fi
    
    # Check models
    if _model_completion_check_models; then
        echo "   Models: ✅ Available"
    else
        echo "   Models: ❌ Not available"
    fi
    
    echo ""
    echo "✨ Enhanced Features:"
    echo "   - Smart commit messages"
    echo "   - Context-aware completions"
    echo "   - Personalized suggestions"
    echo "   - History learning"
    echo ""
    echo "💡 Use CLI commands to test completions!"
}

ai-completion-help() {
    echo "🎯 AI Autocomplete Help:"
    echo "   ai-completion-test  - Test the system"
    echo "   ai-completion-status - Check status"
    echo "   ai-completion-help  - Show this help"
    echo ""
    echo "🔧 Training Commands:"
    echo "   ai-completion-train - Start LoRA fine-tuning"
    echo "   ai-completion-data - Generate training data"
    echo "   ai-completion-models - List available models"
    echo "   ai-completion-setup - Setup Ollama and models"
    echo ""
    echo "💡 Use CLI directly:"
    echo "   model-completer \"git comm\""
    echo "   model-completer --commit-message"
}

ai-completion-train() {
    echo "🚀 Starting LoRA fine-tuning..."
    $MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" --train
}

ai-completion-data() {
    echo "📊 Generating training data..."
    $MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" --generate-data
}

ai-completion-models() {
    echo "🤖 Available models:"
    $MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" --list-models
}

ai-completion-setup() {
    echo "🔧 Setting up Ollama and fine-tuned model..."
    echo ""
    
    # Step 1: Ensure Ollama is installed and running
    echo "Step 1: Checking Ollama..."
    if ! command -v ollama &> /dev/null; then
        echo "❌ Ollama is not installed"
        echo "   Installing Ollama..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            curl -fsSL https://ollama.ai/install.sh | sh
        else
            curl -fsSL https://ollama.ai/install.sh | sh
        fi
    else
        echo "✅ Ollama is installed"
    fi
    
    # Start Ollama if not running
    if ! _model_completion_check_ollama; then
        echo "   Starting Ollama server..."
        _model_completion_start_ollama
        sleep 3
    fi
    
    if ! _model_completion_check_ollama; then
        echo "❌ Failed to start Ollama. Please start manually: ollama serve"
        return 1
    fi
    echo "✅ Ollama is running"
    echo ""
    
    # Step 2: Check for zsh-assistant model
    echo "Step 2: Checking fine-tuned model..."
    if _model_completion_check_zsh_assistant; then
        echo "✅ zsh-assistant model is ready"
    else
        echo "⚠️  zsh-assistant model not found"
        echo "   Generating training data..."
        $MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" --generate-data
        
        echo "   Training LoRA model (this may take a few minutes)..."
        $MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" --train
        
        echo "   Importing model to Ollama..."
        if $MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" --import-to-ollama 2>/dev/null; then
            if _model_completion_check_zsh_assistant; then
                echo "✅ Fine-tuned model is ready in Ollama!"
            else
                echo "⚠️  Model trained but not found in Ollama. Waiting..."
                sleep 3
                if _model_completion_check_zsh_assistant; then
                    echo "✅ Fine-tuned model is ready!"
                fi
            fi
        else
            echo "⚠️  Training completed but import to Ollama may have failed."
            echo "   You can run manually: $MODEL_COMPLETION_PYTHON $MODEL_COMPLETION_SCRIPT --import-to-ollama"
        fi
    fi
    echo ""
    
    echo "✅ Setup complete! Your AI autocomplete is ready."
    echo "   Try: model-completer \"git comm\""
}

# Auto-completion for the utility functions (only register if ZLE is active)
_ai_completion_utils() {
    # Only work in ZLE context
    if [[ -z "$ZLE_STATE" ]] && ! zle; then
        return 1
    fi
    local -a utils
    utils=(
        'test:Test AI completions'
        'status:Check system status'
        'help:Show help information'
        'train:Start LoRA fine-tuning'
        'data:Generate training data'
        'models:List available models'
        'setup:Setup Ollama and models'
    )
    _describe 'AI completion utilities' utils
}

# Only register completion if in interactive shell with ZLE
if [[ -o interactive ]] && zle; then
    compdef _ai_completion_utils ai-completion 2>/dev/null || true
fi

# Function to import LoRA model to Ollama
_model_completion_import_lora() {
    if [[ -z "$MODEL_COMPLETION_PROJECT_DIR" || -z "$MODEL_COMPLETION_PYTHON" ]]; then
        return 1
    fi
    
    local lora_path="${MODEL_COMPLETION_PROJECT_DIR}/zsh-lora-output"
    if [[ ! -d "$lora_path" || ! -f "$lora_path/adapter_config.json" ]]; then
        return 1
    fi
    
    # Import model synchronously
    cd "${MODEL_COMPLETION_PROJECT_DIR}" 2>/dev/null || return 1
    
    local import_output
    import_output=$($MODEL_COMPLETION_PYTHON -c "
import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.join('${MODEL_COMPLETION_PROJECT_DIR}', 'src'))
try:
    from model_completer.ollama_lora_import import import_lora_to_ollama
    base_dir = Path('${MODEL_COMPLETION_PROJECT_DIR}')
    success = import_lora_to_ollama(base_dir)
    sys.exit(0 if success else 1)
except Exception as e:
    print(f'Import error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
    
    local import_result=$?
    
    # Wait a moment for Ollama to register the model
    if [[ $import_result -eq 0 ]]; then
        sleep 2
        # Verify model is now available
        if _model_completion_check_zsh_assistant; then
            return 0
        fi
    fi
    
    return 1
}

# Function to ensure fine-tuned model is in Ollama
_model_completion_ensure_ollama_model() {
    # Step 1: Ensure Ollama is running
    if ! _model_completion_check_ollama; then
        if ! _model_completion_start_ollama > /dev/null 2>&1; then
            return 1
        fi
        # Wait for Ollama to be fully ready
        sleep 2
    fi
    
    # Step 2: Check if fine-tuned model exists in Ollama
    if _model_completion_check_zsh_assistant; then
        return 0
    fi
    
    # Step 3: Model not in Ollama - check if LoRA training completed and import it
    local lora_path="${MODEL_COMPLETION_PROJECT_DIR}/zsh-lora-output"
    if [[ -n "$MODEL_COMPLETION_PROJECT_DIR" && -d "$lora_path" && -f "$lora_path/adapter_config.json" ]]; then
        # LoRA model trained but not imported to Ollama - import it now
        if _model_completion_import_lora; then
            return 0
        fi
    fi
    
    return 1  # Model not available
}

# Auto-check on plugin load (silent, in background)
{
    set +e  # Don't exit on errors
    
    # Step 1: Start Ollama if not running
    local ollama_ready=0
    if ! _model_completion_check_ollama; then
        if _model_completion_start_ollama > /dev/null 2>&1; then
            ollama_ready=1
            # Wait for Ollama to be fully ready
            sleep 3
        else
            # Wait a bit more in case it's still starting
            sleep 2
            if _model_completion_check_ollama; then
                ollama_ready=1
            fi
        fi
    else
        ollama_ready=1
    fi
    
    # Step 2: Ensure fine-tuned model is in Ollama (with auto-import)
    local model_ready=0
    if [[ $ollama_ready -eq 1 ]]; then
        if _model_completion_ensure_ollama_model; then
            model_ready=1
        elif _model_completion_check_zsh_assistant; then
            model_ready=1
        fi
    fi
    
    # Step 3: Show status message
    local status_msg=""
    if [[ $ollama_ready -eq 1 && $model_ready -eq 1 ]]; then
        status_msg="✅ AI Autocomplete ready (Ollama + Fine-tuned model: zsh-assistant)"
    elif [[ $ollama_ready -eq 1 ]]; then
        status_msg="⚠️  AI Autocomplete ready (Ollama running, fine-tuned model not found - run 'ai-completion-setup')"
    else
        status_msg="⚠️  AI Autocomplete ready (Ollama not running - using training data fallback)"
    fi
    
    # Only print to interactive terminals
    if [[ -t 1 ]]; then
        echo "$status_msg"
    fi
} &!

