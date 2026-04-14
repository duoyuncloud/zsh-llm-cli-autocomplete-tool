# Zsh LLM CLI Autocomplete Plugin

Inline command completion for Zsh:

- grey ghost text suggestions while you type
- press `Tab` to accept
- local inference with a base model + LoRA adapter

This project ships a ready-to-use runtime and also includes training utilities for custom adapters.

## Demo

**[Watch the trailer](https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool/blob/main/docs/demo/Trailer.mov)** — opens on GitHub with the built-in player (README inline `<video>` is unreliable for `.mov`).

[Download `Trailer.mov` (raw file)](https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool/raw/main/docs/demo/Trailer.mov) · [Try the demo in your browser](docs/demo/trailer-stage.html) — same flow as the trailer; press **Space** to advance, **←** to go back.

## What This Plugin Does

- Inline shell command completion in Zsh (`POSTDISPLAY` + `region_highlight`)
- Smart commit message completion from staged diff context
- History-aware suggestions (prefix matching + workflow-aware tie-breaker)
- Safety filtering for risky `git push` force flags unless explicitly typed
- Unix-socket daemon for low-latency completion (`~/.cache/zsh-autocomplete.sock`)

All runtime inference is local on your machine.

## Quick Start

```bash
git clone https://github.com/duoyuncloud/zsh-llm-cli-autocomplete-tool.git
cd zsh-llm-cli-autocomplete-tool
./install.sh
source ~/.zshrc
```

Then type in your shell and press `Tab`, for example:

- `git ad` → `git add ...`
- `git co` → smart commit suggestion
- `npm r` → history/model-aware completion

## What `install.sh` Does

1. Creates/uses `venv`
2. Installs runtime dependencies
3. Downloads pre-trained LoRA adapter from Hugging Face (`duoyuncloud/zsh-autocomplete-lora`)
4. Reads adapter metadata to detect the correct base model
5. Merges base + adapter into a local merged model cache
6. Adds plugin source lines into `~/.zshrc`
7. Starts daemon: `python -m model_completer.daemon`

`install.sh` edits your shell config. If you want completions off without uninstalling, use `ai-disable` (see below).

## Runtime Architecture

- Zsh plugin: `src/scripts/zsh_autocomplete.plugin.zsh`
- Daemon entrypoint: `python -m model_completer.daemon`
- Core daemon logic: `src/model_completer/autocomplete_daemon.py`
- Socket transport: Unix domain socket JSON RPC

The plugin gathers lightweight context (`cwd`, git info, scripts/targets, recent commands) and sends it to the daemon for completion.

## User Commands

After sourcing the plugin:

- `ai-setup` — install/download/start helpers
- `ai-status` — show daemon/model/enabled state
- `ai-enable` / `ai-disable` — turn completions on or off (no need to comment out `~/.zshrc` lines)
- `ai-restart` — restart daemon
- `ai-debug` — quick diagnostics

## Smart Commit Behavior

Commit intent is detected early (for partial prefixes like `git c`, `git co`, `git com`).

When commit intent is detected:

- plugin sends staged diff + recent commit log style
- daemon returns a structured commit command
- output format: `git commit -m "type: subject"`

## History + Workflow Adaptation

This repo uses both:

- direct history prefix reuse (fast-path)
- workflow-aware tie-breaker for ambiguous prefixes (example: after `git commit`, short ambiguous `git ...` inputs can prefer `git push` when transition confidence is strong)

This keeps strong personalized prefix matching while reducing repetitive wrong-next-command loops.

## Troubleshooting

- Daemon log: `~/.cache/zsh-autocomplete.log`
- Socket path: `~/.cache/zsh-autocomplete.sock`
- PID file: `~/.cache/zsh-autocomplete.pid`

If completions do not appear:

```bash
ai-status
ai-debug
ai-restart
```

## Training (Maintainers / Advanced Users)

Training-related files are intentionally kept in this repository:

- `src/training/*`
- `requirements-training.txt`
- `run_training.sh`
- `upload_to_huggingface.sh`

Typical flow (advanced):

```bash
pip install -r requirements-training.txt
./run_training.sh
./upload_to_huggingface.sh
```

You can override base/repo through environment variables in scripts:

- `BASE_MODEL_ID=...`
- `HF_REPO_ID=...`
- `ADAPTER_DIR=...`

## Project Layout

- `src/scripts/` — Zsh plugin
- `src/model_completer/` — daemon/runtime/CLI
- `src/training/` — training and adapter utilities
- `docs/` — usage and behavior docs
- `config/default.yaml` — default config values

## License

MIT. See `LICENSE`.
