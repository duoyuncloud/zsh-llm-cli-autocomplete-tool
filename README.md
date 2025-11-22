# Zsh AI CLI Autocomplete Tool

AI-powered Zsh plugin with LoRA fine-tuning and personalized command predictions. Uses local LLMs via Ollama to provide intelligent command completions that learn from your workflow.

## Features

- AI Command Completion: Smart command predictions using LoRA fine-tuned models
- Smart Commit Messages: Automatically generates specific commit messages from git diff analysis
- Personalized Predictions: Remembers your CLI history and learns your workflow patterns
- Grey Preview: See predicted command completion in grey before accepting
- Real-time Processing: Local LLM inference with Ollama
- LoRA Fine-tuning: Train custom models for your specific workflow
- 100% Local: No data leaves your machine

## Quick Start

**Just 2 steps to get started:**

```bash
# 1. Clone and install (automatically downloads pre-trained model)
git clone https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool.git
cd zsh-llm-cli-autocomplete-tool
./install.sh

# 2. Reload shell and start using!
source ~/.zshrc

# That's it! Now try:
git comm[Tab]     # Smart commit: generates commit message from git diff
docker run[Tab]   # Personalized completion based on your history
npm run[Tab]      # Smart predictions based on workflow
```

The installation script automatically:
- Installs all dependencies
- Sets up Ollama server
- Downloads the pre-trained LoRA adapter from Hugging Face
- Downloads the base model (Qwen3-1.7B)
- Merges the adapter with the base model
- Imports everything to Ollama as `zsh-assistant`
- Configures the Zsh plugin

**No additional setup needed!** Just install and reload your shell.

**Note**: The first installation may take 5-15 minutes depending on your internet speed (downloading models). Subsequent terminal sessions will use the cached model.

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

### Smart Commit Messages

When you type `git comm` and press Tab, the system automatically:
- Analyzes your git diff (staged or unstaged changes)
- Extracts functionality from code changes (functions, classes, operations)
- Generates a specific, descriptive commit message
- Rejects generic placeholders like "commit message"

**Example:**
```bash
# After making code changes
git comm[Tab]
# Generates: git commit -m "feat: improve error handling in completion pipeline"
```

The smart commit feature:
- Analyzes actual code changes, not just file names
- Focuses on functionality rather than generic descriptions
- Uses conventional commit format (feat/fix/refactor/etc.)
- Works with both staged and unstaged changes

### Utility Commands

```bash
ai-completion-status    # Check system status
ai-completion-setup     # One-time setup: downloads pre-trained model from Hugging Face
ai-completion-train     # Re-train LoRA model (if you want to train your own)
ai-completion-data      # Generate training data
```

**Important**: The pre-trained model is automatically downloaded and set up during `./install.sh`. You don't need to run `ai-completion-setup` manually unless you want to re-download the model or use a different one.

The pre-trained model repository is configured in `config/default.yaml` via the `hf_lora_repo` setting. If you want to use a different model or train your own, see the [LoRA Fine-tuning](#lora-fine-tuning) section.

## LoRA Fine-tuning

### Base Model

This project uses **LoRA (Low-Rank Adaptation)** to fine-tune a base model for CLI command completion.

**Base Model:** [Qwen/Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B)
- **Model Card:** https://huggingface.co/Qwen/Qwen3-1.7B
- **Size:** 1.7B parameters
- **Quantization:** 4-bit (NF4) for memory efficiency
- **License:** Check the model card for license information

The base model is automatically downloaded from Hugging Face during the first training run. The model will be cached locally for subsequent use.

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
1. **Generates training data** (277 samples) from common CLI command patterns (Git, Docker, NPM, Python, etc.)
2. **Fine-tunes the base model** using LoRA (Low-Rank Adaptation) with 4-bit quantization
   - Training data: `src/training/zsh_training_data.jsonl`
   - LoRA parameters: r=16, alpha=32, dropout=0.05
   - Training epochs: 3
   - Estimated time: 20-40 minutes (Apple Silicon) or 10-20 minutes (NVIDIA GPU)
3. **Imports the trained model** to Ollama as `zsh-assistant` for serving

### Training Data

The training data consists of 277 command completion pairs covering:
- Git commands (status, add, commit, push, pull, etc.)
- Docker commands (run, build, ps, exec, etc.)
- NPM/Node commands (install, run, start, etc.)
- Python commands (-m, -c, pip, etc.)
- Kubernetes commands (get, apply, delete, etc.)
- System commands (ls, cd, mkdir, etc.)

Training data is generated by `src/training/prepare_zsh_data.py` and saved to `src/training/zsh_training_data.jsonl`.

### Using Pre-trained Model

The project includes a pre-trained LoRA adapter available on Hugging Face. To use it:

1. **Automatic Setup** (Recommended):
   ```bash
   ai-completion-setup
   ```
   This will automatically download the adapter from Hugging Face and set it up in Ollama.

2. **Manual Configuration**:
   Edit `~/.config/model-completer/config.yaml` (or `config/default.yaml`) and set:
   ```yaml
   hf_lora_repo: "your-username/zsh-assistant-lora"
   ```
   Then run:
   ```bash
   python -m model_completer.cli --import-to-ollama
   ```

The adapter will be downloaded to `zsh-lora-output/` and automatically merged with the base model when imported to Ollama.

### Training Your Own Model

If you want to train your own LoRA adapter instead of using the pre-trained one:

1. Set `hf_lora_repo: ""` in your config (or remove it)
2. Run the training pipeline:
   ```bash
   python -m model_completer.cli --generate-data
   python -m model_completer.cli --train
   python -m model_completer.cli --import-to-ollama
   ```

After training, the LoRA adapter is saved to `zsh-lora-output/`:
- `adapter_config.json` - LoRA configuration
- `adapter_model.safetensors` - Trained adapter weights

The fine-tuned model is then imported to Ollama and served as `zsh-assistant`.

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

### How Personalization Works

The system uses **two levels of personalization**:

1. **LoRA Model Training** (one-time): The model is trained on general CLI command patterns (not user-specific). This provides base intelligence for command completion.

2. **Runtime Personalization** (real-time): Your command history is saved locally and included in prompts to provide context-aware completions.

### Command History Storage

- **Location**: `~/.cache/model-completer/command_history.jsonl`
- **Format**: JSONL (one JSON object per line)
- **Content**: Each entry contains:
  - Timestamp
  - Original command
  - Completion that was used
  - Context (project type, git info, etc.)
  - Working directory
- **Retention**: Last 100 commands are kept

### How History is Used

Your command history is **NOT used to train the model**. Instead, it's:
- **Included in prompts** sent to the model for context
- Used to identify patterns (frequent commands, command sequences)
- Used to provide personalized suggestions based on your workflow

This means:
- ✅ Your history stays private (never leaves your machine)
- ✅ Personalization happens in real-time (no retraining needed)
- ✅ The model learns general patterns, your history provides context

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

### Smart Commit Message Generation

The smart commit feature analyzes your code changes and generates meaningful commit messages:

- **Diff Analysis**: Extracts functionality from git diff (functions, classes, method calls)
- **Context-Aware**: Considers project type, git status, and code structure
- **Specific Messages**: Generates descriptive messages like "feat: add context-aware command completion" instead of generic placeholders
- **Validation**: Rejects generic messages and ensures specificity
- **Conventional Commits**: Uses standard format (feat/fix/refactor/docs/test/chore)

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
