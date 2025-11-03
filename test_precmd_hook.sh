#!/usr/bin/env zsh
# Test the precmd hook specifically to check for blocking

echo "🧪 Testing precmd hook behavior..."
echo ""

# Clear any existing init files
rm -f /tmp/model-completer-init.*

# Create a test message file
echo "✅ AI Autocomplete ready (Fine-tuned model loaded in Ollama)" > /tmp/model-completer-init.msg
echo "step2:model_ready" > /tmp/model-completer-init.status
echo "result:0" >> /tmp/model-completer-init.status

# Source the plugin
echo "Loading plugin..."
source src/scripts/zsh_autocomplete.plugin.zsh
echo "✅ Plugin loaded"

# Simulate what happens when precmd hook runs
echo ""
echo "Simulating precmd hook execution..."
echo ""

# Set the hook function manually if not already set
if [[ ${+precmd_functions} -eq 0 ]]; then
    typeset -a precmd_functions
fi

# Check if hook is registered
if [[ ${precmd_functions[(I)_model_completion_show_init_message]} -gt 0 ]]; then
    echo "✅ Hook is registered"
    
    # Test the hook function directly (simulating what precmd does)
    echo "Testing hook function directly..."
    typeset -g _model_completion_msg_shown=0
    
    STIME=$(date +%s.%N)
    _model_completion_show_init_message
    ETIME=$(date +%s.%N)
    DURATION=$(echo "$ETIME - $STIME" | bc)
    
    echo "Hook execution time: ${DURATION} seconds"
    
    if (( $(echo "$DURATION > 0.05" | bc -l) )); then
        echo "❌ WARNING: Hook took more than 0.05 seconds - may be blocking!"
        exit 1
    else
        echo "✅ Hook execution is fast (non-blocking)"
    fi
    
    # Test second call (should return immediately)
    echo "Testing second call (should skip immediately)..."
    STIME=$(date +%s.%N)
    _model_completion_show_init_message
    ETIME=$(date +%s.%N)
    DURATION=$(echo "$ETIME - $STIME" | bc)
    
    echo "Second hook execution time: ${DURATION} seconds"
    
    if (( $(echo "$DURATION > 0.001" | bc -l) )); then
        echo "⚠️  Second call should be almost instant (< 0.001s)"
    else
        echo "✅ Second call is instant (correct behavior)"
    fi
else
    echo "⚠️  Hook not registered (might not be in interactive mode)"
fi

echo ""
echo "✅ Test complete"

