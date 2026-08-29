#!/usr/bin/env python3
"""Dependency probes and audio/model operations for transcribe.sh.

Every optional dependency is reached through ``_try_import`` so this module
imports cleanly on a machine with none of them installed - which is what lets
it be unit-tested in CI.
"""

from __future__ import annotations

import array
import importlib
import logging
import math
import os
import sys
from typing import TYPE_CHECKING
import wave

if TYPE_CHECKING:
    import types

logger = logging.getLogger(__name__)


def _try_import(name: str) -> types.ModuleType | None:
    """Attempt to import a module, returning None on failure."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def get_python_version() -> str:
    """Return Python major.minor version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def check_faster_whisper() -> bool:
    """Check if faster_whisper is importable. Exit 7 if not."""
    return _try_import("faster_whisper") is not None


def check_diarization_deps() -> bool:
    """Check if diarization dependencies are available.

    Returns False with warning if missing.
    """
    _sf = _try_import("soundfile")
    _sb = _try_import("speechbrain")
    _torch = _try_import("torch")
    if _sf is None or _sb is None or _torch is None:
        logger.warning(
            "Diarization deps missing offline; speaker labels will be skipped.",
        )
        return False
    return True


def check_ctranslate2() -> bool:
    """Check if ctranslate2 is importable."""
    return _try_import("ctranslate2") is not None


def print_deps_installed() -> None:
    """Print confirmation that Python dependencies are installed."""
    logger.info("Python %s dependencies installed.", sys.version.split()[0])


def generate_sine_wav(
    outfile: str,
    frequency: float = 1000.0,
    duration: int = 3,
    sample_rate: int = 16000,
    amplitude: float = 0.3,
) -> bool:
    """Generate a sine wave WAV file using only Python stdlib.

    Args:
        outfile: Output WAV file path
        frequency: Tone frequency in Hz (default: 1000)
        duration: Duration in seconds (default: 3)
        sample_rate: Sample rate in Hz (default: 16000)
        amplitude: Amplitude 0.0-1.0 (default: 0.3)

    Returns:
        True on success, False on failure
    """
    try:
        n_samples = sample_rate * duration
        data = array.array(
            "h",
            [
                int(
                    max(
                        -1.0,
                        min(
                            1.0,
                            amplitude
                            * math.sin(2 * math.pi * frequency * (i / sample_rate)),
                        ),
                    )
                    * 32767
                )
                for i in range(n_samples)
            ],
        )
        with wave.open(outfile, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(data.tobytes())
    except OSError:
        logger.exception("Failed to generate WAV")
        return False
    return True


def prepare_model(model_name: str, model_dir: str) -> bool:
    """Download a whisper model for offline use.

    Args:
        model_name: Model name (tiny, base, small, medium, large-v3, etc.)
        model_dir: Directory to store the model

    Returns:
        True on success, False on failure
    """
    fw = _try_import("faster_whisper")
    if fw is None:
        logger.error("faster_whisper is not installed")
        return False

    try:
        hf_logging = _try_import("huggingface_hub.logging")
        if hf_logging is not None:
            hf_logging.set_verbosity_info()
        hh = _try_import("huggingface_hub")
        if hh is not None:
            hh.constants.HF_HUB_DISABLE_PROGRESS_BARS = False
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"

        logger.info("Preparing model '%s' into %s", model_name, model_dir)
        logger.info(
            "Downloading model files (progress bar should appear below)...",
        )
        fw.WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
            download_root=model_dir,
        )
        logger.info("Model prepared.")
    except OSError, RuntimeError:
        logger.exception("Failed to prepare model")
        return False
    return True


def test_cuda() -> bool:
    """Test CUDA initialization with faster-whisper.

    Returns:
        True if CUDA works, False otherwise
    """
    fw = _try_import("faster_whisper")
    if fw is None:
        logger.error("faster_whisper is not installed")
        return False

    try:
        fw.WhisperModel("tiny", device="cuda", compute_type="float16")
        logger.info("CUDA test init succeeded.")
    except OSError, RuntimeError:
        logger.exception("CUDA test failed")
        return False
    return True
