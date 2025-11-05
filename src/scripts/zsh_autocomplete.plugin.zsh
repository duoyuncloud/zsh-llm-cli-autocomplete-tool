#!/usr/bin/env zsh
# Zsh AI Autocomplete Plugin
# AI-powered command completion using Ollama with LoRA fine-tuned models

# Detect project directory
# Priority: 1) Environment variable, 2) Plugin location, 3) Common locations
if [[ -n "$MODEL_COMPLETION_PROJECT_DIR" && -f "$MODEL_COMPLETION_PROJECT_DIR/src/model_completer/cli.py" ]]; then
    # Use environment variable if set and valid
    PROJECT_DIR="$MODEL_COMPLETION_PROJECT_DIR"
elif [[ -f "${0:A:h}/../../src/model_completer/cli.py" ]]; then
    # Running from src/scripts/ (standard project layout)
    PROJECT_DIR="${0:A:h}/../.."
elif [[ -f "${0:A:h}/src/model_completer/cli.py" ]]; then
    # Running from project root
    PROJECT_DIR="${0:A:h}"
else
    # Try one common location
    if [[ -f "$HOME/zsh-llm-cli-autocomplete-tool/src/model_completer/cli.py" ]]; then
        PROJECT_DIR="$HOME/zsh-llm-cli-autocomplete-tool"
    else
        echo "❌ Error: Cannot find model completer project directory" >&2
        echo "   Set MODEL_COMPLETION_PROJECT_DIR or ensure plugin is in correct location" >&2
        return 1
    fi
fi

# Set paths
export MODEL_COMPLETION_PROJECT_DIR="$PROJECT_DIR"
export MODEL_COMPLETION_SCRIPT="$PROJECT_DIR/src/model_completer/cli.py"
export MODEL_COMPLETION_CONFIG="${MODEL_COMPLETION_CONFIG:-$HOME/.config/model-completer/config.yaml}"

# Verify script exists
if [[ ! -f "$MODEL_COMPLETION_SCRIPT" ]]; then
    echo "❌ Error: CLI script not found at $MODEL_COMPLETION_SCRIPT" >&2
    return 1
fi

# Find Python executable
if [[ -f "$PROJECT_DIR/venv/bin/python3" ]]; then
    PYTHON_CMD="$PROJECT_DIR/venv/bin/python3"
elif [[ -f "$PROJECT_DIR/venv/bin/python" ]]; then
    PYTHON_CMD="$PROJECT_DIR/venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="$(command -v python3)"
else
    echo "❌ Error: Python 3 not found" >&2
    return 1
fi

export MODEL_COMPLETION_PYTHON="$PYTHON_CMD"

# Verify Python works
if ! "$PYTHON_CMD" --version &> /dev/null; then
    echo "❌ Error: Python at $PYTHON_CMD is not working" >&2
    return 1
fi

# Helper functions
_model_completion_check_ollama() {
    curl -s --connect-timeout 0.3 --max-time 0.5 http://localhost:11434/api/tags > /dev/null 2>&1
}

_model_completion_start_ollama() {
    if command -v ollama &> /dev/null; then
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        sleep 2
    fi
}

