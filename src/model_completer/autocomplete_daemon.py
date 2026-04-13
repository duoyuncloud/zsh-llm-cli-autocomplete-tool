#!/usr/bin/env python3
"""Autocomplete daemon (Cursor-style inline completion).

This is the runtime backend for the Zsh plugin's grey "ghost text" predictions.

- **Model**: base model + optional LoRA adapter (merged on first boot for speed).
- **Transport**: Unix domain socket at `~/.cache/zsh-autocomplete.sock`.
- **Client**: `src/scripts/zsh_autocomplete.plugin.zsh` (connects via a short Python snippet).
"""

import asyncio
import json
import logging
import os
import re
import signal
import sys
from collections import Counter
from pathlib import Path

DEFAULT_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_DIR = Path.home() / ".local/share/zsh-autocomplete/lora-adapter"
MERGED_ROOT = Path.home() / ".local/share/zsh-autocomplete/merged-model"
SOCKET_PATH = Path.home() / ".cache/zsh-autocomplete.sock"
PID_PATH = Path.home() / ".cache/zsh-autocomplete.pid"
LOG_PATH = Path.home() / ".cache/zsh-autocomplete.log"
HISTORY_PATH = Path.home() / ".zsh_history"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="a")],
)
logger = logging.getLogger(__name__)

_DUMMY_MODE = os.environ.get("ZAC_DAEMON_DUMMY") == "1"


def _looks_like_commit_request(inp: str) -> bool:
    s = inp.strip()
    # Support partial commit intent prefixes: git co / git com / git comm / ...
    # (requested UX: smart commit should trigger before full "git commit" is typed)
    if re.match(r"^git\s+c(o(m(m(i(t)?)?)?)?)?$", s):
        return True
    return (
        s.startswith("git comm")
        or s.startswith("git commit")
        or re.match(r'git\s+commit\b.*-m\s*["\']?$', s) is not None
    )


def _normalize_commit_completion(inp: str, completion: str, ctx: dict) -> str:
    """
    Keep smart-commit model-driven, but enforce output shape:
      git commit -m "type: concise subject"
    """
    c = (completion or "").strip()
    if not c:
        c = inp

    # Try to extract quoted message first.
    m = re.search(r'git\s+commit\b.*?-m\s*"(.*?)"', c)
    if m:
        msg = m.group(1).strip()
    else:
        # Or recover from raw "type: subject" style output.
        m2 = re.search(r"\b(feat|fix|docs|refactor|test|chore)\s*:\s*(.+)$", c, re.I)
        if m2:
            msg = f"{m2.group(1).lower()}: {m2.group(2).strip()}"
        else:
            msg = _fallback_commit_message(ctx)

    msg = msg.replace('"', "").strip()
    # enforce "<type>: <subject>" minimal structure
    if ":" not in msg:
        msg = f"chore: {msg}" if msg else "chore: update changes"
    t, s = msg.split(":", 1)
    t = t.strip().lower()
    if t not in {"feat", "fix", "docs", "refactor", "test", "chore"}:
        t = "chore"
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^(feat|fix|docs|refactor|test|chore)\s*:\s*", "", s, flags=re.I)
    s = s[:80]
    if not s:
        s = "update changes"
    if str(ctx.get("git_diff", "")).strip():
        generic = {
            "initial commit",
            "resolve merge conflict",
            "merge branch",
            "update changes",
            "update staged changes",
        }
        if s.lower() in generic:
            fb = _fallback_commit_message(ctx)
            mfb = re.match(
                r"^(feat|fix|docs|refactor|test|chore)\s*:\s*(.+)$", fb, re.I
            )
            if mfb:
                if t == "chore":
                    t = mfb.group(1).lower()
                s = mfb.group(2).strip()
    return f'git commit -m "{t}: {s}"'


