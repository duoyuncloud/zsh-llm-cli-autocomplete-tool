#!/usr/bin/env zsh
# Enhanced Zsh AI Autocomplete Plugin
# Integrates with the existing Python modules for real functionality.

# Plugin configuration
# Auto-detect installation directory (works from plugin dir or project root)
MODEL_COMPLETION_PROJECT_DIR=""

# First, try to find the project from the plugin location
# Priority: current project dir (zsh-llm-cli-autocomplete-tool) > old project dirs
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
    # Try current project first (zsh-llm-cli-autocomplete-tool)
    for dir in "$HOME/zsh-llm-cli-autocomplete-tool" "$HOME/Desktop/zsh-llm-cli-autocomplete-tool" "$HOME/zsh-llm-cli-autocomplete-tool"; do
        if [[ -f "$dir/src/model_completer/cli.py" ]]; then
            MODEL_COMPLETION_PROJECT_DIR="$dir"
            break
        fi
    done
    # Then try old project locations (lower priority)
    if [[ -z "$MODEL_COMPLETION_PROJECT_DIR" ]]; then
        for dir in "$HOME/Desktop/model-cli-autocomplete" "$HOME/model-cli-autocomplete" "$HOME/.model-cli-autocomplete" "/opt/model-cli-autocomplete" "/Users/duoyun/Desktop/model-cli-autocomplete"; do
            if [[ -f "$dir/src/model_completer/cli.py" ]]; then
                MODEL_COMPLETION_PROJECT_DIR="$dir"
                break
            fi
        done
    fi
fi

# If still not found, skip slow find operations during plugin load
# These are deferred to background initialization to avoid blocking
# Quick checks only - no filesystem searches
if [[ -z "$MODEL_COMPLETION_PROJECT_DIR" ]]; then
    # Quick path checks only (no find commands - they block!)
    for quick_path in "$HOME/zsh-llm-cli-autocomplete-tool" "$HOME/Desktop/zsh-llm-cli-autocomplete-tool"; do
        if [[ -f "$quick_path/src/model_completer/cli.py" ]]; then
            MODEL_COMPLETION_PROJECT_DIR="$quick_path"
            break
        fi
    done
fi

export MODEL_COMPLETION_DIR="${MODEL_COMPLETION_PROJECT_DIR}"

# Set script path first (needed to determine project dir)
if [[ -n "$MODEL_COMPLETION_PROJECT_DIR" ]]; then
    export MODEL_COMPLETION_SCRIPT="${MODEL_COMPLETION_PROJECT_DIR}/src/model_completer/cli.py"
else
    # Fallback: try to find it (prioritize current project)
    export MODEL_COMPLETION_SCRIPT=""
    for script_path in "$HOME/zsh-llm-cli-autocomplete-tool/src/model_completer/cli.py" \
                       "$HOME/Desktop/zsh-llm-cli-autocomplete-tool/src/model_completer/cli.py" \
                       "$HOME/Desktop/model-cli-autocomplete/src/model_completer/cli.py" \
                       "$HOME/model-cli-autocomplete/src/model_completer/cli.py" \
                       "/Users/duoyun/Desktop/model-cli-autocomplete/src/model_completer/cli.py"; do
        if [[ -f "$script_path" ]]; then
            export MODEL_COMPLETION_SCRIPT="$script_path"
            # Set project dir from script path (go up two levels: cli.py -> model_completer -> src -> project_root)
            # Use simple dirname to avoid blocking - realpath/readlink can be slow
            # For absolute paths, dirname works fine without symlink resolution
            export MODEL_COMPLETION_PROJECT_DIR="$(dirname "$(dirname "$script_path")")"
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

# Check if the completer script exists (non-blocking - just warn, don't fail)
if [[ -z "$MODEL_COMPLETION_SCRIPT" || ! -f "$MODEL_COMPLETION_SCRIPT" ]]; then
    # Don't block - just set a flag for background init to handle
    # The plugin will work for status checks even without the script
    export MODEL_COMPLETION_SCRIPT_MISSING=1
fi

# Verify Python exists (non-blocking - just set fallback)
if ! command -v "$MODEL_COMPLETION_PYTHON" &> /dev/null; then
    if command -v python3 &> /dev/null; then
        export MODEL_COMPLETION_PYTHON="$(command -v python3)"
    else
        # Don't fail - just use python3 as fallback (will fail later if needed)
        export MODEL_COMPLETION_PYTHON="python3"
    fi
