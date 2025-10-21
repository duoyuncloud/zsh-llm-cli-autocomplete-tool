# Model CLI Autocomplete - Architecture Documentation

## 🏗️ System Overview

The Model CLI Autocomplete system is a modular, AI-powered command completion tool that integrates with Zsh to provide intelligent command suggestions using local LLMs via Ollama.

## 📁 Directory Structure

```
model-cli-autocomplete/
├── 📁 config/                    # Configuration management
│   └── default.yaml             # Default application settings
├── 📁 docs/                     # Documentation
│   └── architecture.md          # This file
├── 📁 src/                      # Source code
│   ├── 📁 model_completer/      # Core Python package (9 modules)
│   │   ├── __init__.py          # Package initialization & API
│   │   ├── cli.py               # Command-line interface
│   │   ├── completer.py          # AI completion logic
│   │   ├── client.py             # Ollama API communication
│   │   ├── ollama_manager.py     # Ollama server management
│   │   ├── ui.py                 # Interactive user interface
│   │   ├── training.py           # LoRA fine-tuning pipeline
│   │   ├── utils.py              # Utility functions
│   │   └── cache.py              # Caching system
│   ├── 📁 scripts/              # Shell integration
│   │   └── zsh_autocomplete.plugin.zsh  # Zsh plugin
│   └── 📁 training/             # Training pipeline (6 files)
│       ├── prepare_zsh_data.py  # Training data generation
│       ├── convert_to_axolotl_format.py  # Data format conversion
│       ├── axolotl_trainer.py   # LoRA training execution
│       ├── test_adapter.py       # Model validation
│       ├── train.sh             # Training orchestration
│       └── zsh_training_data.jsonl  # Training dataset
├── 📁 tests/                    # Testing
│   └── test_client.py           # Unit tests
├── install.sh                   # One-click installation
├── setup.py                     # Python package setup
├── pyproject.toml              # Modern packaging config
├── requirements.txt             # Core dependencies
├── requirements-training.txt    # Training dependencies
├── README.md                    # User documentation
└── .gitignore                   # Git ignore rules
```

## 🔧 Core Components

### 1. **Command-Line Interface (`cli.py`)**
- **Purpose**: Main entry point and argument processing
- **Responsibilities**:
  - Parse command-line arguments
  - Orchestrate different operations (completion, training, data generation)
  - Integrate with all other modules
- **Key Functions**:
  - `get_ai_completion()` - Single completion request
  - `get_suggestions()` - Multiple completion suggestions
  - `get_advanced_completion()` - UI-based completion with confidence scores

### 2. **AI Completion Engine (`completer.py`)**
- **Purpose**: Core intelligence for command completion
- **Responsibilities**:
  - Build context-aware prompts
  - Integrate environmental context (Git status, directory, history)
  - Manage command history and patterns
- **Key Features**:
  - Context-aware prompt building
  - Command history tracking
  - Git integration for repository-aware completions
  - Multiple suggestion generation

### 3. **Ollama Communication (`client.py` vs `ollama_manager.py`)**

#### **`client.py` - API Communication Layer**
- **Purpose**: Direct communication with Ollama API
- **Responsibilities**:
  - Send completion requests to Ollama
  - Handle API responses and errors
  - Manage caching for performance
- **Key Functions**:
  - `generate_completion()` - Send prompts to Ollama
  - `get_available_models()` - List installed models
  - `is_server_available()` - Check API connectivity
- **Scope**: **Runtime operations** - Used during active completion

#### **`ollama_manager.py` - Server Management Layer**
- **Purpose**: Ollama server lifecycle and model management
- **Responsibilities**:
  - Install Ollama if not present
  - Start/stop Ollama server
  - Download and manage models
  - Monitor server status
- **Key Functions**:
  - `install()` - Install Ollama
  - `start_server()` / `stop_server()` - Server lifecycle
  - `pull_model()` - Download models
  - `is_running()` - Check server status
- **Scope**: **Administrative operations** - Used during setup and maintenance

#### **Key Differences**:
| Aspect | `client.py` | `ollama_manager.py` |
|--------|-------------|-------------------|
| **Purpose** | API communication | Server management |
| **Usage** | Runtime completions | Setup & maintenance |
| **Scope** | Individual requests | Server lifecycle |
| **Dependencies** | `requests`, `cache` | `subprocess`, `requests` |
| **Error Handling** | API errors | Installation/system errors |

### 4. **User Interface (`ui.py`)**
- **Purpose**: Interactive completion interface
- **Responsibilities**:
  - Provide navigatable completion suggestions
  - Display confidence scores
  - Handle keyboard navigation
- **Key Features**:
  - Multiple completion modes
  - Confidence-based ranking
  - Keyboard navigation support
  - Fallback for missing dependencies

### 5. **Training Pipeline (`training.py`)**
- **Purpose**: LoRA fine-tuning for specialized completions
- **Responsibilities**:
  - Manage training data preparation
  - Configure Axolotl training
  - Handle model adaptation