def _fallback_commit_message(ctx: dict) -> str:
    diff = str(ctx.get("git_diff", "")).strip()
    git_log = str(ctx.get("git_log", "")).strip()
    ctype = "chore"
    if git_log:
        first = git_log.splitlines()[0].strip()
        m = re.match(r"^(feat|fix|docs|refactor|test|chore)\s*:", first, re.I)
        if m:
            ctype = m.group(1).lower()

    subject = "update staged changes"
    if diff:
        for line in diff.splitlines():
            if "|" in line:
                path = line.split("|", 1)[0].strip().split("/")[-1]
                path = re.sub(r"\.[a-zA-Z0-9]+$", "", path)
                path = path.replace("_", " ").replace("-", " ").strip()
                if path:
                    subject = f"update {path}"
                    break
    return f"{ctype}: {subject}"


def _adapter_base_model() -> str:
    cfg = ADAPTER_DIR / "adapter_config.json"
    if not cfg.exists():
        return DEFAULT_MODEL_ID
    try:
        data = json.loads(cfg.read_text())
        base = str(data.get("base_model_name_or_path") or "").strip()
        return base or DEFAULT_MODEL_ID
    except Exception:
        return DEFAULT_MODEL_ID


def _merged_dir_for_model(model_id: str) -> Path:
    slug = model_id.replace("/", "--").replace(":", "--").replace(".", "_")
    return MERGED_ROOT / slug


class _HistoryIndex:
    """Lightweight in-memory index over ~/.zsh_history."""

    def __init__(self) -> None:
        self._commands: list[str] = []
        self._mtime: float = 0.0

    def refresh(self) -> None:
        try:
            mtime = HISTORY_PATH.stat().st_mtime
        except FileNotFoundError:
            return
        if mtime <= self._mtime:
            return
        self._mtime = mtime
        try:
            raw = HISTORY_PATH.read_bytes().decode("utf-8", errors="replace")
        except OSError:
            return

        commands: list[str] = []
        for line in raw.splitlines():
            # zsh extended history: ": timestamp:elapsed;command"
            if line.startswith(": ") and ";" in line:
                cmd = line.split(";", 1)[1]
            else:
                cmd = line
            cmd = cmd.strip()
            if cmd:
                commands.append(cmd)
        self._commands = commands[-5000:]
        logger.info("History index: %s commands", len(self._commands))

    def similar(self, prefix: str, k: int = 5) -> list[str]:
        """Return up to k recent commands that start with prefix."""
        prefix_lower = prefix.lower()
        seen: set[str] = set()
        results: list[str] = []
        for cmd in reversed(self._commands):
            if cmd.lower().startswith(prefix_lower) and cmd != prefix:
                if cmd not in seen:
                    seen.add(cmd)
                    results.append(cmd)
                    if len(results) >= k:
                        break
        return results


_history = _HistoryIndex()


def _command_key(command: str) -> str:
    toks = command.strip().split()
    if not toks:
        return ""
    if toks[0] == "git" and len(toks) >= 2:
        return f"git {toks[1]}"
    return toks[0]


def _history_next_key(current_key: str) -> str:
    """
    Learn workflow transitions from user history.
    Returns a probable next command key (e.g. 'git push') or empty string.
    """
    if not current_key:
        return ""
    _history.refresh()
    transitions: Counter[str] = Counter()
    total = 0
    cmds = _history._commands
    for i in range(len(cmds) - 1):
        cur = _command_key(cmds[i])
        nxt = _command_key(cmds[i + 1])
        if cur == current_key and nxt:
            transitions[nxt] += 1
            total += 1
    if total < 3 or not transitions:
        return ""
    nxt, count = transitions.most_common(1)[0]
    # Require reasonable confidence so rules don't feel random.
    if count / total < 0.55:
        return ""
    return nxt


def _history_transition_stats(current_key: str, top_k: int = 3) -> tuple[int, list[tuple[str, int]]]:
    """
    Return transition frequency summary for current_key:
      total transitions from current_key,
      top next keys with counts.
    """
    if not current_key:
        return 0, []
    _history.refresh()
    transitions: Counter[str] = Counter()
    total = 0
    cmds = _history._commands
    for i in range(len(cmds) - 1):
        cur = _command_key(cmds[i])
        nxt = _command_key(cmds[i + 1])
        if cur == current_key and nxt:
            transitions[nxt] += 1
            total += 1
    return total, transitions.most_common(top_k)


