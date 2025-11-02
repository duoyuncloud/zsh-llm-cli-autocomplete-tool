#!/bin/bash
# Setup script to add model-completer to PATH

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BIN="$SCRIPT_DIR/venv/bin"
BIN_DIR="$SCRIPT_DIR/bin"

# Function to add to PATH if not already present
add_to_path() {
    local dir=$1
    if [[ ":$PATH:" != *":$dir:"* ]]; then
        export PATH="$dir:$PATH"
        echo "✅ Added $dir to PATH"
    else
        echo "ℹ️  $dir already in PATH"
    fi
}

# Add both venv/bin and bin to PATH
add_to_path "$VENV_BIN"
add_to_path "$BIN_DIR"

echo "✅ PATH setup complete!"
echo ""
echo "You can now use 'model-completer' command."
echo ""
echo "To make this permanent, add to your ~/.zshrc:"
echo "  export PATH=\"$VENV_BIN:\$PATH\""
echo "  export PATH=\"$BIN_DIR:\$PATH\""
echo ""
echo "Or source this script in your ~/.zshrc:"
echo "  source $SCRIPT_DIR/setup_path.sh"

