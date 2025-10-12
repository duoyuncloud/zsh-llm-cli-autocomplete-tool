#!/usr/bin/env zsh

# Zsh-specific AI-powered command completion with fine-tuned models

_MODEL_COMPLETION_DIR="${0:A:h}"
_MODEL_COMPLETION_PY="${_MODEL_COMPLETION_DIR}/model_completer/cli.py"

# Configuration
export MODEL_COMPLETION_OLLAMA_URL="${MODEL_COMPLETION_OLLAMA_URL:-http://localhost:11434}"
export MODEL_COMPLETION_MODEL="${MODEL_COMPLETION_MODEL:-zsh-assistant}"  # Use fine-tuned model
export MODEL_COMPLETION_CACHE_ENABLED="${MODEL_COMPLETION_CACHE_ENABLED:-1}"
export MODEL_COMPLETION_UI_ENABLED="${MODEL_COMPLETION_UI_ENABLED:-1}"

# Check if Python script exists
if [[ ! -f "$_MODEL_COMPLETION_PY" ]]; then
    echo "❌ Error: model_completer not found at $_MODEL_COMPLETION_PY" >&2
    return 1
fi

# Function to check if fine-tuned model is available
_model_completion_check_model() {
    local model_status
    model_status=$(python3 "$_MODEL_COMPLETION_PY" --list-models 2>/dev/null | grep -q "$MODEL_COMPLETION_MODEL" && echo "available" || echo "missing")
    
    if [[ "$model_status" == "missing" ]]; then
        echo "⚠️  Fine-tuned model '$MODEL_COMPLETION_MODEL' not found."
        echo "💡 Run: python3 -m training.finetune_zsh_lora to create it"
        return 1
    fi
    return 0
}

# Enhanced completion function with fine-tuned model
_model_completion_enhanced() {
    if ! _model_completion_check_model; then
        zle expand-or-complete
        return
    fi
    
    local completions
    completions=$(python3 "$_MODEL_COMPLETION_PY" --suggestions 1 "$BUFFER" 2>/dev/null)
    
    if [[ -n "$completions" ]]; then
        BUFFER="$completions"
        CURSOR=${#BUFFER}
    else
        zle expand-or-complete
    fi
}

# UI function with fine-tuned model suggestions
_model_completion_ui() {
    if ! _model_completion_check_model; then
        zle expand-or-complete
        return
    fi
    
    local suggestions
    suggestions=$(python3 "$_MODEL_COMPLETION_PY" --suggestions 3 --ui-mode "$BUFFER" 2>/dev/null)
    
    if [[ -n "$suggestions" ]]; then
        local first_line="${suggestions%%$'\n'*}"
        if [[ "$first_line" =~ "^UI_SUGGESTIONS:([0-9]+)$" ]]; then
            local suggestion_count=${match[1]}
            local suggestions_array=()
            
            while IFS= read -r line; do
                if [[ "$line" =~ "^([0-9]+):(.*)$" ]]; then
                    suggestions_array[${match[1]}+1]="${match[2]}"
                fi
            done <<< "${suggestions_output#$first_line$'\n'}"
            
            compadd -U -a suggestions_array
        fi
    else
        zle expand-or-complete
    fi
}

# Create widgets
zle -N _model_completion_enhanced
zle -N _model_completion_ui

# Bind keys based on UI preference
if [[ "$MODEL_COMPLETION_UI_ENABLED" -eq 1 ]]; then
    bindkey '^I' _model_completion_ui  # Tab for UI mode
else
    bindkey '^I' _model_completion_enhanced  # Tab for simple completion
fi

# Utility functions for model management
zsh-model-train() {
    # Train or update the fine-tuned model
    echo "🚀 Training Zsh-specific model..."
    python3 -m training.finetune_zsh_lora --data src/training/zsh_training_data.jsonl --name zsh-assistant
}

zsh-model-update() {
    # Update training data and retrain
    echo "📊 Updating training data..."
    python3 -m training.prepare_zsh_data --output src/training/zsh_training_data.jsonl
    zsh-model-train
}

zsh-model-test() {
    # Test the fine-tuned model
    echo "🧪 Testing Zsh model..."
    python3 -m training.finetune_zsh_lora --test --name zsh-assistant
}

zsh-model-status() {
    # Check model status
    echo "📋 Model Status:"
    python3 "$_MODEL_COMPLETION_PY" --list-models
    echo ""
    echo "🎯 Current model: $MODEL_COMPLETION_MODEL"
    echo "🔗 Ollama URL: $MODEL_COMPLETION_OLLAMA_URL"
}

# Auto-check model on plugin load
if ! _model_completion_check_model; then
    echo "💡 Tip: Run 'zsh-model-train' to create the fine-tuned model"
fi