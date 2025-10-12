# Model CLI Autocomplete

A intelligent command-line autocompletion tool powered by local LLMs through Ollama.

## Features

- 🤖 AI-powered command completion using local LLMs
- ⚡ Fast and responsive with caching
- 🔧 Configurable through YAML files
- 🐚 Zsh plugin integration
- 💾 Context-aware suggestions (Git, directory, history)

## Installation

1. Install Ollama and pull a model:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull llama2

## Keyboard Navigation

The enhanced UI provides full keyboard navigation:

- **Tab**: First press activates AI completion, subsequent presses cycle through suggestions
- **↑/↓ Arrow Keys**: Navigate through the suggestion list
- **Enter**: Accept the currently selected suggestion
- **Escape**: Cancel the UI and return to original input
- **Any other key**: Cancel UI and continue normal editing

## UI Features

- **Visual highlighting** of the selected suggestion
- **Multi-suggestion display** (3-5 suggestions depending on context)
- **Auto-dismissal** when continuing to type
- **Context-aware** suggestions based on current directory, Git status, and command history

## Configuration

Enable/disable the UI feature:
```zsh
# Disable UI (fall back to simple tab completion)
model-completion-toggle-ui

# Enable UI (default)
model-completion-toggle-ui