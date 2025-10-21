#!/usr/bin/env zsh
# Enhanced Zsh AI Autocomplete Plugin
# Integrates with the existing Python modules for real functionality.

# Plugin configuration
export MODEL_COMPLETION_DIR="${0:A:h}"
export MODEL_COMPLETION_PYTHON="${MODEL_COMPLETION_PYTHON:-/Users/duoyun/Desktop/model-cli-autocomplete/venv/bin/python}"
export MODEL_COMPLETION_SCRIPT="/Users/duoyun/Desktop/model-cli-autocomplete/src/model_completer/cli.py"
export MODEL_COMPLETION_CONFIG="${MODEL_COMPLETION_CONFIG:-~/.config/model-completer/config.yaml}"

# Check if the completer script exists
if [[ ! -f "$MODEL_COMPLETION_SCRIPT" ]]; then
    echo "❌ Error: model completer not found at $MODEL_COMPLETION_SCRIPT" >&2
    return 1
fi

# Function to check if Ollama is available
_model_completion_check_ollama() {
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "⚠️  Ollama server not running. Start with: ollama serve" >&2
        return 1
    fi
    return 0
}

# Function to check if models are available
_model_completion_check_models() {
    local models
    models=$($MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" --list-models 2>/dev/null)
    if [[ -z "$models" || "$models" == *"No models found"* ]]; then
        echo "⚠️  No models available. Run: model-completer --generate-data && model-completer --train" >&2
        return 1
    fi
    return 0
}

# Simple completion function
_model_completion_simple() {
    if ! _model_completion_check_ollama; then
        zle expand-or-complete
        return
    fi
    
    if [[ -z "$BUFFER" ]]; then
        zle expand-or-complete
        return
    fi
    
    # Get AI completion using the existing completer
    local completion
    completion=$($MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" "$BUFFER" 2>/dev/null)
    
    if [[ -n "$completion" && "$completion" != "$BUFFER" ]]; then
        BUFFER="$completion"
        CURSOR=${#BUFFER}
        zle reset-prompt
    else
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
    else
        echo "   Ollama: ❌ Not running"
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
    echo "🔧 Setting up Ollama and models..."
    echo "This will install Ollama, download models, and create the zsh-assistant model."
    echo "This may take several minutes depending on your internet connection."
    echo ""
    read -q "REPLY?Continue? (y/N): "
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # This would need to be implemented as a separate script
        echo "💡 Run the install script: ./install.sh"
    else
        echo "Setup cancelled"
    fi
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

# Auto-check on plugin load
echo "🚀 AI Autocomplete Plugin Loaded"
if ! _model_completion_check_ollama; then
    echo "💡 Start Ollama with: ollama serve"
fi
if ! _model_completion_check_models; then
    echo "💡 Setup models with: ai-completion-setup"
fi
echo "💡 Type 'ai-completion-help' for usage tips"
