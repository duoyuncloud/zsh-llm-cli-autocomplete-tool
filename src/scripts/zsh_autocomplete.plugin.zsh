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
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        # Check if ollama command exists
        if command -v ollama &> /dev/null; then
            # Start Ollama in background
            nohup ollama serve > /tmp/ollama.log 2>&1 &
            # Wait a moment for it to start
            sleep 2
            # Check again
            if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
                return 0
            fi
        fi
        return 1
    fi
    return 0
}

# Function to check if Ollama is available
_model_completion_check_ollama() {
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        return 1
    fi
    return 0
}

# Function to check if zsh-assistant model is available
_model_completion_check_zsh_assistant() {
    local models
    models=$(curl -s http://localhost:11434/api/tags 2>/dev/null)
    if [[ -z "$models" ]]; then
        return 1
    fi
    # Check if zsh-assistant is in the list
    if echo "$models" | grep -q "zsh-assistant"; then
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

# Simple completion function
_model_completion_simple() {
    # Always allow normal completion if buffer is empty or very short
    if [[ -z "$BUFFER" || ${#BUFFER} -lt 3 ]]; then
        zle expand-or-complete
        return
    fi
    
    # Check Ollama but don't block if it's not available
    if ! _model_completion_check_ollama; then
        # Still try completion (will use training data fallback)
    fi
    
    # Get AI completion using the existing completer
    # Python code now handles timeouts internally and uses training data first
    local completion
    # Use python3 as fallback if venv python not found
    local py_cmd="$MODEL_COMPLETION_PYTHON"
    if [[ ! -f "$py_cmd" ]] || [[ "$py_cmd" == "/venv/bin/python"* ]]; then
        py_cmd="python3"
    fi
    # Suppress ALL output - stderr, warnings, and Python runtime messages
    # Only capture clean completion text
    # Filter aggressively to remove all Python/Warning/Log messages
    completion=$($py_cmd -W ignore::UserWarning -W ignore::DeprecationWarning -u "$MODEL_COMPLETION_SCRIPT" "$BUFFER" 2>&1 | \
        grep -vE "(^<frozen|^RuntimeWarning|^Warning:|^DEBUG|^INFO|^ERROR|^WARNING|^Loading|^Using|^Model|^tokenizer|^device|^torch|^transformers)" | \
        grep -vE "^[0-9]{4}-[0-9]{2}-[0-9]{2}" | \
        grep -v "^$" | \
        head -1)
    
    # Check if we got a valid completion
    if [[ -n "$completion" && "$completion" != "$BUFFER" && ${#completion} -gt ${#BUFFER} ]]; then
        BUFFER="$completion"
        CURSOR=${#BUFFER}
        zle reset-prompt
    else
        # Fall back to normal zsh completion
        zle expand-or-complete
    fi
}

# UI completion function with multiple suggestions
_model_completion_ui() {
    if ! _model_completion_check_ollama; then
        zle expand-or-complete
        return
    fi
    
    if [[ -z "$BUFFER" ]]; then
        zle expand-or-complete
        return
    fi
    
    # Get multiple suggestions
    local suggestions
    local py_cmd="$MODEL_COMPLETION_PYTHON"
    if [[ ! -f "$py_cmd" ]] || [[ "$py_cmd" == "/venv/bin/python"* ]]; then
        py_cmd="python3"
    fi
    # Suppress all output except suggestions
    suggestions=$($py_cmd -W ignore::UserWarning -W ignore::DeprecationWarning -u "$MODEL_COMPLETION_SCRIPT" --suggestions 5 "$BUFFER" 2>&1 | \
        grep -vE "(^<frozen|^RuntimeWarning|^Warning:|^DEBUG|^INFO|^ERROR|^WARNING|^Loading|^Using|^Model|^tokenizer|^device|^torch|^transformers)" | \
        grep -vE "^[0-9]{4}-[0-9]{2}-[0-9]{2}" | \
        grep -v "^$")
    
    if [[ -n "$suggestions" ]]; then
        # Parse suggestions and create completion menu
        local -a completion_options
        local line_num=1
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                completion_options+=("$line")
            fi
        done <<< "$suggestions"
        
        if [[ ${#completion_options[@]} -gt 0 ]]; then
            # Use Zsh's built-in completion menu
            _describe 'AI suggestions' completion_options
        else
            zle expand-or-complete
        fi
    else
        zle expand-or-complete
    fi
}

# Advanced completion with confidence scores
_model_completion_advanced() {
    if ! _model_completion_check_ollama; then
        zle expand-or-complete
        return
    fi
    
    if [[ -z "$BUFFER" ]]; then
        zle expand-or-complete
        return
    fi
    
    # Get completion with confidence
    local completion_info
    local py_cmd="$MODEL_COMPLETION_PYTHON"
    if [[ ! -f "$py_cmd" ]] || [[ "$py_cmd" == "/venv/bin/python"* ]]; then
        py_cmd="python3"
    fi
    # Suppress all warnings and debug output
    completion_info=$($py_cmd -W ignore::UserWarning -W ignore::DeprecationWarning -u "$MODEL_COMPLETION_SCRIPT" --advanced "$BUFFER" 2>&1 | \
        grep -vE "(^<frozen|^RuntimeWarning|^Warning:|^DEBUG|^INFO|^ERROR|^WARNING|^Loading|^Using|^Model|^tokenizer|^device|^torch|^transformers)" | \
        grep -vE "^[0-9]{4}-[0-9]{2}-[0-9]{2}" | \
        grep -v "^$" | \
        head -1)
    
    if [[ -n "$completion_info" ]]; then
        # Parse completion and confidence
        local completion="${completion_info%%|*}"
        local confidence="${completion_info##*|}"
        
        if [[ -n "$completion" && "$completion" != "$BUFFER" ]]; then
            BUFFER="$completion"
            CURSOR=${#BUFFER}
            zle reset-prompt
            
            # Show confidence if available
            if [[ "$confidence" =~ ^[0-9]+$ ]] && [[ $confidence -gt 0 ]]; then
                echo "🎯 Confidence: ${confidence}%"
            fi
        else
            zle expand-or-complete
        fi
    else
        zle expand-or-complete
    fi
}

# Create widgets
zle -N _model_completion_simple
zle -N _model_completion_ui
zle -N _model_completion_advanced

# Bind keys
bindkey '^I' _model_completion_simple        # Tab for simple completion
bindkey '^[[Z' _model_completion_ui          # Shift+Tab for UI mode
bindkey '^[[1;5I' _model_completion_advanced # Ctrl+Tab for advanced mode

# Utility functions
ai-completion-test() {
    echo "🧪 Testing AI completions..."
    echo "Try these commands with different keys:"
    echo "  git comm[Tab]        -> Simple completion"
    echo "  docker run[Shift+Tab] -> UI mode with multiple suggestions"
    echo "  npm run[Ctrl+Tab]     -> Advanced mode with confidence"
    echo ""
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
    echo "🎯 Completion Modes:"
    echo "   Tab        - Simple completion"
    echo "   Shift+Tab  - UI mode (multiple suggestions)"
    echo "   Ctrl+Tab   - Advanced mode (with confidence)"
    echo ""
    echo "✨ Enhanced Features:"
    echo "   - Smart commit messages (git comm[Tab])"
    echo "   - Context-aware completions"
    echo "   - Personalized suggestions"
    echo "   - History learning"
    echo ""
    echo "💡 Just type commands and use the keys above!"
}

ai-completion-help() {
    echo "🎯 AI Autocomplete Help:"
    echo "   Tab                 - Simple AI completion"
    echo "   Shift+Tab           - UI mode with multiple suggestions"
    echo "   Ctrl+Tab            - Advanced mode with confidence scores"
    echo "   ai-completion-test  - Test the system"
    echo "   ai-completion-status - Check status"
    echo "   ai-completion-help  - Show this help"
    echo ""
    echo "🔧 Training Commands:"
    echo "   ai-completion-train - Start LoRA fine-tuning"
    echo "   ai-completion-data - Generate training data"
    echo "   ai-completion-models - List available models"
    echo "   ai-completion-setup - Setup Ollama and models"
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
    echo "   Try: git comm[Tab]"
}

# Auto-completion for the utility functions
_ai_completion_utils() {
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

compdef _ai_completion_utils ai-completion

# Function to ensure fine-tuned model is in Ollama
_model_completion_ensure_ollama_model() {
    # Check if Ollama is running
    if ! _model_completion_check_ollama; then
        # Try to start Ollama
        _model_completion_start_ollama > /dev/null 2>&1
        sleep 2
    fi
    
    # Check if fine-tuned model exists in Ollama
    if _model_completion_check_zsh_assistant; then
        return 0
    fi
    
    # Model not in Ollama - check if LoRA training completed
    local lora_path="${MODEL_COMPLETION_PROJECT_DIR}/zsh-lora-output"
    if [[ -d "$lora_path" && -f "$lora_path/adapter_config.json" ]]; then
        # LoRA model trained but not imported to Ollama
        # Import it in background
        (
            $MODEL_COMPLETION_PYTHON -c "
import sys
sys.path.insert(0, '${MODEL_COMPLETION_PROJECT_DIR}/src')
from model_completer.ollama_lora_import import import_lora_to_ollama
import_lora_to_ollama()
" > /dev/null 2>&1
        ) &!
        return 1  # Not ready yet
    fi
    
    return 1  # Model not available
}

# Auto-check on plugin load (silent, in background)
{
    # Ensure Ollama is running (start if needed)
    if ! _model_completion_check_ollama; then
        _model_completion_start_ollama > /dev/null 2>&1
        sleep 2
    fi
    
    # Ensure fine-tuned model is in Ollama
    if _model_completion_ensure_ollama_model; then
        # Fine-tuned model is ready in Ollama - best case
        echo "✅ AI Autocomplete ready (Fine-tuned model loaded in Ollama)"
    elif _model_completion_check_ollama && _model_completion_check_zsh_assistant; then
        # Ollama with zsh-assistant model available
        echo "✅ AI Autocomplete ready (Ollama model: zsh-assistant)"
    elif _model_completion_check_ollama; then
        # Ollama running but no fine-tuned model
        echo "⚠️  AI Autocomplete ready (Ollama available, fine-tuned model not found - run 'ai-completion-setup')"
    else
        # Only training data fallback
        echo "⚠️  AI Autocomplete ready (training data fallback mode)"
    fi
} &!