_model_completion_check_model() {
    local models
    models=$(curl -s --connect-timeout 0.3 --max-time 0.5 http://localhost:11434/api/tags 2>/dev/null)
    [[ -n "$models" ]] && echo "$models" | grep -q "zsh-assistant"
}

# Completion functions
_model_completion_simple() {
    # Short buffer - use normal completion
    if [[ -z "$BUFFER" || ${#BUFFER} -lt 3 ]]; then
        zle expand-or-complete
        return
    fi
    
    # Get AI completion (Python handles timeouts and fallbacks)
    local completion
    completion=$("$PYTHON_CMD" -W ignore::UserWarning -W ignore::DeprecationWarning -u "$MODEL_COMPLETION_SCRIPT" "$BUFFER" 2>&1 | \
        grep -vE "(^<frozen|^RuntimeWarning|^Warning:|^DEBUG|^INFO|^ERROR|^WARNING|^Loading|^Using|^Model|^tokenizer|^device|^torch|^transformers)" | \
        grep -vE "^[0-9]{4}-[0-9]{2}-[0-9]{2}" | \
        grep -v "^$" | \
        head -1)
    
    if [[ -n "$completion" && "$completion" != "$BUFFER" && ${#completion} -gt ${#BUFFER} ]]; then
        BUFFER="$completion"
        CURSOR=${#BUFFER}
        zle reset-prompt
    else
        zle expand-or-complete
    fi
}

_model_completion_ui() {
    if [[ -z "$BUFFER" || ${#BUFFER} -lt 3 ]]; then
        zle expand-or-complete
        return
    fi
    
    local suggestions
    suggestions=$("$PYTHON_CMD" -W ignore::UserWarning -W ignore::DeprecationWarning -u "$MODEL_COMPLETION_SCRIPT" --suggestions 5 "$BUFFER" 2>&1 | \
        grep -vE "(^<frozen|^RuntimeWarning|^Warning:|^DEBUG|^INFO|^ERROR|^WARNING|^Loading|^Using|^Model|^tokenizer|^device|^torch|^transformers)" | \
        grep -vE "^[0-9]{4}-[0-9]{2}-[0-9]{2}" | \
        grep -v "^$")
    
    if [[ -n "$suggestions" ]]; then
        local -a completion_options
        while IFS= read -r line; do
            [[ -n "$line" ]] && completion_options+=("$line")
        done <<< "$suggestions"
        
        [[ ${#completion_options[@]} -gt 0 ]] && _describe 'AI suggestions' completion_options || zle expand-or-complete
    else
        zle expand-or-complete
    fi
}

_model_completion_advanced() {
    if [[ -z "$BUFFER" || ${#BUFFER} -lt 3 ]]; then
        zle expand-or-complete
        return
    fi
    
    local completion_info
    completion_info=$("$PYTHON_CMD" -W ignore::UserWarning -W ignore::DeprecationWarning -u "$MODEL_COMPLETION_SCRIPT" --advanced "$BUFFER" 2>&1 | \
        grep -vE "(^<frozen|^RuntimeWarning|^Warning:|^DEBUG|^INFO|^ERROR|^WARNING|^Loading|^Using|^Model|^tokenizer|^device|^torch|^transformers)" | \
        grep -vE "^[0-9]{4}-[0-9]{2}-[0-9]{2}" | \
        grep -v "^$" | \
        head -1)
    
    if [[ -n "$completion_info" ]]; then
        local completion="${completion_info%%|*}"
        local confidence="${completion_info##*|}"
        
        if [[ -n "$completion" && "$completion" != "$BUFFER" ]]; then
            BUFFER="$completion"
            CURSOR=${#BUFFER}
            zle reset-prompt
            [[ "$confidence" =~ ^[0-9]+$ ]] && [[ $confidence -gt 0 ]] && echo "🎯 Confidence: ${confidence}%"
        else
            zle expand-or-complete
        fi
    else
        zle expand-or-complete
    fi
}

# Register widgets
zle -N _model_completion_simple
zle -N _model_completion_ui
zle -N _model_completion_advanced

# Bind keys
bindkey '^I' _model_completion_simple        # Tab
bindkey '^[[Z' _model_completion_ui          # Shift+Tab
bindkey '^[[1;5I' _model_completion_advanced # Ctrl+Tab

# Utility commands
ai-completion-test() {
    echo "🧪 Testing AI completions..."
    echo "Try: git comm[Tab], docker run[Shift+Tab], npm run[Ctrl+Tab]"
    "$PYTHON_CMD" "$MODEL_COMPLETION_SCRIPT" "git comm"
}

ai-completion-status() {
    echo "📊 AI Completion Status"
    echo "   Project: $PROJECT_DIR"
    echo "   Python:  $PYTHON_CMD"
    echo ""
    
    if _model_completion_check_ollama; then
        echo "   Ollama: ✅ Running"
        if _model_completion_check_model; then
            echo "   Model:  ✅ zsh-assistant ready"
        else
            echo "   Model:  ⚠️  zsh-assistant not found (run: ai-completion-setup)"
        fi
    else
        echo "   Ollama: ❌ Not running"
        echo "   Model:  ⚠️  Not available"
    fi
    
    echo ""
    echo "💡 Usage: Tab (simple), Shift+Tab (UI), Ctrl+Tab (advanced)"
}

ai-completion-help() {
    echo "🎯 AI Autocomplete Help"
    echo ""
    echo "Completion Keys:"
    echo "   Tab        - Simple AI completion"
    echo "   Shift+Tab  - UI mode (multiple suggestions)"
    echo "   Ctrl+Tab   - Advanced mode (with confidence)"
    echo ""
    echo "Commands:"
    echo "   ai-completion-test    - Test the system"
    echo "   ai-completion-status  - Check status"
    echo "   ai-completion-setup   - Setup Ollama and models"
    echo "   ai-completion-train   - Start LoRA training"
    echo "   ai-completion-data    - Generate training data"
    echo "   ai-completion-models  - List available models"
}

ai-completion-setup() {
    echo "🔧 Setting up Ollama and models..."
    echo ""
    
    # Check Ollama
    if ! command -v ollama &> /dev/null; then
        echo "📥 Installing Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        echo "✅ Ollama installed"
    fi
    
    # Start Ollama
    if ! _model_completion_check_ollama; then
        echo "🚀 Starting Ollama server..."
        _model_completion_start_ollama
        sleep 3
    fi
    
    if ! _model_completion_check_ollama; then
        echo "❌ Failed to start Ollama. Please start manually: ollama serve"
        return 1
    fi
    echo "✅ Ollama running"
    echo ""
    
    # Check model
    if _model_completion_check_model; then
        echo "✅ zsh-assistant model ready"
    else
        echo "📊 Generating training data..."
        "$PYTHON_CMD" "$MODEL_COMPLETION_SCRIPT" --generate-data
        
        echo "🚀 Training LoRA model (this may take a few minutes)..."
        "$PYTHON_CMD" "$MODEL_COMPLETION_SCRIPT" --train
        
        echo "📦 Importing to Ollama..."
        "$PYTHON_CMD" "$MODEL_COMPLETION_SCRIPT" --import-to-ollama
        
        sleep 2
        if _model_completion_check_model; then
            echo "✅ Model ready!"
        else
            echo "⚠️  Model may need manual import"
        fi
    fi
    
    echo ""
    echo "✅ Setup complete! Try: git comm[Tab]"
}

ai-completion-train() {
    echo "🚀 Starting LoRA training..."
    "$PYTHON_CMD" "$MODEL_COMPLETION_SCRIPT" --train
}

ai-completion-data() {
    echo "📊 Generating training data..."
    "$PYTHON_CMD" "$MODEL_COMPLETION_SCRIPT" --generate-data
}

ai-completion-models() {
    echo "🤖 Available models:"
    "$PYTHON_CMD" "$MODEL_COMPLETION_SCRIPT" --list-models
}

# Auto-start Ollama in background (non-blocking)
{
    if ! _model_completion_check_ollama; then
        _model_completion_start_ollama > /dev/null 2>&1
        sleep 2
    fi
    
    if _model_completion_check_ollama; then
        if _model_completion_check_model; then
            echo "✅ AI Autocomplete ready (zsh-assistant model loaded)"
        else
            echo "⚠️  AI Autocomplete ready (run 'ai-completion-setup' to load fine-tuned model)"
        fi
    else
        echo "⚠️  AI Autocomplete ready (training data fallback mode)"
    fi
} &!