def _context_recent_commands(ctx: dict) -> list[str]:
    raw = ctx.get("recent_commands")
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        return [line.strip() for line in raw.splitlines() if line.strip()]
    return []


def _blended_commands(ctx: dict) -> list[str]:
    _history.refresh()
    cmds = list(_history._commands)
    recent = _context_recent_commands(ctx)
    if not recent:
        return cmds
    for cmd in recent:
        if not cmds or cmds[-1] != cmd:
            cmds.append(cmd)
    return cmds[-5000:]


def _similar_from_commands(commands: list[str], prefix: str, k: int = 5) -> list[str]:
    prefix_lower = prefix.lower()
    seen: set[str] = set()
    results: list[str] = []
    for cmd in reversed(commands):
        if cmd.lower().startswith(prefix_lower) and cmd != prefix:
            if cmd not in seen:
                seen.add(cmd)
                results.append(cmd)
                if len(results) >= k:
                    break
    return results


def _transition_stats_from_commands(
    commands: list[str], current_key: str, top_k: int = 3
) -> tuple[int, list[tuple[str, int]]]:
    if not current_key:
        return 0, []
    transitions: Counter[str] = Counter()
    total = 0
    for i in range(len(commands) - 1):
        cur = _command_key(commands[i])
        nxt = _command_key(commands[i + 1])
        if cur == current_key and nxt:
            transitions[nxt] += 1
            total += 1
    return total, transitions.most_common(top_k)


def _workflow_hint(inp: str, ctx: dict) -> str:
    """
    Build prompt-only workflow guidance (no hard override).
    Priority:
      1) user-history transition
      2) common fallback workflow hint
    """
    key = _command_key(inp.strip())
    if not key:
        return ""
    commands = _blended_commands(ctx)
    if not commands:
        return ""

    # Cross-command workflow hint: use the last executed command as state.
    prev_key = _command_key(commands[-1])
    if prev_key:
        prev_total, prev_top = _transition_stats_from_commands(commands, prev_key, top_k=2)
        if prev_total >= 3 and prev_top:
            prev_parts = [f"{nxt} ({cnt}/{prev_total})" for nxt, cnt in prev_top]
            cross = (
                f"Your last command was '{prev_key}'. "
                f"Likely next commands are: {', '.join(prev_parts)}."
            )
        else:
            cross = ""
    else:
        cross = ""

    total, top = _transition_stats_from_commands(commands, key, top_k=3)
    if total >= 3 and top:
        parts = [f"{nxt} ({cnt}/{total})" for nxt, cnt in top]
        direct = (
            f"From your history, likely next commands after '{key}': "
            + ", ".join(parts)
            + "."
        )
        return f"{cross} {direct}".strip()

    if key == "git add":
        base = "Typical git workflow: after 'git add', users often run 'git commit'."
        return f"{cross} {base}".strip()
    if key == "git commit":
        base = "Typical git workflow: after 'git commit', users often run 'git push'."
        return f"{cross} {base}".strip()
    return cross


def _sanitize_completion(input_text: str, completion: str) -> str:
    """
    Safety filter for risky flags in generated output.
    Keep model in control, but prevent unsolicited force-push suggestions.
    """
    c = completion.strip()
    if not c:
        return c

    # If user didn't type force intent, remove force flags from git push suggestions.
    typed_force = "--force" in input_text or "--force-with-lease" in input_text or re.search(r"\s-f(\s|$)", input_text or "")
    if c.startswith("git push") and not typed_force:
        c = c.replace("--force-with-lease", "")
        c = c.replace("--force", "")
        c = re.sub(r"\s-f(\s|$)", " ", c)
        c = re.sub(r"\s{2,}", " ", c).strip()

    return c


