# How General Inline Autocomplete Works (Cursor / Copilot Style)

This doc summarizes how IDE-style inline completion (e.g. Cursor, GitHub Copilot, Zed) works and how this CLI autocomplete matches it.

## Cursor / Copilot behavior

1. **Ghost text**  
   The suggestion appears as grey (semi-transparent) text **inline** after the cursor. It’s a single completion, not a dropdown.

2. **Tab to accept, Esc to dismiss**  
   - **Tab**: the grey text is inserted as if the user typed it.  
   - **Esc**: the suggestion is discarded.

3. **Very quick**  
   Completions feel fast because:
   - **One long-running process** (language server / daemon), not a new process per keystroke. Reusing the same process and connection cuts a lot of latency.
   - **Debounce**: the client doesn’t ask on every keypress; it waits for a short pause (e.g. ~1 s) so the prefix is stable and requests are fewer.
   - **Streaming** (when available): the first tokens are shown as soon as they’re ready, so the UI feels responsive even if the full completion takes a bit longer.

4. **Single suggestion**  
   One “ghost” completion at a time, not a list of options.

## How this CLI autocomplete matches it

| Aspect              | Cursor/Copilot              | This CLI tool                          |
|---------------------|-----------------------------|----------------------------------------|
| Grey preview        | Ghost text inline           | Zsh `region_highlight` (grey suffix)  |
| Accept              | Tab                         | Tab                                    |
| Dismiss             | Esc                         | Keep typing / normal completion        |
| Speed                | Daemon + streaming/debounce | **Daemon** (optional) + Ollama        |
| One suggestion      | Yes                         | Yes (one completed command line)      |

### Making Tab “very quick”

- **Without daemon**: each keystroke/completion may spawn a Python process; startup dominates.
- **With daemon**: one long-lived Python process keeps the base model + LoRA adapter loaded and answers requests over a **Unix domain socket**. This avoids Python startup and avoids HTTP overhead.

**Start the daemon (recommended):**

```bash
python -m model_completer.daemon
```

Leave it running in a terminal or run it in the background. The Zsh plugin will use it when it’s available and fall back to the Python CLI otherwise.

### Flow (with daemon)

1. User types e.g. `git ad`.
2. User presses **Tab**.
3. Plugin sends `git ad` to `~/.cache/zsh-autocomplete.sock` (JSON over Unix socket).
4. Daemon runs the **base model + LoRA adapter** (merging once on first boot for speed) and returns e.g. `git add .`.
5. Plugin shows `git add .` as grey text (suffix after `git ad`); second Tab or Enter accepts it.

So the behavior is “model predicts the next bit of the command; it’s shown as grey; Tab turns it into real typing,” just like Cursor’s inline completion for code.
