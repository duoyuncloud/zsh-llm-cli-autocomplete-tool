#!/usr/bin/env zsh
# Test script to verify initialization doesn't block

echo "🧪 Testing plugin initialization..."
echo ""

# Source the plugin
source src/scripts/zsh_autocomplete.plugin.zsh

echo ""
echo "✅ Plugin loaded - checking if prompt is available..."
echo "   (If you see this immediately, initialization is non-blocking)"

# Wait a moment and check status files
sleep 2
echo ""
echo "📊 Initialization status:"
if [[ -f /tmp/model-completer-init.msg ]]; then
    echo "   Message: $(cat /tmp/model-completer-init.msg)"
else
    echo "   Message: (not ready yet or already shown)"
fi

if [[ -f /tmp/model-completer-init.status ]]; then
    echo "   Status: $(cat /tmp/model-completer-init.status | tail -1)"
else
    echo "   Status: (not started yet)"
fi

echo ""
echo "🔍 Checking processes..."
ps aux | grep -E "(ollama|model-completer)" | grep -v grep | head -3 || echo "   No background processes found"

echo ""
echo "✅ Test complete - prompt should be immediately available!"
