#!/usr/bin/env zsh
# zsh-autocomplete — AI ghost-text completions
#
# As you type, a grey suggestion appears after the cursor.
# Press Tab to accept it.  That's all there is to it.
#
# First time: run  ai-setup  to download and fine-tune the model.

# ---------------------------------------------------------------------------
# Locate project + Python
# ---------------------------------------------------------------------------

if [[ -n "$ZSH_AUTOCOMPLETE_DIR" && -d "$ZSH_AUTOCOMPLETE_DIR" ]]; then
    _ZAC_ROOT="$ZSH_AUTOCOMPLETE_DIR"
elif [[ -d "${0:A:h}/../.." && -f "${0:A:h}/../../src/daemon/autocomplete_daemon.py" ]]; then
    _ZAC_ROOT="${0:A:h}/../.."
elif [[ -d "$HOME/zsh-llm-cli-autocomplete-tool" ]]; then
    _ZAC_ROOT="$HOME/zsh-llm-cli-autocomplete-tool"
else
    echo "zsh-autocomplete: cannot find project dir (set ZSH_AUTOCOMPLETE_DIR)" >&2
    return 1
fi

_ZAC_ROOT="${_ZAC_ROOT:A}"
_ZAC_DAEMON="$_ZAC_ROOT/src/daemon/autocomplete_daemon.py"
_ZAC_TRAIN="$_ZAC_ROOT/src/training/finetune_small_model.py"
_ZAC_DATA="$_ZAC_ROOT/src/training/generate_shell_data.py"

if [[ -x "$_ZAC_ROOT/venv/bin/python3" ]]; then
    _ZAC_PY="$_ZAC_ROOT/venv/bin/python3"
elif command -v python3 &>/dev/null; then
    _ZAC_PY="$(command -v python3)"
else
    echo "zsh-autocomplete: python3 not found" >&2
    return 1
fi

# ---------------------------------------------------------------------------
# Ghost-text state
# ---------------------------------------------------------------------------

typeset -g _zac_suggestion=""
typeset -g _zac_last_input=""
typeset -g _zac_async_fd=0
typeset -g _zac_pending=""

# ---------------------------------------------------------------------------
# Daemon helpers
# ---------------------------------------------------------------------------

_zac_sock()    { echo "$HOME/.cache/zsh-autocomplete.sock" }
_zac_pidfile() { echo "$HOME/.cache/zsh-autocomplete.pid"  }
_zac_log()     { echo "$HOME/.cache/zsh-autocomplete.log"  }

_zac_alive() {
    local sock="$(_zac_sock)"
    [[ -S "$sock" ]] || return 1
    local pid_file="$(_zac_pidfile)"
    [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file" 2>/dev/null)" 2>/dev/null
}

_zac_start_daemon() {
    _zac_alive && return 0
    local _pid_file="$(_zac_pidfile)"
    if [[ -f "$_pid_file" ]]; then
        local _pid=$(cat "$_pid_file" 2>/dev/null)
        kill -0 "$_pid" 2>/dev/null && return 0
    fi
    [[ -f "$_ZAC_DAEMON" ]] || return 1
    # Prefer module entrypoint so imports resolve consistently.
    # Keep file path fallback (`$_ZAC_DAEMON`) for backwards compatibility.
    PYTHONPATH="$_ZAC_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
      nohup "$_ZAC_PY" -m model_completer.daemon >> "$(_zac_log)" 2>&1 &!
}

_zac_stop_daemon() {
    local pid_file="$(_zac_pidfile)"
    if [[ -f "$pid_file" ]]; then
        kill "$(cat "$pid_file" 2>/dev/null)" 2>/dev/null
        rm -f "$pid_file"
    fi
    rm -f "$(_zac_sock)"
}

# ---------------------------------------------------------------------------
# Context gathering — enriches completions with live project state
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Query daemon (runs in subshell → async pipe)
# ---------------------------------------------------------------------------

# All context gathering and socket I/O happen in a single Python process.
# Data is passed via environment variables to avoid shell injection.
_zac_query() {
    local input="$1"
    [[ -S "$(_zac_sock)" ]] || return
    ZAC_SOCK="$(_zac_sock)" ZAC_INPUT="$input" ZAC_CWD="$PWD" \
    "$_ZAC_PY" - 2>/dev/null <<'EOF'
import json, os, re, socket, subprocess
from pathlib import Path

sock_path = os.environ["ZAC_SOCK"]
text      = os.environ["ZAC_INPUT"]
cwd       = os.environ["ZAC_CWD"]
ctx: dict = {"cwd": cwd}

# --- git context ---
try:
    in_git = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=cwd, capture_output=True, timeout=1
    ).returncode == 0
    if in_git:
        branch = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=cwd, capture_output=True, timeout=1, text=True
        ).stdout.strip()
        if branch:
            ctx["git_branch"] = branch
        # For commit messages: staged diff + recent log style.
        # Trigger early on partial intent: git co / git com / git comm / ...
        if re.search(r'^git\s+c(o(m(m(i(t)?)?)?)?)?(\s|$)', text):
            diff = subprocess.run(
                ["git", "diff", "--staged", "--stat"],
                cwd=cwd, capture_output=True, timeout=2, text=True
            ).stdout.strip()
            log_raw = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                cwd=cwd, capture_output=True, timeout=2, text=True
            ).stdout.strip()
            # Strip hashes, keep messages only
            log = "\n".join(
                line.split(" ", 1)[1] if " " in line else line
                for line in log_raw.splitlines()
            )
            if diff: ctx["git_diff"] = diff
            if log:  ctx["git_log"] = log
