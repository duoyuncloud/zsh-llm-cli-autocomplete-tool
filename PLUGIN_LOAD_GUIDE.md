# Zsh Plugin Loading Guide

## 📦 How to Load the Plugin

### Method 1: Direct source (Recommended)

Add this to your `~/.zshrc` file:

```bash
# Load AI Autocomplete plugin
source /path/to/zsh-llm-cli-autocomplete-tool/src/scripts/zsh_autocomplete.plugin.zsh
```

Replace `/path/to/zsh-llm-cli-autocomplete-tool` with your actual project path.

### Method 2: Using Oh My Zsh

If you're using Oh My Zsh:

```bash
# 1. Copy plugin to Oh My Zsh directory
mkdir -p ~/.oh-my-zsh/custom/plugins/zsh-autocomplete
cp /path/to/zsh-llm-cli-autocomplete-tool/src/scripts/zsh_autocomplete.plugin.zsh \
   ~/.oh-my-zsh/custom/plugins/zsh-autocomplete/

# 2. Add plugin to ~/.zshrc
plugins=(... zsh-autocomplete)
```

### Method 3: Using Custom Plugin Directory

```bash
# 1. Create plugin directory
mkdir -p ~/.zsh-plugins/zsh-autocomplete

# 2. Copy plugin file
cp /path/to/zsh-llm-cli-autocomplete-tool/src/scripts/zsh_autocomplete.plugin.zsh \
   ~/.zsh-plugins/zsh-autocomplete/

# 3. Add to ~/.zshrc
source ~/.zsh-plugins/zsh-autocomplete/zsh_autocomplete.plugin.zsh
```

## 🚀 Auto-Start Features

When the plugin loads, it **automatically**:

1. ✅ **Starts Ollama Server** (if not running)
2. ✅ **Loads the fine-tuned model** (zsh-assistant)
3. ✅ **Runs silently in background** (doesn't block prompt)

**Important**: All startup operations run asynchronously in the background and **will NOT block** your terminal prompt!

## 🔍 Verify Plugin is Loaded

After opening a new terminal, run:

```bash
# Check if plugin is loaded
ai-completion-status

# Or test it
ai-completion-test
```

## ⚙️ Environment Variables (Optional)

If you need to customize paths, you can set:

```bash
# Set in ~/.zshrc (before plugin loads)
export MODEL_COMPLETION_PROJECT_DIR="/path/to/zsh-llm-cli-autocomplete-tool"
export MODEL_COMPLETION_PYTHON="/path/to/python3"
```

## 💡 Usage Tips

After loading the plugin:

1. **Prompt shows immediately** - No need to press Enter, you can start typing commands right away
2. **Background auto-preparation** - Ollama and model load in the background
3. **Check status** - Run `ai-completion-status` to verify everything is ready

## 🐛 Troubleshooting

If the prompt is blocked:

1. Check if the plugin path is correct
2. Check for syntax errors: `zsh -n ~/.zshrc`
3. Try manual start: `ollama serve &`

