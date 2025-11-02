#!/bin/bash
# Quick fix script to make model-completer command available

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Fixing model-completer command availability..."
echo ""

# Add to PATH for current session
export PATH="$SCRIPT_DIR/venv/bin:$PATH"
export PATH="$SCRIPT_DIR/bin:$PATH"

echo "✅ Added to PATH for current session"
echo ""

# Check if command works
if command -v model-completer &> /dev/null; then
    echo "✅ Command 'model-completer' is now available!"
    echo ""
    echo "Test it:"
    echo "  model-completer --help"
    echo ""
else
    echo "⚠️  Command still not found. Try:"
    echo "  source $SCRIPT_DIR/venv/bin/activate"
    echo "  python3 -m model_completer.cli --help"
    echo ""
fi

# Add to ~/.zshrc if requested
read -q "REPLY?Add to ~/.zshrc for permanent access? (y/N): "
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if ! grep -q "model-cli-autocomplete.*PATH" ~/.zshrc 2>/dev/null; then
        echo "" >> ~/.zshrc
        echo "# Model CLI Autocomplete - PATH setup" >> ~/.zshrc
        echo "export PATH=\"$SCRIPT_DIR/venv/bin:\$PATH\"" >> ~/.zshrc
        echo "export PATH=\"$SCRIPT_DIR/bin:\$PATH\"" >> ~/.zshrc
        echo "✅ Added to ~/.zshrc"
        echo "   Run: source ~/.zshrc"
    else
        echo "ℹ️  Already in ~/.zshrc"
    fi
fi

