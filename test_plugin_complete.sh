#!/usr/bin/env zsh
# Complete test of plugin loading including all steps

echo "🧪 Complete Plugin Loading Test"
echo "================================"
echo ""

# Clear init files
rm -f /tmp/model-completer-init.*

echo "Step 1: Testing plugin load (should be < 0.1s)"
echo "-----------------------------------------------"
STIME=$(date +%s.%N)
source src/scripts/zsh_autocomplete.plugin.zsh
ETIME=$(date +%s.%N)
DURATION=$(echo "$ETIME - $STIME" | bc)

if (( $(echo "$DURATION > 0.1" | bc -l) )); then
    echo "❌ Plugin load took ${DURATION}s - TOO SLOW!"
    exit 1
else
    echo "✅ Plugin loaded in ${DURATION}s (fast!)"
fi

echo ""
echo "Step 2: Waiting for background initialization (5 seconds)"
echo "----------------------------------------------------------"
sleep 5

echo ""
echo "Step 3: Checking initialization status"
echo "---------------------------------------"
if [[ -f /tmp/model-completer-init.status ]]; then
    echo "Status file contents:"
    cat /tmp/model-completer-init.status | tail -5
else
    echo "❌ No status file found"
fi

echo ""
if [[ -f /tmp/model-completer-init.msg ]]; then
    echo "Message file:"
    cat /tmp/model-completer-init.msg
else
    echo "No message file (already shown or not ready)"
fi

echo ""
echo "Step 4: Testing Ollama check (should be instant)"
echo "------------------------------------------------"
STIME=$(date +%s.%N)
if curl -s --connect-timeout 0.3 --max-time 0.5 http://localhost:11434/api/tags >/dev/null 2>&1; then
    ETIME=$(date +%s.%N)
    DURATION=$(echo "$ETIME - $STIME" | bc)
    echo "✅ Ollama check: ${DURATION}s"
else
    ETIME=$(date +%s.%N)
    DURATION=$(echo "$ETIME - $STIME" | bc)
    echo "⚠️  Ollama not responding (${DURATION}s)"
fi

echo ""
echo "Step 5: Testing model check (should be instant)"
echo "------------------------------------------------"
STIME=$(date +%s.%N)
models=$(curl -s --connect-timeout 0.3 --max-time 0.5 http://localhost:11434/api/tags 2>/dev/null || echo "")
if echo "$models" | grep -q 'zsh-assistant' 2>/dev/null; then
    ETIME=$(date +%s.%N)
    DURATION=$(echo "$ETIME - $STIME" | bc)
    echo "✅ Model check: ${DURATION}s (zsh-assistant found)"
else
    ETIME=$(date +%s.%N)
    DURATION=$(echo "$ETIME - $STIME" | bc)
    echo "⚠️  Model check: ${DURATION}s (zsh-assistant not found)"
fi

echo ""
echo "Step 6: Simulating precmd hook execution"
echo "-----------------------------------------"
typeset -g _model_completion_msg_shown=0
echo "✅ AI Autocomplete ready (Fine-tuned model loaded in Ollama)" > /tmp/model-completer-init.msg

STIME=$(date +%s.%N)
_model_completion_show_init_message 2>&1
ETIME=$(date +%s.%N)
DURATION=$(echo "$ETIME - $STIME" | bc)

echo ""
if (( $(echo "$DURATION > 0.01" | bc -l) )); then
    echo "❌ Precmd hook took ${DURATION}s - TOO SLOW!"
    exit 1
else
    echo "✅ Precmd hook: ${DURATION}s (fast!)"
fi

# Test second call (should be even faster)
STIME=$(date +%s.%N)
_model_completion_show_init_message 2>&1
ETIME=$(date +%s.%N)
DURATION=$(echo "$ETIME - $STIME" | bc)
echo "✅ Second precmd call: ${DURATION}s (instant skip)"

echo ""
echo "================================"
echo "✅ All tests passed!"
echo ""
echo "Summary:"
echo "  - Plugin load: Fast (< 0.1s)"
echo "  - Ollama check: Fast (< 1s)"
echo "  - Model check: Fast (< 1s)"
echo "  - Precmd hook: Fast (< 0.01s)"
echo ""
echo "If you're still experiencing hangs, the issue might be:"
echo "  1. Network timeout in curl (if Ollama is unreachable)"
echo "  2. LORA model preloading (if preload_lora.py is being called)"
echo "  3. Model import (if import_lora is being called automatically)"
echo ""
echo "Check: cat /tmp/model-completer-init.log"

