# Zsh AI CLI Autocomplete Tool

AI-powered Zsh plugin with LoRA fine-tuning and personalized command predictions. Uses local LLMs via Ollama to provide intelligent command completions that learn from your workflow.

## Features

- AI Command Completion: Smart command predictions using LoRA fine-tuned models
- Personalized Predictions: Remembers your CLI history and learns your workflow patterns
- Grey Preview: See predicted command completion in grey before accepting
- Real-time Processing: Local LLM inference with Ollama
- LoRA Fine-tuning: Train custom models for your specific workflow
- 100% Local: No data leaves your machine

## Quick Start

```bash
# Clone and install
git clone https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool.git
cd zsh-llm-cli-autocomplete-tool
./install.sh

# Reload shell (plugin is automatically added to ~/.zshrc)
source ~/.zshrc

# Start using AI completions
# Type a command and press Tab to see grey preview, then Tab again to accept
git comm[Tab]     # Shows grey preview, press Tab again to complete
docker run[Tab]   # Personalized completion based on your history
npm run[Tab]      # Smart predictions based on workflow
```

The plugin automatically starts Ollama server (if not running) and loads the fine-tuned model (zsh-assistant).

## Installation

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

# Install training dependencies (optional, for LoRA training)
pip install -r requirements-training.txt

# Setup Ollama and models
python -m model_completer.cli --generate-data
python -m model_completer.cli --train
python -m model_completer.cli --import-to-ollama
```

## Usage

### Tab Completion

Simply type a command and press Tab:
- First Tab: Shows grey preview of predicted completion
- Second Tab (or Enter): Accepts the completion

The system learns from your command history and provides personalized predictions based on:
- Your previous commands
- Current project context (Git status, project type)
- Command sequence patterns
- Workflow patterns

### Utility Commands

```bash
ai-completion-status    # Check system status
ai-completion-setup     # Setup Ollama and models
ai-completion-train     # Start LoRA training
ai-completion-data      # Generate training data
```

## LoRA Fine-tuning

### Training Your Own Model

```bash
# Generate training data
python -m model_completer.cli --generate-data

# Start LoRA training
python -m model_completer.cli --train

# Import to Ollama
python -m model_completer.cli --import-to-ollama
```

The training pipeline:
1. Generates comprehensive training data from common CLI patterns
2. Fine-tunes a base model using LoRA (Low-Rank Adaptation)
3. Imports the trained model to Ollama for serving

## Architecture

```
Zsh Plugin -> Python Backend -> Ollama Server
                |                    |
                |                    |
         EnhancedCompleter      LoRA Models
         History tracking       Model serving
         Personalization        API endpoints
```

### Core Components

- EnhancedCompleter: Main completion logic with personalization and history tracking
- OllamaClient: Ollama API communication with caching
- OllamaManager: Server and model management
- TrainingDataManager: Training data preparation
- LoRATrainer: LoRA fine-tuning with transformers/PEFT or Axolotl

## Configuration

Configuration file location: `~/.config/model-completer/config.yaml`

```yaml
ollama:
  url: "http://localhost:11434"
  timeout: 10

model: "zsh-assistant"

cache:
  enabled: true
  ttl: 3600

logging:
  level: "INFO"
  file: "~/.cache/model-completer/logs.txt"
```

## Personalization

The system automatically:
- Tracks your command history in `~/.cache/model-completer/command_history.jsonl`
- Learns your patterns from frequently used commands
- Adapts to your workflow based on command sequences
- Considers project context (Git status, project type, recent files)

## Advanced Features

### Context-Aware Completions

- Git repository status
- Current directory context
- Command history patterns
- Project type detection

### Training Pipeline

- Automatic data generation
- LoRA fine-tuning (transformers/PEFT or Axolotl)
- Model validation
- Ollama integration

## Troubleshooting

### Common Issues

1. Ollama not running: `ollama serve`
2. No models: `ai-completion-setup`
3. Plugin not loaded: Check `~/.zshrc`
4. Training fails: Install training dependencies

### Debug Commands

```bash
# Check system status
ai-completion-status

# Test completions
python -m model_completer.cli --test

# List available models
python -m model_completer.cli --list-models

# Check logs
tail -f ~/.cache/model-completer/logs.txt
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Ollama](https://ollama.ai/) for local LLM serving
- [Axolotl](https://github.com/OpenAccess-AI-Collaborative/axolotl) for LoRA training
- [PEFT](https://github.com/huggingface/peft) for efficient fine-tuning
