#!/bin/bash

# Zsh AI Autocomplete - Training Script
set -e

echo "🤖 Starting Zsh AI Autocomplete Training Pipeline"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Check if we're in the right directory
if [ ! -f "src/training/axolotl_trainer.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Step 2: Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Step 3: Generate training data
print_status "Step 1: Generating training data..."
python3 -m training.prepare_zsh_data --max-examples 300

# Step 4: Convert to Axolotl format
print_status "Step 2: Converting to Axolotl format..."
python3 -m training.convert_to_axolotl_format

# Step 5: Check if low memory mode should be used
if [ "$1" == "--low-memory" ]; then
    print_warning "Using low memory configuration"
    LOW_MEMORY_FLAG="--low-memory"
else
    LOW_MEMORY_FLAG=""
fi

# Step 6: Start training
print_status "Step 3: Starting LoRA fine-tuning..."
print_warning "This will take 30 minutes to 2 hours depending on your hardware"
print_warning "Do not interrupt the process once it starts"

python3 -m training.axolotl_trainer $LOW_MEMORY_FLAG

# Step 7: Final message
if [ $? -eq 0 ]; then
    echo
    print_status "🎉 Training completed successfully!"
    echo
    print_status "Your fine-tuned LoRA adapter is ready in: zsh-lora-output/"
    echo
    print_status "To use your fine-tuned model:"
    echo "  1. The adapter can be loaded with transformers + peft"
    echo "  2. For Ollama integration, await official LoRA support"
    echo "  3. Check adapter files: ls -la zsh-lora-output/"
else
    print_error "Training failed. Check the error messages above."
    exit 1
fi