- **Key Features**:
  - Zsh-specific training data
  - LoRA parameter optimization
  - Training monitoring and validation

### 6. **Supporting Modules**

#### **`utils.py` - Utility Functions**
- Configuration loading
- Logging setup
- Common helper functions

#### **`cache.py` - Caching System**
- TTL-based completion caching
- Performance optimization
- Memory management

## 🔄 Data Flow Architecture

### **Installation Flow**
```mermaid
graph TD
    A[install.sh] --> B[ollama_manager.py]
    B --> C[Install Ollama]
    B --> D[Start Server]
    B --> E[Download Models]
    A --> F[training.py]
    F --> G[Setup Training Environment]
    A --> H[zsh_autocomplete.plugin.zsh]
    H --> I[Configure Zsh Integration]
```

### **Runtime Completion Flow**
```mermaid
graph TD
    A[User Types Command] --> B[Zsh Plugin]
    B --> C[cli.py]
    C --> D[completer.py]
    D --> E[Build Context-Aware Prompt]
    E --> F[client.py]
    F --> G[Ollama API Request]
    G --> H[ui.py]
    H --> I[Display Suggestions]
    I --> J[cache.py]
    J --> K[Store Result]
```

### **Training Flow**
```mermaid
graph TD
    A[prepare_zsh_data.py] --> B[Generate Training Data]
    B --> C[convert_to_axolotl_format.py]
    C --> D[Format for Axolotl]
    D --> E[axolotl_trainer.py]
    E --> F[Execute LoRA Training]
    F --> G[test_adapter.py]
    G --> H[Validate Model]
```

## 🎯 Design Principles

### **1. Modularity**
- **Single Responsibility**: Each module has one clear purpose
- **Loose Coupling**: Modules interact through well-defined interfaces
- **High Cohesion**: Related functionality grouped together

### **2. Real Functionality**
- **No Dummy Code**: All components provide actual functionality
- **Production Ready**: Error handling, logging, monitoring
- **Performance Optimized**: Caching, async operations where appropriate

### **3. User Experience**
- **One-Click Installation**: `install.sh` handles everything
- **Multiple Completion Modes**: Simple, UI, advanced
- **Rich Integration**: Seamless Zsh integration
- **Comprehensive Error Handling**: Clear error messages and recovery

### **4. Extensibility**
- **Plugin Architecture**: Easy to add new completion modes
- **Configurable**: YAML-based configuration
- **Model Agnostic**: Support for different LLMs
- **Training Pipeline**: Easy to add new training data sources

## 🔧 Integration Points

### **Zsh Integration**
- **Plugin File**: `src/scripts/zsh_autocomplete.plugin.zsh`
- **Completion Modes**: Simple, UI, Advanced
- **Utility Commands**: Status, test, train, help
- **Key Bindings**: Tab, Shift+Tab, Ctrl+Tab

### **Ollama Integration**
- **Server Management**: `ollama_manager.py` handles lifecycle
- **API Communication**: `client.py` handles requests
- **Model Support**: CodeLlama, Llama2, custom fine-tuned models
- **Caching**: Performance optimization for repeated requests

### **Training Integration**
- **Data Sources**: Git history, command patterns, system commands
- **Format Support**: JSONL for Axolotl compatibility
- **Model Types**: LoRA adapters for efficient fine-tuning
- **Validation**: Automated testing of trained models

## 📊 Performance Characteristics

### **Response Times**
- **Cached Completions**: < 50ms
- **API Requests**: 200-500ms (depending on model size)
- **Training**: 30-60 minutes (depending on hardware)

### **Resource Usage**
- **Memory**: 2-8GB (depending on model size)
- **CPU**: Moderate during completion, high during training
- **Storage**: 1-10GB (depending on models and training data)

### **Scalability**
- **Concurrent Users**: Limited by Ollama server capacity
- **Model Switching**: Fast model loading and switching
- **Cache Efficiency**: TTL-based cache with configurable expiration

## 🛠️ Development Workflow

### **Adding New Features**
1. **Core Logic**: Add to appropriate module in `src/model_completer/`
2. **CLI Integration**: Update `cli.py` for new commands
3. **Zsh Integration**: Update plugin for new functionality
4. **Testing**: Add tests in `tests/`
5. **Documentation**: Update README and architecture docs

### **Training New Models**
1. **Data Preparation**: Use `prepare_zsh_data.py` or add custom data
2. **Format Conversion**: Use `convert_to_axolotl_format.py`
3. **Training**: Use `axolotl_trainer.py` with appropriate config
4. **Validation**: Use `test_adapter.py` to verify model quality
5. **Integration**: Update model configuration in `config/default.yaml`

This architecture provides a **robust, scalable, and maintainable** foundation for AI-powered command completion with real functionality and excellent user experience! 🚀
