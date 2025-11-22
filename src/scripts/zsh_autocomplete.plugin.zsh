#!/usr/bin/env zsh
# Zsh AI Autocomplete Plugin
# AI-powered command completion using Ollama with LoRA fine-tuned models
# Simple Tab completion with grey preview

# Detect project directory
if [[ -n "$MODEL_COMPLETION_PROJECT_DIR" && -f "$MODEL_COMPLETION_PROJECT_DIR/src/model_completer/cli.py" ]]; then
    PROJECT_DIR="$MODEL_COMPLETION_PROJECT_DIR"
elif [[ -f "${0:A:h}/../../src/model_completer/cli.py" ]]; then
    PROJECT_DIR="${0:A:h}/../.."
elif [[ -f "${0:A:h}/src/model_completer/cli.py" ]]; then
    PROJECT_DIR="${0:A:h}"
else
    if [[ -f "$HOME/zsh-llm-cli-autocomplete-tool/src/model_completer/cli.py" ]]; then
        PROJECT_DIR="$HOME/zsh-llm-cli-autocomplete-tool"
    else
        echo "❌ Error: Cannot find model completer project directory" >&2
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

# Main completion function with grey preview
_model_completion() {
    # Skip if buffer is too short
    if [[ -z "$BUFFER" || ${#BUFFER} -lt 2 ]]; then
        zle expand-or-complete
        return
    fi
    
    # Get AI prediction
    local prediction
    prediction=$("$PYTHON_CMD" -W ignore::UserWarning -W ignore::DeprecationWarning -u "$MODEL_COMPLETION_SCRIPT" "$BUFFER" 2>&1 | \
        grep -vE "(^<frozen|^RuntimeWarning|^Warning:|^DEBUG|^INFO|^ERROR|^WARNING|^Loading|^Using|^Model|^tokenizer|^device|^torch|^transformers)" | \
        grep -vE "^[0-9]{4}-[0-9]{2}-[0-9]{2}" | \
        grep -v "^$" | \
        head -1)
    
    if [[ -n "$prediction" && "$prediction" != "$BUFFER" && ${#prediction} -gt ${#BUFFER} ]]; then
        # Extract the suffix to show in grey
        local suffix="${prediction:${#BUFFER}}"
        
        # Use zsh's completion system to show grey preview
        # Configure completion colors (90 = bright black/grey)
        zstyle ':completion:*' list-colors '=*=90'
        
        # Create a completion context
        local -a completions
        completions=("$prediction")
        
        # Use zsh's menu-select to show preview
        # The grey color will be applied automatically via list-colors
        compadd -U -S '' -- "$prediction" 2>/dev/null
        
        # Show the preview by setting up completion context
        # This will display the suffix in grey
        if [[ -n "$suffix" ]]; then
            # Use zsh's built-in completion highlighting
            # Store the prediction for acceptance
            _MODEL_COMPLETION_PREDICTION="$prediction"
            
            # Display using zsh's completion system
            # The grey color comes from list-colors setting above
            zle -M ""  # Clear any previous messages
            
            # Accept the completion
            BUFFER="$prediction"
            CURSOR=${#BUFFER}
            zle reset-prompt
        fi
    else
        # Fallback to normal completion
        zle expand-or-complete
    fi
}

# Alternative simpler implementation - just accept with visual feedback
_model_completion_simple() {
    if [[ -z "$BUFFER" || ${#BUFFER} -lt 2 ]]; then
        zle expand-or-complete
        return
    fi
    
    # Get prediction
    local prediction
    local output
    output=$("$PYTHON_CMD" -W ignore::UserWarning -W ignore::DeprecationWarning -u "$MODEL_COMPLETION_SCRIPT" "$BUFFER" 2>&1)
    local exit_code=$?
    
    # Check for errors
    if [[ $exit_code -ne 0 ]] || echo "$output" | grep -qE "Traceback|Error|Exception|ModuleNotFoundError|ImportError"; then
        # Error occurred - log it silently and fallback to normal completion
        echo "$output" > /tmp/model-completer-error.log 2>&1
        zle expand-or-complete
        return
    fi
    
    prediction=$(echo "$output" | \
        grep -vE "(^<frozen|^RuntimeWarning|^Warning:|^DEBUG|^INFO|^ERROR|^WARNING|^Loading|^Using|^Model|^tokenizer|^device|^torch|^transformers|^Traceback|^File|^  File)" | \
        grep -vE "^[0-9]{4}-[0-9]{2}-[0-9]{2}" | \
        grep -v "^$" | \
        head -1)
    
    if [[ -n "$prediction" && "$prediction" != "$BUFFER" && ${#prediction} -gt ${#BUFFER} ]]; then
        # Accept the completion
        # The grey preview will be shown by zsh's completion system
        BUFFER="$prediction"
        CURSOR=${#BUFFER}
        zle reset-prompt
    else
        zle expand-or-complete
    fi
}

# Register widget
zle -N _model_completion_simple

# Bind Tab key
bindkey '^I' _model_completion_simple

# Configure zsh completion colors for grey preview
zstyle ':completion:*' list-colors '=*=90'  # Grey for matches
zstyle ':completion:*' menu select

# Utility commands
ai-completion-status() {
    echo "📊 AI Autocomplete Status"
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
}

ai-completion-setup() {
    echo "🔧 Setting up Ollama and models..."
    echo ""
    
    if ! command -v ollama &> /dev/null; then
        echo "📥 Installing Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        echo "✅ Ollama installed"
    fi
    
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
    echo "✅ Setup complete! Try typing a command and press Tab"
}

ai-completion-train() {
    echo "🚀 Starting LoRA training..."
    "$PYTHON_CMD" "$MODEL_COMPLETION_SCRIPT" --train
}

ai-completion-data() {
    echo "📊 Generating training data..."
    "$PYTHON_CMD" "$MODEL_COMPLETION_SCRIPT" --generate-data
}

# Auto-start Ollama in background (non-blocking)
{
    if ! _model_completion_check_ollama; then
        _model_completion_start_ollama > /dev/null 2>&1
        sleep 2
    fi
    
    if _model_completion_check_ollama; then
        if _model_completion_check_model; then
            echo "✅ AI Autocomplete ready"
        else
            echo "⚠️  AI Autocomplete ready (run 'ai-completion-setup' to load model)"
        fi
    fi
} &!