fi

# Function to auto-start Ollama if not running (non-blocking version)
_model_completion_start_ollama() {
    # Check if already running (with short timeout)
    if curl -s --connect-timeout 0.3 --max-time 0.5 http://localhost:11434/api/tags > /dev/null 2>&1; then
        return 0
    fi
    
    # Check if ollama command exists
    if ! command -v ollama &> /dev/null; then
        return 1
    fi
    
    # Check if Ollama process already exists (might be starting)
    if pgrep -x ollama > /dev/null 2>&1; then
        # Quick check - don't wait long (max 2 seconds)
        local wait_time=0
        while [[ $wait_time -lt 2 ]]; do
            if curl -s --connect-timeout 0.3 --max-time 0.5 http://localhost:11434/api/tags > /dev/null 2>&1; then
                return 0
            fi
            sleep 0.5
            wait_time=$((wait_time + 1))
        done
    fi
    
    # Start Ollama in background (don't wait for it)
    nohup ollama serve > /tmp/ollama.log 2>&1 </dev/null &
    
    # Don't wait - return immediately and let it start in background
    return 0
}

# Function to check if Ollama is available (non-blocking)
_model_completion_check_ollama() {
    # Use very short timeouts to prevent blocking
    if curl -s --connect-timeout 0.3 --max-time 0.5 http://localhost:11434/api/tags > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Function to check if zsh-assistant model is available (non-blocking)
_model_completion_check_zsh_assistant() {
    local models
    # Use very short timeouts to prevent blocking
    models=$(curl -s --connect-timeout 0.3 --max-time 0.5 http://localhost:11434/api/tags 2>/dev/null || echo "")
    if [[ -z "$models" ]]; then
        return 1
    fi
    # Try proper JSON parsing if Python available (with timeout)
    if command -v python3 &> /dev/null; then
        if echo "$models" | timeout 0.3 python3 -c "import sys, json; data = json.load(sys.stdin); exit(0 if any('zsh-assistant' in str(m.get('name', '')) for m in data.get('models', [])) else 1)" 2>/dev/null; then
            return 0
        fi
    fi
    # Fallback to grep (fastest)
    if echo "$models" | grep -q '"name"[[:space:]]*:[[:space:]]*"zsh-assistant"' 2>/dev/null || echo "$models" | grep -q 'zsh-assistant' 2>/dev/null; then
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

ai-completion-debug() {
    echo "🔍 Debugging smart commit..."
    echo ""
    
    # Check git status
    echo "1. Git status:"
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "   ✅ In git repo"
        git status --short | head -5 | sed 's/^/   /'
        
        echo ""
        echo "2. Staged changes:"
        staged=$(git diff --cached --name-only 2>/dev/null)
        if [[ -n "$staged" ]]; then
            echo "$staged" | head -5 | sed 's/^/   /'
        else
            echo "   (none)"
        fi
        
        echo ""
        echo "3. Unstaged changes:"
        unstaged=$(git diff --name-only 2>/dev/null)
        if [[ -n "$unstaged" ]]; then
            echo "$unstaged" | head -5 | sed 's/^/   /'
        else
            echo "   (none)"
        fi
        
        echo ""
        echo "4. Testing smart commit:"
        if [[ -n "$MODEL_COMPLETION_PYTHON" && -n "$MODEL_COMPLETION_SCRIPT" ]]; then
            result=$($MODEL_COMPLETION_PYTHON "$MODEL_COMPLETION_SCRIPT" --commit-message 2>&1)
            echo "$result"
        else
            echo "   ❌ Python/script not set"
        fi
    else
        echo "   ❌ Not in git repo"
    fi
}

ai-completion-help() {
    echo "🎯 AI Autocomplete Help:"
    echo "   ai-completion-test     - Test the system"
    echo "   ai-completion-status   - Check status"
    echo "   ai-completion-debug    - Debug smart commit"
    echo "   ai-completion-help     - Show this help"
    echo ""
    echo "🔧 Training Commands:"
    echo "   ai-completion-train     - Start LoRA fine-tuning"
    echo "   ai-completion-data     - Generate training data"
    echo "   ai-completion-models   - List available models"
    echo "   ai-completion-setup    - Setup Ollama and models"
    echo ""
    echo "💡 Use CLI directly:"
    echo "   model-completer \"git comm\"           # Smart commit message"
    echo "   model-completer \"git\"                # Suggests 'git add' if unstaged changes"
    echo "   model-completer --commit-message     # Generate commit message from staged changes"
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

# Only register completion if in interactive shell
# Don't check zle() - it can block during plugin load
# Completion will work when zle is active during actual use
if [[ -o interactive ]]; then
    # Register completion - compdef is safe to call even if zle isn't ready yet
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

# Lightweight initialization function (only checks, no training)
# Training should be done manually via ai-completion-setup
# CRITICAL: This function must NEVER block - all operations use minimal timeouts
_model_completion_full_init() {
    local status_file="/tmp/model-completer-init.status"
    local log_file="/tmp/model-completer-init.log"
    
    # Clear previous status
    echo "" > "$status_file" 2>/dev/null
    echo "Initializing AI Autocomplete..." > "$log_file" 2>&1
    
    # Step 1: Ensure Ollama is running (quick check and start if needed)
    echo "step1:checking_ollama" > "$status_file"
    if ! command -v ollama >/dev/null 2>&1; then
        echo "step1:ollama_not_found" > "$status_file"
        echo "⚠️  Ollama not installed" >> "$log_file"
        return 0  # Don't fail - return success to avoid blocking
    fi
    
    # Quick check if Ollama is already running (non-blocking with ultra-short timeout)
    # Use connection timeout to prevent DNS/network blocking
    if curl -s --connect-timeout 0.3 --max-time 0.5 http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "step1:ollama_running" > "$status_file"
    else
        # Start Ollama in background without waiting (non-blocking)
        echo "step1:starting_ollama" > "$status_file"
        echo "Starting Ollama server (background)..." >> "$log_file"
        nohup ollama serve >/tmp/ollama.log 2>&1 </dev/null &
        # Don't wait - let it start in background
        echo "step1:ollama_starting" > "$status_file"
    fi
    
    # Step 2: Quick check if model exists (non-blocking, no training)
    echo "step2:checking_model" > "$status_file"
    
    # Quick check with ultra-short timeout (0.5 second max, completely non-blocking)
    local models
    # Use connection timeout to prevent DNS blocking, and very short max-time
    # If curl hangs, we want it to fail fast
    if command -v timeout >/dev/null 2>&1; then
        models=$(timeout 0.5 curl -s --connect-timeout 0.3 --max-time 0.5 http://localhost:11434/api/tags 2>/dev/null || echo "")
    else
        models=$(curl -s --connect-timeout 0.3 --max-time 0.5 http://localhost:11434/api/tags 2>/dev/null || echo "")
    fi
    
    local model_exists=0
    
    # Only check if we got a valid JSON response (Ollama is ready and responded)
    if [[ -n "$models" ]] && [[ "$models" == "{"* ]] && [[ "$models" != *"connection refused"* ]] && [[ "$models" != *"curl:"* ]] && [[ "$models" != *"timeout"* ]]; then
        # Quick parse - check for zsh-assistant (with or without :latest tag)
        # Use simple grep first (fastest)
        if echo "$models" | grep -q 'zsh-assistant' 2>/dev/null; then
            model_exists=1
        elif command -v jq >/dev/null 2>&1; then
            # If grep didn't work, try jq (but this is slower, use timeout)
            if echo "$models" 2>/dev/null | timeout 0.3 jq -e '.models[] | select(.name | startswith("zsh-assistant"))' >/dev/null 2>&1; then
                model_exists=1
            fi
        fi
        
        if [[ $model_exists -eq 1 ]]; then
            echo "step2:model_ready" > "$status_file"
            echo "✅ Model ready in Ollama" >> "$log_file"
            return 0
        fi
    else
        # Ollama not ready or no response - that's OK, just note it
        echo "step2:ollama_not_ready" > "$status_file"
        echo "Ollama not ready or starting..." >> "$log_file"
        # Don't fail - Ollama might still be starting
    fi
    
    # Model not found in Ollama - don't try to import automatically
    # Import should be done manually via ai-completion-setup
    echo "step2:model_not_found_in_ollama" > "$status_file"
    echo "⚠️  Model not in Ollama - run 'ai-completion-setup' if needed" >> "$log_file"
    return 0  # Don't fail - plugin can work with fallback
}

# Auto-initialization on plugin load (completely non-blocking)
# CRITICAL: This MUST NOT block the prompt - everything runs asynchronously
# Fork immediately and completely detach from shell with all file descriptors closed
(
    {
        # Close all file descriptors and redirect to log
        exec >/tmp/model-completer-init.log 2>&1 <&- || exec >/tmp/model-completer-init.log 2>&1
        
        # Set error handling - never fail
        set +e
        
        # Change directory immediately to avoid any cwd blocking
        cd /tmp 2>/dev/null || cd ~ 2>/dev/null || true
        
        # Variables
        status_file="/tmp/model-completer-init.status"
        log_file="/tmp/model-completer-init.log"
        
        # Initialize (quick check only)
        _model_completion_full_init
        init_result=$?
        
        # Write result
        echo "result:$init_result" >> "$status_file" 2>/dev/null || true
        
        # Prepare message
        message=""
        last_step=""
        if [[ -f "$status_file" ]]; then
            last_step=$(cat "$status_file" 2>/dev/null | grep "^step" | tail -1 || echo "")
        fi
        
        # Determine message
        if [[ "$last_step" == *"step2:model_ready"* ]]; then
            message="✅ AI Autocomplete ready (Fine-tuned model loaded in Ollama)"
        elif [[ "$last_step" == *"step2:lora_not_found"* ]] || [[ "$last_step" == *"step2:config_missing"* ]]; then
            message="⚠️  AI Autocomplete ready (Fine-tuned model not found - run 'ai-completion-setup')"
        elif [[ "$last_step" == *"step1:ollama_not_found"* ]] || [[ "$last_step" == *"step1:ollama_failed"* ]]; then
            message="⚠️  AI Autocomplete ready (Ollama not available - will use training data fallback)"
        elif [[ "$last_step" == *"step2:ollama_not_ready"* ]] || [[ "$last_step" == *"step1:ollama_starting"* ]]; then
            message="⏳ AI Autocomplete ready (Ollama starting in background)"
        else
            message="✅ AI Autocomplete ready (check 'ai-completion-status' for details)"
        fi
        
        # Write message (non-blocking)
        echo "$message" > /tmp/model-completer-init.msg 2>/dev/null || true
    } &
) &!

# Immediately disown to prevent blocking
disown -a 2>/dev/null || true

# Set up precmd hook to show initialization message when ready (non-blocking)
# This runs before each prompt, but only shows message once
# CRITICAL: Must be ultra-fast and never block - use static flag to skip after first run
if [[ -o interactive ]] && [[ -n "$ZSH_VERSION" ]]; then
    # Static flag to prevent multiple executions
    typeset -g _model_completion_msg_shown=0
    
    _model_completion_show_init_message() {
        # Fastest possible exit - check static variable first
        (( _model_completion_msg_shown )) && return 0
        
        # Fast exit if no message file (avoid filesystem check if possible)
        [[ ! -f /tmp/model-completer-init.msg ]] && return 0
        
        # Read message (quick operation with timeout protection)
        local msg
        msg=$(cat /tmp/model-completer-init.msg 2>/dev/null || true)
        [[ -z "$msg" ]] && return 0
        
        # Display message
        echo "$msg"
        
        # Mark as shown immediately (before any cleanup)
        _model_completion_msg_shown=1
        
        # Cleanup in background to not block
        (rm -f /tmp/model-completer-init.msg /tmp/model-completer-init.shown 2>/dev/null &)
    }
    
    # Initialize precmd_functions array if it doesn't exist
    [[ ${+precmd_functions} -eq 0 ]] && typeset -a precmd_functions
    
    # Add to precmd hooks (only once - use simple check)
    [[ "${precmd_functions[(ie)_model_completion_show_init_message]}" -gt "${#precmd_functions}" ]] && \
        precmd_functions+=(_model_completion_show_init_message)
fi

# The initialization is now running completely in background
# Status message will appear automatically when ready, or check with:
#   cat /tmp/model-completer-init.msg
#   ai-completion-status

