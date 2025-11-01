# Smart Commit Message Feature

## 🎯 Overview

The Enhanced LoRA model now includes **smart commit message generation** that analyzes your git changes and suggests descriptive, conventional commit messages automatically.

## ✨ Features

### 1. **Automatic Change Analysis**
- Detects files added, modified, or deleted
- Counts lines added/removed
- Understands file types and project structure

### 2. **AI-Powered Commit Messages**
- Generates commit messages following [Conventional Commits](https://www.conventionalcommits.org/) format
- Context-aware based on your changes
- Uses LoRA fine-tuned model for quality suggestions

### 3. **Seamless Integration**
- Automatically triggers when you type `git comm` or `git commit`
- Integrates with command completion
- Works with both staged and unstaged changes

## 📝 Usage

### Method 1: Automatic (via completion)
```bash
# Just type git commit and get smart message suggestion
git comm[Tab]
# → git commit -m "feat: add user authentication module"
```

### Method 2: Direct command
```bash
# Generate commit message directly
model-completer --commit-message
# Output:
# 📝 Smart commit message: feat: add smart commit message feature
# 
# Use it with:
#   git commit -m "feat: add smart commit message feature"
```

### Method 3: Python API
```python
from model_completer.enhanced_completer import EnhancedCompleter

completer = EnhancedCompleter(model='zsh-assistant')
commit_msg = completer.get_smart_commit_message()
print(commit_msg)
```

## 🔍 How It Works

1. **Analyzes Git Changes**
   - Checks `git status` for file changes
   - Analyzes `git diff` for line changes
   - Detects project type and context

2. **Generates Context**
   - File types affected (.py, .js, .yaml, etc.)
   - Project structure (Python, Node.js, etc.)
   - Change summary (added/modified/deleted)

3. **AI Generation**
   - Uses LoRA fine-tuned model
   - Follows conventional commits format
   - Provides descriptive, concise messages

## 📋 Commit Message Format

The system generates messages in Conventional Commits format:

```
<type>(<scope>): <subject>

Types:
- feat: New feature
- fix: Bug fix
- refactor: Code refactoring
- docs: Documentation changes
- test: Test additions/changes
- chore: Maintenance tasks
```

### Examples:

```bash
# Added new feature
feat: add smart commit message generation

# Fixed bug
fix: resolve memory leak in parser

# Refactored code
refactor: simplify error handling

# Updated docs
docs: update API documentation
```

## 🆚 Comparison with Manual Messages

| Scenario | Manual | Smart Commit |
|----------|--------|--------------|
| **Time** | 30-60 seconds | Instant |
| **Format** | Inconsistent | Conventional Commits |
| **Quality** | Varies | Consistent, descriptive |
| **Context** | Limited | Full project context |

## 🎯 Benefits

1. **Saves Time**: No need to think about commit messages
2. **Consistent Format**: Follows industry standards
3. **Better Messages**: AI understands context and generates descriptive messages
4. **Project-Aware**: Considers your project structure and file types
5. **Learning**: Gets smarter over time with your patterns

## 💡 Tips

- **Stage your changes first** for best results:
  ```bash
  git add .
  git comm[Tab]  # Get smart message
  ```

- **Works with unstaged changes too** - analyzes current working directory

- **Customize**: The AI considers your project type and recent changes

## 🔧 Technical Details

- Analyzes both staged (`git diff --cached`) and unstaged (`git diff`) changes
- Uses LoRA fine-tuned model for natural language generation
- Falls back to descriptive summaries if AI unavailable
- Saves commit history for pattern learning

## 📊 Example Output

```bash
$ model-completer --commit-message

📊 Analyzing Git Changes:
Files changed: 5
  Modified: 4 - ['src/completer.py', 'src/cli.py', ...]
  Added: 1 - ['SMART_COMMIT.md']
Lines: +245 / -89

📝 Smart commit message: feat: add smart commit message generation feature

Use it with:
  git commit -m "feat: add smart commit message generation feature"
```

## 🚀 Future Enhancements

- Multi-line commit messages with detailed descriptions
- Branch-specific message styles
- Team commit message patterns
- Integration with git hooks
- Commit message templates per project

