#!/usr/bin/env zsh
# Enhanced Zsh AI Autocomplete Plugin
# Integrates with the existing Python modules for real functionality.

# Plugin configuration
# Auto-detect installation directory (works from plugin dir or project root)
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
    # Try to find it in common locations
    for dir in "$HOME/model-cli-autocomplete" "$HOME/.model-cli-autocomplete" "/opt/model-cli-autocomplete"; do
        if [[ -f "$dir/src/model_completer/cli.py" ]]; then
            MODEL_COMPLETION_PROJECT_DIR="$dir"
            break
        fi
    done
fi

export MODEL_COMPLETION_DIR="${MODEL_COMPLETION_PROJECT_DIR}"
export MODEL_COMPLETION_PYTHON="${MODEL_COMPLETION_PYTHON:-${MODEL_COMPLETION_PROJECT_DIR}/venv/bin/python}"
export MODEL_COMPLETION_SCRIPT="${MODEL_COMPLETION_PROJECT_DIR}/src/model_completer/cli.py"
export MODEL_COMPLETION_CONFIG="${MODEL_COMPLETION_CONFIG:-~/.config/model-completer/config.yaml}"

# If venv doesn't exist, try system python
if [[ ! -f "$MODEL_COMPLETION_PYTHON" ]]; then
    if command -v python3 &> /dev/null; then
        export MODEL_COMPLETION_PYTHON="$(command -v python3)"
    fi
fi

# Check if the completer script exists
if [[ ! -f "$MODEL_COMPLETION_SCRIPT" ]]; then
    echo "❌ Error: model completer not found at $MODEL_COMPLETION_SCRIPT" >&2
    return 1
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
    # Suppress all error output to avoid showing timeout messages
    completion=$($MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" "$BUFFER" 2>/dev/null)
    
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
    suggestions=$($MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" --suggestions 5 "$BUFFER" 2>/dev/null)
    
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
    completion_info=$($MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" --advanced "$BUFFER" 2>/dev/null)
    
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
        
        if _model_completion_check_zsh_assistant; then
            echo "✅ Fine-tuned model is ready!"
        else
            echo "⚠️  Training may have failed. Check logs or run manually:"
            echo "   python -m model_completer.cli --train"
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

# Auto-check on plugin load (silent, in background)
{
    # Ensure Ollama is running (start if needed)
    if ! _model_completion_check_ollama; then
        _model_completion_start_ollama
    fi
    
    # Check if fine-tuned model is ready
    if _model_completion_check_ollama && _model_completion_check_zsh_assistant; then
        # Everything ready - show minimal message
        echo "✅ AI Autocomplete ready (LoRA model: zsh-assistant)"
    elif _model_completion_check_ollama; then
        # Ollama running but model not ready
        echo "⚠️  AI Autocomplete ready (fine-tuned model not found - run 'ai-completion-setup')"
    else
        # Ollama not available
        echo "⚠️  AI Autocomplete ready (Ollama not available - will use training data fallback)"
    fi
} &!

