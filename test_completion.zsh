#!/usr/bin/env zsh
# Test script to verify completion works

echo "🧪 Testing AI Completion System"
echo ""

# Source the plugin
source ~/.zsh-plugins/zsh-autocomplete/zsh_autocomplete.plugin.zsh 2>&1 | grep -v 'command not found'

echo ""
echo "Configuration:"
echo "  PROJECT_DIR: $MODEL_COMPLETION_PROJECT_DIR"
echo "  SCRIPT: $MODEL_COMPLETION_SCRIPT"
echo "  PYTHON: $MODEL_COMPLETION_PYTHON"
echo ""

# Test completion
echo "Testing completion for 'git comm':"
if [[ -f "$MODEL_COMPLETION_SCRIPT" ]]; then
    py_cmd="$MODEL_COMPLETION_PYTHON"
    if [[ ! -f "$py_cmd" ]] || [[ "$py_cmd" == "/venv/bin/python"* ]]; then
        py_cmd="python3"
    fi
    result=$($py_cmd "$MODEL_COMPLETION_SCRIPT" "git comm" 2>&1)
    echo "  Result: $result"
    if [[ "$result" == *"git commit"* ]]; then
        echo "  ✅ Completion working!"
    else
        echo "  ⚠️  Completion may not be working correctly"
    fi
else
    echo "  ❌ Script not found"
fi

echo ""
echo "To test in your terminal:"
echo "  1. Reload zsh: source ~/.zshrc"
echo "  2. Type: git comm[Tab]"
echo "  3. It should complete to: git commit -m \"commit message\""

