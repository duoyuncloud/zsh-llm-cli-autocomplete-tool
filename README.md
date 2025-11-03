# 🚀 Zsh AI CLI Autocomplete Tool

> Advanced AI-powered Zsh plugin with LoRA fine-tuning, navigatable UI, and Ollama integration

![Zsh](https://img.shields.io/badge/Shell-Zsh-blue)
![AI](https://img.shields.io/badge/AI-Ollama-green)
![Python](https://img.shields.io/badge/Python-3.8%2B-yellow)
![LoRA](https://img.shields.io/badge/LoRA-Fine--tuning-purple)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- **🤖 AI Command Completion**: Context-aware command suggestions using local LLMs
- **🎯 LoRA Fine-tuning**: Train custom models for your specific workflow
- **🖥️ Navigatable UI**: Multiple completion modes with confidence scores
- **⚡ Real-time Processing**: Local LLM inference with Ollama
- **🔧 Modular Design**: Clean, extensible architecture
- **💾 100% Local**: No data leaves your machine
- **🎨 Multiple Completion Modes**: Simple, UI, and advanced modes

## 🚀 Quick Start

```bash
# 1. Clone and install
git clone https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool.git
cd zsh-llm-cli-autocomplete-tool
./install.sh

# 2. Load plugin into ~/.zshrc
echo 'source '"$(pwd)"'/src/scripts/zsh_autocomplete.plugin.zsh' >> ~/.zshrc

# 3. Reload shell (or open new terminal)
source ~/.zshrc

# Plugin will automatically:
# ✅ Start Ollama Server (if not running)
# ✅ Load fine-tuned model (zsh-assistant)
# ✅ Prompt shows immediately, ready for command input

# 4. Start using AI completions!
git comm[Tab]        # → git commit -m "smart message"
docker run[Shift+Tab] # → Multiple suggestions
npm run[Ctrl+Tab]    # → With confidence score
```

### 📝 Manual Plugin Loading

If the install script didn't auto-configure, you can add manually:

```bash
# Add to end of ~/.zshrc file:
source /path/to/zsh-llm-cli-autocomplete-tool/src/scripts/zsh_autocomplete.plugin.zsh
```

Replace the path with your actual project path. The plugin will automatically start Ollama and load the model after loading, **without blocking the prompt**.

## 🛠️ Installation

### One-Click Installation
```bash
git clone https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool.git
cd zsh-llm-cli-autocomplete-tool
./install.sh
```

### Manual Installation
```bash
# Install Python dependencies
pip install -e .

# Install training dependencies (optional)
pip install -r requirements-training.txt

# Setup Ollama and models
python -m model_completer.cli --generate-data
python -m model_completer.cli --train
```

## 🔧 Usage

### Completion Modes
- **Tab**: Simple AI completion
- **Shift+Tab**: UI mode with multiple suggestions  
- **Ctrl+Tab**: Advanced mode with confidence scores

### Utility Commands
```bash
ai-completion-test      # Test the system
ai-completion-status    # Check status
ai-completion-help      # Show help
ai-completion-train     # Start LoRA training
ai-completion-data      # Generate training data
ai-completion-models    # List available models
ai-completion-setup     # Setup Ollama and models
```

### Python API
```python
from model_completer import ModelCompleter, create_ollama_manager

# Initialize completer
completer = ModelCompleter(model="zsh-assistant")
completion = completer.get_completion("git comm")

# Get multiple suggestions
suggestions = completer.get_suggestions("docker run", max_suggestions=3)

# Manage Ollama
manager = create_ollama_manager()
manager.setup_default_models()
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Zsh Plugin    │───▶│  Python Backend  │───▶│  Ollama Server  │
│                 │    │                  │    │                 │
│ • Tab completion│    │ • ModelCompleter │    │ • Local LLMs     │
│ • UI modes      │    │ • OllamaClient   │    │ • Model serving  │
│ • Key bindings  │    │ • Training       │    │ • API endpoints │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Core Modules
- **`ModelCompleter`**: Main completion logic with context awareness
- **`OllamaClient`**: Ollama API communication with caching
- **`OllamaManager`**: Server and model management
- **`TrainingDataManager`**: Training data preparation and validation
- **`LoRATrainer`**: LoRA fine-tuning with Axolotl
- **`CompletionUI`**: Navigatable UI components
- **`ZshCompletionUI`**: Zsh-specific completion interface

## 🎯 LoRA Fine-tuning

### Training Your Own Model
```bash
# Generate training data
python -m model_completer.cli --generate-data

# Start LoRA training
python -m model_completer.cli --train

# Test the trained model
python -m model_completer.cli --test
```

### Training Configuration
```python
from model_completer import TrainingConfig, create_trainer

config = TrainingConfig(
    base_model="codellama/CodeLlama-7b-hf",
    lora_r=16,
    lora_alpha=32,
    num_epochs=3,
    learning_rate=0.0002
)

trainer = create_trainer(config)
trainer.train("src/training/zsh_training_data.jsonl")
```

## 🔧 Configuration

### YAML Configuration
```yaml
# ~/.config/model-completer/config.yaml
ollama:
  url: "http://localhost:11434"
  timeout: 10

model: "zsh-assistant"
fallback_model: "codellama:7b"

cache:
  enabled: true
  ttl: 3600

ui:
  enabled: true
  max_suggestions: 5
  show_confidence: true

training:
  enabled: true
  data_path: "src/training/zsh_training_data.jsonl"
  output_path: "zsh-lora-output"
```

## 📊 Training Data

The system includes comprehensive training data for:
- **Git commands**: commit, push, pull, checkout, etc.
- **Docker commands**: run, build, exec, logs, etc.
- **NPM/Node.js**: install, run, test, etc.
- **Python**: modules, pip, virtual environments
- **Kubernetes**: kubectl commands
- **System commands**: ls, cd, mkdir, etc.
- **Zsh-specific**: autoload, compdef, bindkey, etc.

## 🚀 Advanced Features

### Context-Aware Completions
- Git repository status
- Current directory context
- Command history
- Environment variables

### Multiple UI Modes
- **Simple**: Direct completion
- **UI**: Multiple suggestions with navigation
- **Advanced**: Confidence scores and metadata

### Training Pipeline
- Automatic data generation
- Axolotl integration
- LoRA fine-tuning
- Model validation

## 🔧 Troubleshooting

### Common Issues
1. **Ollama not running**: `ollama serve`
2. **No models**: `ai-completion-setup`
3. **Plugin not loaded**: Check `~/.zshrc`
4. **Training fails**: Install training dependencies

### Debug Commands
```bash
# Check system status
ai-completion-status

# Test individual components
python -m model_completer.cli --test
python -m model_completer.cli --list-models

# Check logs
tail -f ~/.cache/model-completer/logs.txt
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) for local LLM serving
- [Axolotl](https://github.com/OpenAccess-AI-Collaborative/axolotl) for LoRA training
- [Prompt Toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) for UI components

---

**Star this repo if you find it useful! ⭐**