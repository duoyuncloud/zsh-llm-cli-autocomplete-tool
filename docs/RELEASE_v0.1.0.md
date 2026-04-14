**Zsh LLM CLI Autocomplete Plugin** brings local, LLM-powered inline command completion to Zsh: grey ghost suggestions as you type, **Tab** to accept, plus smart commit hints and history-aware behaviour. A Python daemon serves completions over a Unix socket; inference uses a **base model + LoRA** merged on your machine.

Install: clone the repo, run `./install.sh`, then `source ~/.zshrc`. Use `ai-status`, `ai-enable`, and `ai-disable` to control the plugin.

See the [README](https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool/blob/main/README.md) for full documentation.