except Exception:
    pass

# --- npm / yarn / pnpm run: inject available scripts ---
if re.match(r"(npm|yarn|pnpm) run", text):
    pkg = Path(cwd) / "package.json"
    if pkg.exists():
        try:
            scripts = list(json.loads(pkg.read_text()).get("scripts", {}).keys())
            if scripts:
                ctx["npm_scripts"] = ", ".join(scripts)
        except Exception:
            pass

# --- make: inject Makefile targets ---
if text.startswith("make "):
    mf = Path(cwd) / "Makefile"
    if mf.exists():
        try:
            targets = [
                line.split(":")[0]
                for line in mf.read_text().splitlines()
                if re.match(r"^[a-zA-Z0-9_-]+:", line)
            ][:20]
            if targets:
                ctx["make_targets"] = " ".join(targets)
        except Exception:
            pass

# --- send request to daemon ---
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(sock_path)
    s.sendall(json.dumps({"id": "1", "input": text, "context": ctx}).encode())
    buf = b""
    while chunk := s.recv(4096):
        buf += chunk
        if len(chunk) < 4096:
            break
    c = json.loads(buf).get("completion", "")
    if c:
        print(c, end="")
except Exception:
    pass
EOF
}

# ---------------------------------------------------------------------------
# Async fd callback
# ---------------------------------------------------------------------------

