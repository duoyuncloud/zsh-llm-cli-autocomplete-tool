#🚀 Zsh LLM CLI Autocomplete Tool

> AI-powered Zsh plugin for intelligent command line completion using local LLMs

![Zsh](https://img.shields.io/badge/Shell-Zsh-blue)
![AI](https://img.shields.io/badge/AI-Ollama-green)
![Python](https://img.shields.io/badge/Python-3.8%2B-yellow)

## ✨ Features

- **🤖 AI Command Completion**: Get smart command suggestions as you type
- **⚡ Real-time Processing**: Local LLM inference with Ollama
- **🎯 Zsh Optimized**: Built specifically for Zsh workflows
- **⌨️ Tab Integration**: Use familiar Tab key for completions
- **🔧 One-Click Setup**: Run `./install.sh` and you're ready
- **💾 100% Local**: No data leaves your machine

## 🚀 Quick Start

```bash
# 1. Clone and install
git clone https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool.git
cd zsh-llm-cli-autocomplete-tool
./install.sh

# 2. Reload your shell
source ~/.zshrc

# 3. Start using AI completions!
git comm[Tab]        # → git commit -m "message"
docker run[Tab]      # → docker run -it --name container
npm run[Tab]         # → npm run dev
python -m[Tab]       # → python -m http.server 8000
```
## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool.git
cd zsh-llm-cli-autocomplete-tool

# Run the one-click installer
./install.sh
```
This script automatically:

Sets up Ollama and downloads models

Installs Python dependencies

Configures Zsh plugin

Ready to use immediately

## 🔧 Usage
Just use Tab key as normal - AI completions will appear automatically.
**Utility Commands**
```bash
zsh-llm-autocomplete-test     # Test the system
zsh-llm-autocomplete-status   # Check status
zsh-llm-autocomplete-help     # Show help
```

## 🏗️ How It Works
Your Zsh Terminal → AI Plugin → Ollama Server → Smart Completions

Zsh Plugin: Intercepts Tab key and shows AI suggestions

Python Backend: Communicates with Ollama server

Ollama: Runs local LLMs for command completion

Fine-tuned Models: Optimized for CLI command patterns

## 💡 About
This tool brings AI-powered command completion to your Zsh terminal using local LLMs. Everything runs on your machine for complete privacy.

Star this repo if you find it useful! ⭐