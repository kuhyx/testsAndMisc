"""Tests for media-duration probing and temp-file handling.

Duration is probed twice: through the ffmpeg-python binding if it is
importable, then by shelling out to ffprobe. Both are patched here, so the
tests pass whether or not ffmpeg is installed on the machine running them.
"""

from __future__ import annotations

import shutil
import subprocess

import _transcribe_diarize as diar
import pytest


class _FfmpegModule:
    """An ffmpeg-python double whose probe() returns a fixed payload."""

    def __init__(self, payload: object) -> None:
        self._payload = payload

    def probe(self, _path: str) -> object:
        """Return the canned probe result, or raise it if it is an error."""
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _only(name: str, module: object) -> object:
    """Return a _try_import double resolving exactly one module name."""

    def _try(requested: str) -> object | None:
        return module if requested == name else None

    return _try


# --------------------------------------------------------------------------- #
# The optional-dependency import seam
# --------------------------------------------------------------------------- #
def test_try_import_returns_the_module_when_present() -> None:
    """The seam the other tests patch works against a real module."""
    assert diar._try_import("json") is not None


def test_try_import_returns_none_for_a_missing_module() -> None:
    """A missing optional dependency is None, not an ImportError."""
    assert diar._try_import("no_such_module_anywhere_12345") is None


# --------------------------------------------------------------------------- #
# _probe_with_ffmpeg_python
# --------------------------------------------------------------------------- #
def test_probe_with_ffmpeg_python_reads_the_format_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The binding reports duration under probe()['format']['duration']."""
    module = _FfmpegModule({"format": {"duration": "123.5"}})
    monkeypatch.setattr(diar, "_try_import", _only("ffmpeg", module))

    assert diar._probe_with_ffmpeg_python("clip.wav") == pytest.approx(123.5)


def test_probe_with_ffmpeg_python_returns_none_without_the_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without ffmpeg-python installed this probe declines."""
    monkeypatch.setattr(diar, "_try_import", lambda _n: None)

    assert diar._probe_with_ffmpeg_python("clip.wav") is None


def test_probe_with_ffmpeg_python_returns_none_without_a_duration_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A probe result with no duration falls through to the next method."""
    module = _FfmpegModule({"format": {}})
    monkeypatch.setattr(diar, "_try_import", _only("ffmpeg", module))

    assert diar._probe_with_ffmpeg_python("clip.wav") is None


@pytest.mark.parametrize("error", [OSError("boom"), RuntimeError("boom")])
def test_probe_with_ffmpeg_python_survives_a_probe_error(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """A failing probe returns None rather than propagating."""
    monkeypatch.setattr(diar, "_try_import", _only("ffmpeg", _FfmpegModule(error)))

    assert diar._probe_with_ffmpeg_python("clip.wav") is None


# --------------------------------------------------------------------------- #
# _probe_with_ffprobe
# --------------------------------------------------------------------------- #
def test_probe_with_ffprobe_parses_the_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ffprobe prints a bare float, which is parsed to seconds."""
    monkeypatch.setattr(shutil, "which", lambda _b: "/usr/bin/ffprobe")
    monkeypatch.setattr(subprocess, "check_output", lambda *_a, **_k: b" 42.25 \n")

    assert diar._probe_with_ffprobe("clip.wav") == pytest.approx(42.25)


def test_probe_with_ffprobe_returns_none_when_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No ffprobe on PATH means no duration."""
    monkeypatch.setattr(shutil, "which", lambda _b: None)

    assert diar._probe_with_ffprobe("clip.wav") is None


@pytest.mark.parametrize(
    "error",
    [
        OSError("boom"),
        subprocess.CalledProcessError(1, "ffprobe"),
        ValueError("not a float"),
    ],
)
def test_probe_with_ffprobe_survives_every_failure_mode(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """A crash, a non-zero exit, or unparsable output all yield None."""
    monkeypatch.setattr(shutil, "which", lambda _b: "/usr/bin/ffprobe")

    def _boom(*_a: object, **_k: object) -> None:
        raise error

    monkeypatch.setattr(subprocess, "check_output", _boom)

    assert diar._probe_with_ffprobe("clip.wav") is None


# --------------------------------------------------------------------------- #
# get_media_duration
# --------------------------------------------------------------------------- #
def test_get_media_duration_prefers_the_python_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the binding answers, ffprobe is never invoked."""
    called: list[str] = []

    def _record_ffprobe(_path: str) -> None:
        called.append("ffprobe")

    monkeypatch.setattr(diar, "_probe_with_ffmpeg_python", lambda _p: 10.0)
    monkeypatch.setattr(diar, "_probe_with_ffprobe", _record_ffprobe)

    assert diar.get_media_duration("clip.wav") == pytest.approx(10.0)
    assert called == []


def test_get_media_duration_falls_back_to_ffprobe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without the binding, the CLI is tried next."""
    monkeypatch.setattr(diar, "_probe_with_ffmpeg_python", lambda _p: None)
    monkeypatch.setattr(diar, "_probe_with_ffprobe", lambda _p: 20.0)

    assert diar.get_media_duration("clip.wav") == pytest.approx(20.0)


def test_get_media_duration_is_none_when_both_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unprobeable file is not an error - the caller drops the percentage."""
    monkeypatch.setattr(diar, "_probe_with_ffmpeg_python", lambda _p: None)
    monkeypatch.setattr(diar, "_probe_with_ffprobe", lambda _p: None)
