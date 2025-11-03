#!/usr/bin/env zsh
# Test LORA loading steps to identify where it hangs

echo "🧪 Testing LORA Loading Steps"
echo "=============================="
echo ""

# Step 1: Test Ollama Server
echo "Step 1: Testing Ollama Server"
echo "----------------------------"
if curl -s --connect-timeout 1 --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "✅ Ollama server is running"
    echo "   Models available:"
    curl -s http://localhost:11434/api/tags | python3 -m json.tool 2>/dev/null | grep -A 2 '"name"' | head -10 || echo "   (could not parse)"
else
    echo "❌ Ollama server is NOT running"
    echo "   Starting Ollama..."
    if command -v ollama >/dev/null 2>&1; then
        nohup ollama serve >/tmp/ollama-test.log 2>&1 &
        echo "   Waiting for Ollama to start..."
        sleep 3
        if curl -s --connect-timeout 1 --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "✅ Ollama started successfully"
        else
            echo "❌ Ollama failed to start"
        fi
    else
        echo "❌ Ollama not installed"
    fi
fi
echo ""

# Step 2: Test Model Fine-tuning Status
echo "Step 2: Testing Model Fine-tuning Status"
echo "----------------------------------------"
if [[ -d "zsh-lora-output" ]]; then
    echo "✅ LORA output directory exists"
    if [[ -f "zsh-lora-output/adapter_config.json" ]]; then
        echo "✅ adapter_config.json found"
        if [[ -f "zsh-lora-output/adapter_model.safetensors" ]]; then
            echo "✅ adapter_model.safetensors found"
            echo "   LORA model files are present"
        else
            echo "⚠️  adapter_model.safetensors NOT found"
        fi
    else
        echo "⚠️  adapter_config.json NOT found"
    fi
else
    echo "❌ LORA output directory does not exist"
fi
echo ""

# Step 3: Test Model Loading (THIS IS WHERE IT MIGHT HANG)
echo "Step 3: Testing Model Loading"
echo "-----------------------------"
echo "⚠️  WARNING: This step might take a long time or hang!"
echo "   Testing LORA model loading..."
echo ""

# Check if Python dependencies are available
if python3 -c "from transformers import AutoTokenizer" 2>/dev/null; then
    echo "✅ Transformers library available"
else
    echo "❌ Transformers library NOT available"
    echo "   Install with: pip install transformers peft"
    exit 1
fi

# Test if model loading blocks
echo "   Attempting to check LORA availability (non-blocking test)..."
STIME=$(date +%s.%N)

# Run in background with timeout simulation
(
    python3 -c "
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
try:
    from model_completer.lora_inference import is_lora_ready
    result = is_lora_ready()
    print('✅' if result else '❌', 'LORA is_available() returned:', result, flush=True)
except Exception as e:
    print('❌ Error:', str(e), flush=True)
    sys.exit(1)
" 2>&1
) &
PID=$!

# Wait max 5 seconds for the check (just availability, not loading)
for i in {1..10}; do
    if ! kill -0 $PID 2>/dev/null; then
        wait $PID
        break
    fi
    sleep 0.5
done

if kill -0 $PID 2>/dev/null; then
    echo "❌ is_lora_ready() is hanging! Killing process..."
    kill -9 $PID 2>/dev/null
    ETIME=$(date +%s.%N)
    DURATION=$(echo "$ETIME - $STIME" | bc)
    echo "   Process was running for ${DURATION} seconds before being killed"
else
    ETIME=$(date +%s.%N)
    DURATION=$(echo "$ETIME - $STIME" | bc)
    echo "✅ is_lora_ready() completed in ${DURATION} seconds"
fi

echo ""
echo "   Now testing ensure_lora_ready() - THIS IS WHERE IT LIKELY HANGS"
echo "   (This actually loads the model, which can take minutes)"
echo ""

# Check if we should test the actual loading
read -q "CONTINUE? Continue with actual model loading test? (y/N): " || echo "Skipping actual model load test"
if [[ "$CONTINUE" == "y" ]]; then
    echo ""
    echo "   Testing ensure_lora_ready() with 30 second timeout..."
    STIME=$(date +%s.%N)
    
    (
        timeout 30 python3 -c "
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
try:
    from model_completer.lora_inference import ensure_lora_ready
    print('Starting ensure_lora_ready()...', flush=True)
    result = ensure_lora_ready()
    print('✅ ensure_lora_ready() returned:', result, flush=True)
except Exception as e:
    print('❌ Error:', str(e), flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
" 2>&1
    ) &
    PID=$!
    
    # Monitor for 30 seconds
    for i in {1..60}; do
        if ! kill -0 $PID 2>/dev/null; then
            wait $PID
            break
        fi
        echo -n "."
        sleep 0.5
    done
    echo ""
    
    if kill -0 $PID 2>/dev/null; then
        echo "❌ ensure_lora_ready() is HANGING! Killing process..."
        kill -9 $PID 2>/dev/null
        ETIME=$(date +%s.%N)
        DURATION=$(echo "$ETIME - $STIME" | bc)
        echo "   Process was running for ${DURATION} seconds - LIKELY DOWNLOADING/MODEL LOADING"
    else
        ETIME=$(date +%s.%N)
        DURATION=$(echo "$ETIME - $STIME" | bc)
        echo "✅ ensure_lora_ready() completed in ${DURATION} seconds"
    fi
else
    echo "   Skipped actual model loading test"
fi

echo ""
echo "=============================="
echo "✅ Test complete"
echo ""
echo "💡 Findings:"
echo "   - If Step 1 fails: Ollama server issue"
echo "   - If Step 2 fails: LORA model files missing"
echo "   - If Step 3 hangs: Model loading is blocking (downloading base model?)"

