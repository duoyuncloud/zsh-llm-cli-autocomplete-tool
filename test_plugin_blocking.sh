#!/usr/bin/env zsh
# Test script to verify plugin doesn't block

echo "🧪 Testing plugin for blocking behavior..."
echo ""

# Clear any existing init files
rm -f /tmp/model-completer-init.*

# Measure load time
STIME=$(date +%s.%N)
source src/scripts/zsh_autocomplete.plugin.zsh >/tmp/plugin-test.log 2>&1
ETIME=$(date +%s.%N)
DURATION=$(echo "$ETIME - $STIME" | bc)

echo "Plugin load time: ${DURATION} seconds"
echo ""

if (( $(echo "$DURATION > 0.1" | bc -l) )); then
    echo "❌ WARNING: Plugin took more than 0.1 seconds - may be blocking!"
    echo "   This should be < 0.05 seconds for non-blocking"
    exit 1
else
    echo "✅ Plugin load is fast (non-blocking)"
fi

echo ""
echo "Checking for background processes..."
ps aux | grep -E "model-completer|ollama.*serve" | grep -v grep | head -3 || echo "✅ No blocking processes found"

echo ""
sleep 1
echo "Initialization status:"
cat /tmp/model-completer-init.status 2>/dev/null | tail -3 || echo "Still initializing..."

echo ""
echo "✅ Test complete"