def _build_system(input_text: str, context: dict) -> str:
    """Build a context-enriched system prompt."""
    parts: list[str] = []

    commands = _blended_commands(context)
    examples = _similar_from_commands(commands, input_text, k=5)
    if not examples:
        tokens = input_text.split()
        short = " ".join(tokens[:2]) if len(tokens) >= 2 else input_text
        if short != input_text:
            examples = _similar_from_commands(commands, short, k=5)
    if examples:
        parts.append("Recent matching commands from your history:")
        parts.extend(f"  {ex}" for ex in examples)

    hint = _workflow_hint(input_text, context)
    if hint:
        parts.append(f"\nWorkflow hint: {hint}")

    if _looks_like_commit_request(input_text):
        parts.append(
            "\nFor commit intents, output exactly one command in this form: "
            'git commit -m "type: subject". '
            "Type must be one of feat/fix/docs/refactor/test/chore. "
            "Subject must be concise and based on staged changes. "
            "Do not output generic messages like 'initial commit' unless the diff clearly indicates that."
        )
    if _looks_like_commit_request(input_text):
        if context.get("git_diff"):
            parts.append(f"\nStaged changes:\n{context['git_diff']}")
        if context.get("git_log"):
            parts.append(f"\nRecent commit style:\n{context['git_log']}")
    elif re.match(r"git (checkout|switch|merge|rebase|push|pull)\b", input_text):
        if context.get("git_branch"):
            parts.append(f"\nCurrent branch: {context['git_branch']}")
    elif re.match(r"(npm|yarn|pnpm) run\b", input_text):
        if context.get("npm_scripts"):
            parts.append(f"\nAvailable scripts: {context['npm_scripts']}")
    elif input_text.startswith("make "):
        if context.get("make_targets"):
            parts.append(f"\nMakefile targets: {context['make_targets']}")

    if context.get("cwd"):
        parts.append(f"\nWorking directory: {context['cwd']}")

    base = (
        "You complete shell commands for a developer. "
        "Output only the completed command — no explanation, no markdown."
    )
    if parts:
        return base + "\n\n" + "\n".join(parts)
    return base


