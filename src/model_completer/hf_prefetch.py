from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class PrefetchSpec:
    base_model_id: str
    lora_repo_id: str
    adapter_target_dir: Path


def prefetch_base_and_adapter(
    spec: PrefetchSpec,
    *,
    hf_token: Optional[str] = None,
) -> None:
    """
    Download both:
      - base model (into HF cache)
      - LoRA adapter repo (into adapter_target_dir)

    This is intended to be run once so `model_completer.autocomplete_daemon`
    can start without waiting for Hugging Face downloads.
    """
    from huggingface_hub import snapshot_download, hf_hub_download

    # Base model: cache only (respect the user's HF cache location).
    print(f"[hf] caching base model: {spec.base_model_id}", flush=True)
    try:
        snapshot_download(
            repo_id=spec.base_model_id,
            token=hf_token,
            local_files_only=True,
        )
        print("[hf] base model already cached", flush=True)
    except Exception:
        snapshot_download(
            repo_id=spec.base_model_id,
            token=hf_token,
        )

    # Adapter: materialize files to the well-known adapter directory.
    spec.adapter_target_dir.mkdir(parents=True, exist_ok=True)
    print(f"[hf] downloading adapter files: {spec.lora_repo_id}", flush=True)
    # Download only the runtime-critical files deterministically.
    for filename in ("adapter_config.json", "adapter_model.safetensors"):
        print(f"[hf]   - {filename}", flush=True)
        hf_hub_download(
            repo_id=spec.lora_repo_id,
            filename=filename,
            token=hf_token,
            local_dir=str(spec.adapter_target_dir),
            local_dir_use_symlinks=False,
        )

