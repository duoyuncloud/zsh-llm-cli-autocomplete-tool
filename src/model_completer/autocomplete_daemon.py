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

        seen: dict[str, None] = {}
        commands: list[str] = []
        for line in raw.splitlines():
            # zsh extended history: ": timestamp:elapsed;command"
            if line.startswith(": ") and ";" in line:
                cmd = line.split(";", 1)[1]
            else:
                cmd = line
            cmd = cmd.strip()
            if cmd and cmd not in seen:
                seen[cmd] = None
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


def _build_system(input_text: str, context: dict) -> str:
    """Build a context-enriched system prompt."""
    parts: list[str] = []

    _history.refresh()
    examples = _history.similar(input_text, k=5)
    if not examples:
        tokens = input_text.split()
        short = " ".join(tokens[:2]) if len(tokens) >= 2 else input_text
        if short != input_text:
            examples = _history.similar(short, k=5)
    if examples:
        parts.append("Recent matching commands from your history:")
        parts.extend(f"  {ex}" for ex in examples)

    if re.match(r'git commit\b.*-m\s*["\']', input_text):
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
    if re.match(r'git commit\b.*-m\s*["\']', input_text):
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
                return result

        return await loop.run_in_executor(None, _backend.complete, inp, system)


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

