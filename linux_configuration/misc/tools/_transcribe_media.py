#!/usr/bin/env python3
"""Media duration probing and the ffmpeg transcode fallback.

Duration is probed through the ffmpeg-python binding first, then by shelling
out to ffprobe; both are optional, and an unprobeable file simply reports no
duration rather than failing the run.
"""

from __future__ import annotations

import contextlib
import importlib
import logging
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import types

logger = logging.getLogger(__name__)


def _try_import(name: str) -> types.ModuleType | None:
    """Attempt to import a module, returning None on failure."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def _probe_with_ffmpeg_python(
    path: str,
) -> float | None:
    """Try ffmpeg-python to get duration."""
    ffmpeg_mod = _try_import("ffmpeg")
    if ffmpeg_mod is None:
        return None
    try:
        probe = ffmpeg_mod.probe(path)
        fmt = probe.get("format", {})
        if "duration" in fmt:
            return float(fmt["duration"])
    except OSError, RuntimeError:
        pass
    return None


def _probe_with_ffprobe(path: str) -> float | None:
    """Try ffprobe CLI to get duration."""
    ffprobe_bin = shutil.which("ffprobe")
    if ffprobe_bin is None:
        return None
    try:
        out = subprocess.check_output(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            stderr=subprocess.DEVNULL,
        )
        return float(out.decode().strip())
    except (
        OSError,
        subprocess.CalledProcessError,
        ValueError,
    ):
        return None


def get_media_duration(path: str) -> float | None:
    """Try to get media duration in seconds.

    Returns None if unavailable.
    """
    result = _probe_with_ffmpeg_python(path)
    if result is not None:
        return result
    return _probe_with_ffprobe(path)


def _ffmpeg_transcode_to_wav16_mono(
    src_path: str,
) -> str | None:
    """Transcode input to a temporary 16k mono WAV.

    Returns its path, or None if ffmpeg is unavailable.
    """
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin is None:
        return None
    with tempfile.NamedTemporaryFile(
        prefix="fw_diar_",
        suffix=".wav",
        delete=False,
    ) as tmp:
        tmp_path = tmp.name

    cmd = [
        ffmpeg_bin,
        "-y",
        "-v",
        "error",
        "-i",
        src_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        tmp_path,
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError, subprocess.CalledProcessError:
        with contextlib.suppress(OSError):
            Path(tmp_path).unlink()
        return None
    return tmp_path


def _cleanup_temp(path: str | None) -> None:
    """Remove a temporary file if it exists."""
    if path is not None:
        with contextlib.suppress(OSError):
            Path(path).unlink()
