"""Tests for the ffmpeg transcode fallback, temp files, and audio loading.

``_load_audio`` reads with soundfile and, when that fails, transcodes through
ffmpeg to a temporary 16 kHz mono WAV. Both binaries are patched, so these
pass whether or not ffmpeg is installed on the machine running them.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import TYPE_CHECKING

import _transcribe_diarize as diar
import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _importer(available: dict[str, object]) -> object:
    """Return a _try_import double resolving only the named modules."""

    def _try(name: str) -> object | None:
        return available.get(name)

    return _try


def _only(name: str, module: object) -> object:
    """Return a _try_import double resolving exactly one module name."""

    def _try(requested: str) -> object | None:
        return module if requested == name else None

    return _try


# --------------------------------------------------------------------------- #
# _ffmpeg_transcode_to_wav16_mono / _cleanup_temp
# --------------------------------------------------------------------------- #
def test_transcode_returns_none_without_ffmpeg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No ffmpeg binary means no fallback transcode."""
    monkeypatch.setattr(shutil, "which", lambda _b: None)

    assert diar._ffmpeg_transcode_to_wav16_mono("clip.mp4") is None


def test_transcode_returns_the_temp_path_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful transcode hands back the temporary WAV path."""
    monkeypatch.setattr(shutil, "which", lambda _b: "/usr/bin/ffmpeg")
    commands: list[list[str]] = []

    def _record(cmd: list[str], **_kwargs: object) -> None:
        commands.append(cmd)

    monkeypatch.setattr(subprocess, "run", _record)

    result = diar._ffmpeg_transcode_to_wav16_mono("clip.mp4")

    assert result is not None
    assert result.endswith(".wav")
    assert "16000" in commands[0]
    assert "-ac" in commands[0]
    diar._cleanup_temp(result)


@pytest.mark.parametrize(
    "error", [OSError("boom"), subprocess.CalledProcessError(1, "ffmpeg")]
)
def test_transcode_cleans_up_after_a_failure(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """A failed transcode removes the temp file it had already created."""
    monkeypatch.setattr(shutil, "which", lambda _b: "/usr/bin/ffmpeg")
    removed: list[str] = []
    monkeypatch.setattr(diar.Path, "unlink", lambda self: removed.append(str(self)))

    def _boom(*_a: object, **_k: object) -> None:
        raise error

    monkeypatch.setattr(subprocess, "run", _boom)

    assert diar._ffmpeg_transcode_to_wav16_mono("clip.mp4") is None
    assert len(removed) == 1


def test_cleanup_temp_removes_an_existing_file(tmp_path: Path) -> None:
    """The temp WAV is deleted once diarization is done with it."""
    victim = tmp_path / "scratch.wav"
    victim.write_bytes(b"RIFF")

    diar._cleanup_temp(str(victim))

    assert not victim.exists()


def test_cleanup_temp_ignores_none() -> None:
    """No temp file was created, so there is nothing to remove."""
    diar._cleanup_temp(None)


def test_cleanup_temp_survives_an_already_deleted_file(tmp_path: Path) -> None:
    """A file removed by something else is not an error."""
    diar._cleanup_temp(str(tmp_path / "never-existed.wav"))


def test_load_audio_returns_none_without_soundfile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Diarization needs soundfile; without it there is no audio to read."""
    monkeypatch.setattr(diar, "_try_import", lambda _n: None)

    assert diar._load_audio("clip.wav") is None


def test_load_audio_warns_when_the_ffmpeg_fallback_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """An unreadable file with no transcode path warns and gives up."""

    class _Sf:
        def read(self, *_a: object, **_k: object) -> None:
            msg = "unsupported format"
            raise OSError(msg)

    monkeypatch.setattr(diar, "_try_import", _only("soundfile", _Sf()))
    monkeypatch.setattr(diar, "_ffmpeg_transcode_to_wav16_mono", lambda _p: None)

    with caplog.at_level(logging.WARNING):
        assert diar._load_audio("clip.mp4") is None

    assert "no ffmpeg fallback" in caplog.text


class _SfFailingThenOk:
    """A soundfile double that fails on the original and reads the transcode."""

    def __init__(self, *, second_fails: bool = False) -> None:
        self.calls: list[str] = []
        self._second_fails = second_fails

    def read(self, path: str, **_kwargs: object) -> tuple[str, int]:
        """Fail for the source file; succeed (or not) for the transcode."""
        self.calls.append(path)
        if len(self.calls) == 1:
            msg = "unsupported format"
            raise OSError(msg)
        if self._second_fails:
            msg = "still unreadable"
            raise OSError(msg)
        return "wav-data", 16000


def test_load_audio_falls_back_to_a_transcoded_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An unreadable container is transcoded, then read from the temp WAV."""
    scratch = str(tmp_path / "scratch.wav")
    sf = _SfFailingThenOk()
    monkeypatch.setattr(diar, "_try_import", _only("soundfile", sf))
    monkeypatch.setattr(diar, "_ffmpeg_transcode_to_wav16_mono", lambda _p: scratch)

    result = diar._load_audio("clip.mp4")

    assert result == ("wav-data", 16000, scratch)
    assert sf.calls == ["clip.mp4", scratch]


def test_load_audio_cleans_up_when_the_transcode_is_also_unreadable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """If even the transcode cannot be read, the temp file is removed."""
    temp = tmp_path / "scratch.wav"
    temp.write_bytes(b"RIFF")
    monkeypatch.setattr(
        diar, "_try_import", _only("soundfile", _SfFailingThenOk(second_fails=True))
    )
    monkeypatch.setattr(diar, "_ffmpeg_transcode_to_wav16_mono", lambda _p: str(temp))

    with caplog.at_level(logging.WARNING):
        assert diar._load_audio("clip.mp4") is None

    assert "Could not read transcoded audio" in caplog.text
    assert not temp.exists()


def test_load_audio_returns_the_source_when_it_reads_cleanly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A readable file needs no transcode and reports no temp path."""

    class _Sf:
        def read(self, _path: str, **_kwargs: object) -> tuple[str, int]:
            return "wav-data", 44100

    monkeypatch.setattr(diar, "_try_import", _only("soundfile", _Sf()))

    assert diar._load_audio("clip.wav") == ("wav-data", 44100, None)
