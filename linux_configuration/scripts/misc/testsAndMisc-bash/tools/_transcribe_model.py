"""Model download and caching for faster-whisper."""

from __future__ import annotations

import contextlib
import importlib
import logging
from pathlib import Path
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import types

logger = logging.getLogger(__name__)

_BYTES_PER_KB = 1024

# Model name to HF repo mapping
_MODEL_MAP: dict[str, str] = {
    "tiny": "Systran/faster-whisper-tiny",
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "base": "Systran/faster-whisper-base",
    "base.en": "Systran/faster-whisper-base.en",
    "small": "Systran/faster-whisper-small",
    "small.en": "Systran/faster-whisper-small.en",
    "medium": "Systran/faster-whisper-medium",
    "medium.en": "Systran/faster-whisper-medium.en",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
    "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
}


def _try_import(name: str) -> types.ModuleType | None:
    """Attempt to import a module, returning None on failure."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def _format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    fsize = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if fsize < _BYTES_PER_KB:
            return f"{fsize:.1f}{unit}"
        fsize /= _BYTES_PER_KB
    return f"{fsize:.1f}TB"


def _check_cache(
    repo_id: str,
) -> str | None:
    """Check HF cache for an already-downloaded model."""
    hh = _try_import("huggingface_hub")
    if hh is None:
        return None
    cache_path = hh.try_to_load_from_cache(
        repo_id, "model.bin"
    )
    if cache_path is not None:
        parent = str(Path(cache_path).parent)
        logger.info(
            "Model already cached, loading from: %s",
            parent,
        )
        return parent
    return None


def _download_files(
    repo_id: str,
    required_files: list[str],
) -> str:
    """Download required model files from HuggingFace."""
    hh = _try_import("huggingface_hub")
    if hh is None:
        msg = "huggingface_hub not available"
        raise RuntimeError(msg)

    logger.info(
        "Downloading model files from %s...",
        repo_id,
    )
    logger.info(
        "This may take several minutes for large "
        "models (~3GB for large-v3)",
    )

    _log_total_download_size(repo_id, required_files)

    downloaded = 0
    model_dir = ""
    start_time = time.time()

    for filename in required_files:
        file_start = time.time()
        logger.info("DOWNLOAD %s...", filename)
        try:
            local_path = hh.hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                resume_download=True,
            )
            elapsed = time.time() - file_start
            lp = Path(local_path)
            file_size = (
                lp.stat().st_size
                if lp.exists()
                else 0
            )
            logger.info(
                "done (%s, %.1fs)",
                _format_bytes(file_size),
                elapsed,
            )
            downloaded += 1
            if downloaded == 1:
                model_dir = str(lp.parent)
        except OSError:
            logger.info("not found (optional)")
        except RuntimeError as exc:
            logger.info("error: %s", exc)

    total_time = time.time() - start_time
    logger.info("Download complete in %.1fs", total_time)
    return model_dir


def _log_total_download_size(
    repo_id: str, required_files: list[str]
) -> None:
    """Log total download size if available."""
    hh = _try_import("huggingface_hub")
    if hh is None:
        return
    with contextlib.suppress(OSError, RuntimeError):
        fs = hh.HfFileSystem()
        files_info = fs.ls(repo_id, detail=True)
        total_size = sum(
            f.get("size", 0)
            for f in files_info
            if f.get("name", "").split("/")[-1]
            in required_files
        )
        logger.info(
            "Total download size: ~%s",
            _format_bytes(total_size),
        )


def download_model_with_progress(
    model_name: str,
) -> str:
    """Download model files from HuggingFace with progress.

    Returns the local path to the downloaded model.
    """
    hh = _try_import("huggingface_hub")
    if hh is None:
        logger.warning(
            "huggingface_hub not available, "
            "falling back to default download",
        )
        return model_name

    repo_id = _MODEL_MAP.get(model_name, model_name)

    if "/" not in repo_id and model_name not in _MODEL_MAP:
        repo_id = f"Systran/faster-whisper-{model_name}"

    logger.info("Checking model: %s", repo_id)

    required_files = [
        "config.json",
        "model.bin",
        "tokenizer.json",
        "vocabulary.txt",
    ]

    try:
        cached = _check_cache(repo_id)
        if cached is not None:
            return cached
        return _download_files(repo_id, required_files)
    except (OSError, RuntimeError) as exc:
        logger.warning(
            "Custom download failed (%s), "
            "falling back to default",
            exc,
        )
        return model_name