# Apply ghost text — called as a ZLE widget so BUFFER is properly accessible.
# Reads _zac_pending (set by _zac_on_result) and updates POSTDISPLAY.
_zac_apply_ghost() {
    local completion="$_zac_pending"
    _zac_pending=""
    [[ -z "$completion" ]] && return
    [[ -z "$BUFFER" ]] && return
    # Completion must extend what's currently in the buffer
    [[ "$completion" == "$BUFFER"* && "$completion" != "$BUFFER" ]] || return
    _zac_suggestion="$completion"
    POSTDISPLAY="${completion#${BUFFER}}"
    local b=${#BUFFER} p=${#POSTDISPLAY}
    region_highlight=("$b $(( b + p )) fg=244")
}

_zac_on_result() {
    local fd="$1"
    local completion
    { IFS='' read -r -u $fd completion } 2>/dev/null
    zle -F "$fd" 2>/dev/null
    exec {fd}<&- 2>/dev/null
    _zac_async_fd=0

    # Store completion globally then invoke as a widget — widget calls have
    # proper BUFFER access, unlike zle -F callbacks where $BUFFER reads empty.
    if [[ -n "$completion" && -n "$_zac_last_input" && "$completion" != "$_zac_last_input" ]]; then
        _zac_pending="$completion"
        zle _zac_apply_ghost
        zle -R
    fi
}

# ---------------------------------------------------------------------------
# Fetch (fire on every keypress)
# ---------------------------------------------------------------------------

_zac_fetch() {
    local input="$BUFFER"
    if (( ${#input} < 2 )); then
        _zac_clear_ghost
        return
    fi
    [[ "$input" == "$_zac_last_input" ]] && return

    _zac_last_input="$input"
    POSTDISPLAY=""
    region_highlight=()
    _zac_suggestion=""

    if (( _zac_async_fd )); then
        zle -F "$_zac_async_fd" 2>/dev/null
        exec {_zac_async_fd}<&- 2>/dev/null
        _zac_async_fd=0
    fi

    exec {_zac_async_fd}< <(_zac_query "$input")
    zle -F "$_zac_async_fd" _zac_on_result
}

_zac_clear_ghost() {
    POSTDISPLAY=""
    region_highlight=()
    _zac_suggestion=""
    _zac_last_input=""
    if (( _zac_async_fd )); then
        zle -F "$_zac_async_fd" 2>/dev/null
        exec {_zac_async_fd}<&- 2>/dev/null
        _zac_async_fd=0
    fi
}

# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------

# Tab: accept ghost text or fall through to normal completion
_zac_tab() {
    if [[ -n "$_zac_suggestion" && "$_zac_suggestion" != "$BUFFER" ]]; then
        BUFFER="$_zac_suggestion"
        CURSOR=${#BUFFER}
        POSTDISPLAY=""
        region_highlight=()
        _zac_suggestion=""
        _zac_last_input="$BUFFER"
    else
        zle expand-or-complete
    fi
}

# Wraps self-insert — fires on every character typed
_zac_self_insert() {
    zle .self-insert "$@"
    _zac_fetch
}

# Also fires on delete/backspace so ghost text clears immediately
_zac_backward_delete() {
    zle .backward-delete-char "$@"
    _zac_fetch
}

# Clear ghost text and state when user submits the line
_zac_accept_line() {
    _zac_clear_ghost
    zle .accept-line
}

_zac_test_ghost() {
    # Synchronous test: type something, press Ctrl-G — should show grey " [ghost]" suffix.
    # If it appears: POSTDISPLAY works. If not: terminal/ZLE issue unrelated to async.
    POSTDISPLAY=" [ghost]"
    local b=${#BUFFER} p=${#POSTDISPLAY}
    region_highlight=("$b $(( b + p )) fg=244")
    zle -R
}

_zac_do_init() {
    zle -N _zac_on_result
    zle -N _zac_apply_ghost
    zle -N _zac_tab
    zle -N _zac_test_ghost
    zle -N self-insert          _zac_self_insert
    zle -N backward-delete-char _zac_backward_delete
    zle -N accept-line          _zac_accept_line

    bindkey '^I' _zac_tab       # Tab
    bindkey '^G' _zac_test_ghost # Ctrl-G: test ghost text rendering
    bindkey '^M' accept-line    # Enter (CR)
    bindkey '^J' accept-line    # Enter (LF)
}

# Try immediately (works if sourced in a running interactive session)
_zac_do_init

# Also register via precmd_functions in case ZLE wasn't ready yet
# (e.g. sourced from .zshrc before ZLE starts)
_zac_init_once() {
    # Remove self so this only runs once
    precmd_functions=("${(@)precmd_functions:#_zac_init_once}")
    _zac_do_init
}
precmd_functions+=(_zac_init_once)

# ---------------------------------------------------------------------------
# User-facing commands
# ---------------------------------------------------------------------------

ai-setup() {
    echo "Setting up zsh-autocomplete..."
    echo "Model: Qwen2.5-1.5B-Instruct + LoRA adapter (from HuggingFace)"
    echo ""

    local adapter_dir="$HOME/.local/share/zsh-autocomplete/lora-adapter"
    local hf_repo="duoyuncloud/zsh-autocomplete-lora"

    # 1. Install Python deps
    echo "[1/3] Installing Python dependencies..."
    "$_ZAC_PY" -m pip install -q --upgrade \
        torch transformers peft sentencepiece huggingface_hub \
        2>&1 | tail -3
    echo "      Done."

    # 2. Download pre-trained adapter
    echo "[2/3] Downloading LoRA adapter from HuggingFace..."
    echo "      (repo: $hf_repo  base: Qwen2.5-1.5B-Instruct)"
    "$_ZAC_PY" - <<PYEOF
from huggingface_hub import snapshot_download
snapshot_download(repo_id="$hf_repo", local_dir="$adapter_dir")
print("      Adapter ready.")
PYEOF

    # 3. Start daemon (merges adapter + base model on first boot)
    echo "[3/3] Starting autocomplete daemon..."
    _zac_stop_daemon
    sleep 0.3
    _zac_start_daemon
    sleep 2

    if _zac_alive; then
        echo ""
        echo "Ready. Start typing — grey completions appear after your cursor."
        echo "Press Tab to accept."
    else
        echo ""
        echo "Daemon failed to start. Check: $(_zac_log)"
    fi
}

ai-status() {
    echo "zsh-autocomplete"
    if _zac_alive; then
        echo "  daemon : running"
    else
        echo "  daemon : stopped  (run: ai-setup)"
    fi
    local adapter="$HOME/.local/share/zsh-autocomplete/lora-adapter/adapter_config.json"
    local merged="$HOME/.local/share/zsh-autocomplete/merged-model/config.json"
    if [[ -f "$merged" ]]; then
        echo "  model  : Qwen2.5-1.5B-Instruct + LoRA (merged, ready)"
    elif [[ -f "$adapter" ]]; then
        echo "  model  : Qwen2.5-1.5B-Instruct + LoRA adapter (merging on next start)"
    else
        echo "  model  : not trained yet (run: ai-setup)"
    fi
    if [[ -n "$ANTHROPIC_API_KEY" ]]; then
        echo "  claude : enabled (complex completions routed to Claude Haiku)"
    else
        echo "  claude : disabled (set ANTHROPIC_API_KEY to enable)"
    fi
    echo "  log    : $(_zac_log)"
}

ai-restart() {
    _zac_stop_daemon
    sleep 0.3
    _zac_start_daemon
    echo "Daemon restarted"
}

ai-debug() {
    echo "=== zsh-autocomplete diagnostics ==="
    echo ""

    echo "[1] Daemon"
    if _zac_alive; then
        echo "    status : running"
    else
        echo "    status : STOPPED — run: ai-setup"
        return 1
    fi

    echo "[2] Completion query (input: 'git comm')"
    local result
    result=$("$_ZAC_PY" - "$(_zac_sock)" "git comm" "{}" 2>&1 <<'PYEOF'
import socket, json, sys
sock, text = sys.argv[1], sys.argv[2]
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(5); s.connect(sock)
s.sendall(json.dumps({"id":"1","input":text,"context":{}}).encode())
buf=b""
while c:=s.recv(4096): buf+=c
print(json.loads(buf).get("completion","(empty)"))
PYEOF
)
    echo "    result : $result"

    echo "[3] ZLE widget overrides"
    local si
    si=$(zle -l -L self-insert 2>/dev/null)
    if [[ "$si" == *_zac_self_insert* ]]; then
        echo "    self-insert → _zac_self_insert : OK"
    else
        echo "    self-insert → _zac_self_insert : NOT set ← main issue"
        echo "    current: $si"
    fi

    echo "[4] Keybinding"
    local tab_binding
    tab_binding=$(bindkey "^I" 2>/dev/null | awk '{print $2}')
    echo "    Tab (^I) bound to : $tab_binding"

    echo "[5] Claude API"
    if [[ -n "$ANTHROPIC_API_KEY" ]]; then
        echo "    ANTHROPIC_API_KEY : set (complex completions use Claude Haiku)"
    else
        echo "    ANTHROPIC_API_KEY : not set (local model only)"
    fi

    echo "[6] POSTDISPLAY test"
    print -P "    %F{8}[ghost text appears in grey like this]%f"

    echo ""
    echo "=== done ==="
}

# ---------------------------------------------------------------------------
# Auto-start daemon at shell init (silent, non-blocking)
# ---------------------------------------------------------------------------

{ _zac_start_daemon } &!
