# Installation Guide

## 🚀 Quick Installation (One Command)

For the easiest installation experience:

```bash
git clone https://github.com/yourusername/model-cli-autocomplete.git
cd model-cli-autocomplete
./install.sh
source ~/.zshrc
```

That's it! The install script will:
- ✅ Set up Python virtual environment
- ✅ Install all dependencies
- ✅ Install Ollama
- ✅ Download base models
- ✅ Train LoRA fine-tuned model
- ✅ Configure zsh plugin
- ✅ Set up auto-start on terminal open

## 📋 Manual Installation Steps

If you prefer to install manually or the script fails:

### 1. Prerequisites

- **Python 3.8+** with pip
- **Zsh shell**
- **curl** (for Ollama installation)
- **Git** (optional, for cloning)

Check prerequisites:
```bash
python3 --version  # Should be 3.8+
zsh --version
curl --version
```

### 2. Clone or Download

```bash
git clone https://github.com/yourusername/model-cli-autocomplete.git
cd model-cli-autocomplete
```

Or download and extract the zip file.

### 3. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -e .
pip install -r requirements-training.txt  # For LoRA training
```

### 4. Install Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Or download from https://ollama.ai
```

### 5. Configure Zsh Plugin

#### Option A: Using Oh My Zsh

```bash
# Create plugins directory if it doesn't exist
mkdir -p ~/.oh-my-zsh/custom/plugins

# Copy plugin
cp -r src/scripts/zsh_autocomplete.plugin.zsh ~/.oh-my-zsh/custom/plugins/

# Update ~/.zshrc
echo 'plugins=(... zsh_autocomplete)' >> ~/.zshrc
```

#### Option B: Direct Installation

```bash
# Add to ~/.zshrc
echo 'source /path/to/model-cli-autocomplete/src/scripts/zsh_autocomplete.plugin.zsh' >> ~/.zshrc
```

### 6. Initial Setup

```bash
# Generate training data
python -m model_completer.cli --generate-data

# Train LoRA model (optional but recommended)
python -m model_completer.cli --train
```

### 7. Reload Shell

```bash
source ~/.zshrc
```

Or open a new terminal window.

## ✨ Automatic Setup (Recommended)

After installation, run the setup command to ensure everything is ready:

```bash
ai-completion-setup
```

This will:
- ✅ Check if Ollama is installed and running
- ✅ Verify the fine-tuned model exists
- ✅ Generate training data if needed
- ✅ Train the LoRA model if missing

## 🔄 What Happens on Terminal Startup

Every time you open a terminal, the plugin automatically:

1. **Checks if Ollama is running** → Starts it in background if not
2. **Verifies fine-tuned model** → Shows status message
3. **Everything is ready** → You can use AI completions immediately

You'll see:
- `✅ AI Autocomplete ready (LoRA model: zsh-assistant)` - Everything perfect!
- `⚠️  AI Autocomplete ready (fine-tuned model not found - run 'ai-completion-setup')` - Need to set up model
- `⚠️  AI Autocomplete ready (Ollama not available - will use training data fallback)` - Using fallback mode

## ✅ Verification

Test that everything works:

```bash
# Check status
ai-completion-status

# Test completions
ai-completion-test

# Try it out
git comm[Tab]  # Should complete to: git commit -m "..."
```

## 🎯 Configuration

### Custom Configuration File

Create `~/.config/model-completer/config.yaml`:

```yaml
ollama:
  url: "http://localhost:11434"
  timeout: 60

model: "zsh-assistant"  # Use fine-tuned model

cache:
  enabled: true
  ttl: 3600

logging:
  level: "INFO"
  file: "~/.cache/model-completer/logs.txt"
```

### Environment Variables

You can override paths with:

```bash
export MODEL_COMPLETION_PYTHON="/path/to/python"
export MODEL_COMPLETION_SCRIPT="/path/to/cli.py"
export MODEL_COMPLETION_CONFIG="/path/to/config.yaml"
```

## 🔧 Troubleshooting

### Ollama Not Starting Automatically

If Ollama doesn't start on terminal open:

1. Check if `ollama` command exists: `which ollama`
2. Manually start: `ollama serve`
3. Make it a service (Linux):
   ```bash
   systemctl --user enable ollama
   systemctl --user start ollama
   ```

### Model Not Found

If you see "fine-tuned model not found":

```bash
# Run setup
ai-completion-setup

# Or manually
python -m model_completer.cli --generate-data
python -m model_completer.cli --train
```

### Plugin Not Loading

Check if plugin is sourced in `~/.zshrc`:

```bash
grep "zsh_autocomplete" ~/.zshrc
```

If not found, add:
```bash
source /path/to/model-cli-autocomplete/src/scripts/zsh_autocomplete.plugin.zsh
```

### Python Path Issues

If you see Python errors:

1. Ensure virtual environment is activated
2. Check `MODEL_COMPLETION_PYTHON` environment variable
3. Try: `export MODEL_COMPLETION_PYTHON="$(which python3)"`

## 📦 System-Wide Installation (Optional)

For system-wide installation:

```bash
sudo mkdir -p /opt/model-cli-autocomplete
sudo cp -r . /opt/model-cli-autocomplete/
sudo chown -R $USER:$USER /opt/model-cli-autocomplete

# Update plugin path
export MODEL_COMPLETION_PROJECT_DIR="/opt/model-cli-autocomplete"
```

## 🚀 Quick Start After Installation

Once installed, you can immediately start using:

```bash
# Simple completion
git comm[Tab]           # → git commit -m "smart message"

# Multiple suggestions
docker run[Shift+Tab]  # → Multiple options

# With confidence
npm run[Ctrl+Tab]      # → With confidence score

# Smart commit message
git comm[Tab]          # → Analyzes changes and suggests commit message
```

## 💡 Tips

1. **First time setup**: Run `ai-completion-setup` to ensure everything is configured
2. **Check status**: Use `ai-completion-status` anytime to see system status
3. **Training data**: The system includes 278+ training examples for common commands
4. **History**: Your completions are saved to `~/.cache/model-completer/command_history.jsonl`
5. **Fallback**: If AI is unavailable, it falls back to training data automatically

## 🎉 You're Ready!

Your AI autocomplete with LoRA fine-tuning is now ready to use! Every terminal session will automatically:

- ✅ Start Ollama if needed
- ✅ Verify fine-tuned model
- ✅ Load enhanced features
- ✅ Enable smart completions

Just open a terminal and start typing! 🚀

