# Troubleshooting Tab Completion

If Tab completion is not working, follow these steps:

## Quick Fix

1. **Reload your shell:**
   ```bash
   source ~/.zshrc
   ```

2. **Test the completion manually:**
   ```bash
   python3 /Users/duoyun/Desktop/model-cli-autocomplete/src/model_completer/cli.py "git comm"
   ```
   This should output: `git commit -m "commit message"`

3. **Check if plugin is loaded:**
   ```bash
   echo $MODEL_COMPLETION_SCRIPT
   ```
   Should show: `/Users/duoyun/Desktop/model-cli-autocomplete/src/model_completer/cli.py`

## Common Issues

### Issue: "command not found" when pressing Tab
**Solution:** The Python path might be wrong. The plugin will auto-fallback to `python3`, but you can verify:
```bash
which python3
```

### Issue: Plugin not detecting project directory
**Solution:** Manually set it in `~/.zshrc` before the plugin source line:
```bash
export MODEL_COMPLETION_PROJECT_DIR="/Users/duoyun/Desktop/model-cli-autocomplete"
export MODEL_COMPLETION_PYTHON="${MODEL_COMPLETION_PROJECT_DIR}/venv/bin/python3"
```

### Issue: Ollama not running
**Solution:** Start Ollama:
```bash
ollama serve
```
Or let the plugin auto-start it (it will try in background).

### Issue: Model not found in Ollama
**Solution:** Import the fine-tuned model:
```bash
cd /Users/duoyun/Desktop/model-cli-autocomplete
source venv/bin/activate
model-completer --import-to-ollama
```

## Testing

Run the test script:
```bash
zsh /Users/duoyun/Desktop/model-cli-autocomplete/test_completion.zsh
```

## Manual Test in Terminal

1. Open a new terminal
2. Type: `git comm`
3. Press Tab
4. Should complete to: `git commit -m "commit message"`

## Debug Mode

Add this to your `~/.zshrc` before the plugin source:
```bash
export MODEL_COMPLETION_DEBUG=1
```

This will show more detailed error messages.