def _claude_complete(input_text: str, system: str) -> str | None:
    """Call Claude if ANTHROPIC_API_KEY is set. Returns None on any failure."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic

        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=120,
            system=system,
            messages=[{"role": "user", "content": f"Complete: {input_text}"}],
        )
        completion = msg.content[0].text.strip()
        for stop in ("\n", ";", " &&", " ||"):
            if stop in completion:
                completion = completion[: completion.index(stop)]
        completion = completion.strip()
        if completion and not completion.startswith(input_text):
            completion = input_text + completion.lstrip()
        return completion if completion != input_text else None
    except Exception as e:
        logger.debug("Claude API error: %s", e)
        return None


def _should_use_api(input_text: str) -> bool:
    if _looks_like_commit_request(input_text):
        return True
    return len(input_text) > 45


class _ModelBackend:
    def __init__(self) -> None:
        self.model = None
        self.tokenizer = None
        self.device: str = "cpu"

    def load(self) -> None:
        if _DUMMY_MODE:
            logger.warning("ZAC_DAEMON_DUMMY=1 enabled — skipping model load")
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if torch.backends.mps.is_available():
            self.device = "mps"
            dtype = torch.float16
        elif torch.cuda.is_available():
            self.device = "cuda"
            dtype = torch.float16
        else:
            self.device = "cpu"
            dtype = torch.float32

        src = self._model_source()
        self.tokenizer = AutoTokenizer.from_pretrained(src, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        logger.info("Loading model from '%s' on %s (%s)", src, self.device, dtype)
        self.model = AutoModelForCausalLM.from_pretrained(
            src, dtype=dtype, device_map=self.device, trust_remote_code=True
        )
        self.model.eval()
        logger.info("Model ready")

    @staticmethod
    def _model_source() -> str:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        model_id = _adapter_base_model()
        merged_dir = _merged_dir_for_model(model_id)

        if (merged_dir / "config.json").exists():
            logger.info("Loading merged model from %s", merged_dir)
            return str(merged_dir)

        adapter_cfg = ADAPTER_DIR / "adapter_config.json"
        if adapter_cfg.exists():
            logger.info("Merging LoRA adapter (one-time, ~30s)...")
            dtype = (
                torch.float16
                if (torch.backends.mps.is_available() or torch.cuda.is_available())
                else torch.float32
            )
            from peft import PeftModel

            tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
            base = AutoModelForCausalLM.from_pretrained(
                model_id, dtype=dtype, device_map="cpu", trust_remote_code=True
            )
            merged = PeftModel.from_pretrained(base, str(ADAPTER_DIR)).merge_and_unload()
            merged_dir.mkdir(parents=True, exist_ok=True)
            merged.save_pretrained(str(merged_dir))
            tokenizer.save_pretrained(str(merged_dir))
            logger.info("Merged model saved to %s", merged_dir)
            return str(merged_dir)

        logger.info("No adapter found — using base %s", model_id)
        return model_id

    def complete(self, input_text: str, system: str) -> str:
        if _DUMMY_MODE:
            # Deterministic "completion" for protocol/UI smoke tests.
            return (input_text.rstrip() + " __dummy_completion__").strip()
        import torch

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Complete: {input_text}"},
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        input_len = inputs["input_ids"].shape[1]

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=80,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        new_tokens = output_ids[0][input_len:]
        completion = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        for stop in ("\n", ";", " &&", " ||", " #"):
            if stop in completion:
                completion = completion[: completion.index(stop)]
        completion = completion.strip()

        if completion and not completion.startswith(input_text):
            completion = input_text + completion.lstrip()

        return completion if completion != input_text else ""


_backend = _ModelBackend()


class AutocompleteDaemon:
    def __init__(self) -> None:
        self._pending_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        logger.info("Starting model load...")
        await loop.run_in_executor(None, _backend.load)

        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)

        server = await asyncio.start_unix_server(self._handle, path=str(SOCKET_PATH))
        logger.info("Listening on %s", SOCKET_PATH)
        async with server:
            await server.serve_forever()

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            raw = await asyncio.wait_for(reader.read(32768), timeout=2)
            req = json.loads(raw.decode())
            req_id = req.get("id", "")
            inp = (req.get("input") or "").strip()
            ctx = req.get("context") or {}

            completion = await self._fetch(inp, ctx)

            writer.write(json.dumps({"id": req_id, "completion": completion}).encode())
            await writer.drain()
        except (asyncio.TimeoutError, json.JSONDecodeError):
            pass
        except Exception as e:
            logger.error("Handle error: %s", e)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _fetch(self, inp: str, ctx: dict) -> str:
        async with self._lock:
            if self._pending_task and not self._pending_task.done():
                self._pending_task.cancel()
                try:
                    await self._pending_task
                except (asyncio.CancelledError, Exception):
                    pass
            task = asyncio.create_task(self._complete(inp, ctx))
            self._pending_task = task

        try:
            return await task
        except asyncio.CancelledError:
            return ""
        except Exception as e:
            logger.error("Completion error: %s", e)
            return ""

    @staticmethod
    async def _complete(inp: str, ctx: dict) -> str:
        if not inp:
            return ""

        loop = asyncio.get_running_loop()
        system = _build_system(inp, ctx)

        if _should_use_api(inp):
            result = await loop.run_in_executor(None, _claude_complete, inp, system)
            if result:
                logger.info("Claude: %r → %r", inp, result)
                cleaned = _sanitize_completion(inp, result)
                if _looks_like_commit_request(inp):
                    return _normalize_commit_completion(inp, cleaned, ctx)
                return cleaned

        raw = await loop.run_in_executor(None, _backend.complete, inp, system)
        cleaned = _sanitize_completion(inp, raw)
        if _looks_like_commit_request(inp):
            return _normalize_commit_completion(inp, cleaned, ctx)
        return cleaned


def main() -> None:
    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()))

    def _shutdown(sig, _frame):
        logger.info("Signal %s — shutting down", sig)
        for p in (SOCKET_PATH, PID_PATH):
            try:
                p.unlink()
            except FileNotFoundError:
                pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        asyncio.run(AutocompleteDaemon().start())
    except KeyboardInterrupt:
        pass
    finally:
        for p in (SOCKET_PATH, PID_PATH):
            try:
                p.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    main()

