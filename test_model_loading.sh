#!/usr/bin/env zsh
# Test that model loading works correctly

echo "🧪 Testing Model Loading Process"
echo "================================="
echo ""

# Clear init files
rm -f /tmp/model-completer-init.*

echo "Step 1: Loading plugin..."
source src/scripts/zsh_autocomplete.plugin.zsh
echo "✅ Plugin loaded"
echo ""

echo "Step 2: Waiting for initialization (12 seconds)..."
for i in {1..12}; do
    sleep 1
    if [[ -f /tmp/model-completer-init.status ]]; then
        current_step=$(tail -1 /tmp/model-completer-init.status 2>/dev/null | grep "^step" || echo "")
        if [[ -n "$current_step" ]]; then
            echo "   [$i s] Step: $current_step"
        fi
    fi
done
echo ""

echo "Step 3: Final status check"
echo "--------------------------"
if [[ -f /tmp/model-completer-init.status ]]; then
    final_step=$(tail -1 /tmp/model-completer-init.status | grep "^step" || echo "")
    echo "Final step: $final_step"
    
    if [[ "$final_step" == *"model_ready"* ]]; then
        echo "✅ Model loading completed successfully!"
    elif [[ "$final_step" == *"loading_model"* ]]; then
        echo "⏳ Model still loading (may take a bit longer)"
    else
        echo "⚠️  Model not ready: $final_step"
    fi
else
    echo "❌ No status file found"
fi

echo ""
echo "Step 4: Testing model inference"
echo "-------------------------------"
result=$(curl -s --max-time 5 -X POST http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"zsh-assistant","prompt":"test","stream":false,"num_predict":2}' 2>/dev/null)

if [[ -n "$result" ]] && echo "$result" | grep -q '"response"' 2>/dev/null; then
    echo "✅ Model is ready and can respond to inference requests"
    echo "   This confirms the fine-tuned model is loaded and working!"
else
    echo "⚠️  Model inference test failed (model may still be loading)"
fi

echo ""
echo "Step 5: Checking log"
echo "---------------------"
if [[ -f /tmp/model-completer-init.log ]]; then
    echo "Last 3 log lines:"
    tail -3 /tmp/model-completer-init.log | sed 's/^/   /'
else
    echo "No log file found"
fi

echo ""
echo "================================="
echo "✅ Test complete"

