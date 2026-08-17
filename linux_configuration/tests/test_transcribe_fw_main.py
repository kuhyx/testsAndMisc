"""Tests for transcribe_fw's ``main`` entry point.

transcribe.sh calls this and branches on the return code: 2 for a missing
dependency or a missing input file, 0 on success. faster_whisper is reached
only through ``_try_import``, so no ML package is needed here.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import pytest
import transcribe_fw as fw

if TYPE_CHECKING:
    from pathlib import Path

_EXIT_FAILURE = 2


class _Segment:
    """A faster_whisper segment, which the code only reads ``end`` from."""

    def __init__(self, end: float) -> None:
        self.end = end
        self.text = "hello"
        self.start = 0.0


class _Model:
    """A WhisperModel double yielding one fixed segment."""

    def transcribe(self, _inp: str, **_kw: object) -> tuple[object, object]:
        """Return one segment and a language-detection info object."""
        info = type("I", (), {"language": "en", "language_probability": 0.99})()
        return iter([_Segment(1.0)]), info


class _Whisper:
    """A faster_whisper module double recording model construction."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def _construct(self, path: str, **kwargs: object) -> _Model:
        self.calls.append({"path": path, **kwargs})
        return _Model()

    def __getattr__(self, attr: str) -> object:
        if attr == "WhisperModel":
            return self._construct
        raise AttributeError(attr)


@pytest.fixture
def recorded_writes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Record output writes instead of performing them."""
    written: list[tuple[str, str]] = []
    for name in ("write_txt", "write_srt"):
        monkeypatch.setattr(
            fw,
            name,
            lambda _segs, path, _n=name: written.append((_n, path)),
        )
    return written


def test_main_exits_2_without_faster_whisper(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The missing-dependency path is what transcribe.sh installs against."""
    monkeypatch.setattr(sys, "argv", ["transcribe_fw.py", "audio.wav"])
    monkeypatch.setattr(fw, "_try_import", lambda _n: None)

    with caplog.at_level(logging.ERROR):
        assert fw.main() == _EXIT_FAILURE

    assert "not installed" in caplog.text


def test_main_exits_2_for_a_missing_input_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A path that does not exist is reported before any model is loaded."""
    missing = tmp_path / "nope.wav"
    monkeypatch.setattr(sys, "argv", ["transcribe_fw.py", str(missing)])
    monkeypatch.setattr(fw, "_try_import", lambda _n: _Whisper())

    with caplog.at_level(logging.ERROR):
        assert fw.main() == _EXIT_FAILURE

    assert "not found" in caplog.text


def test_main_transcribes_and_writes_both_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    recorded_writes: list[tuple[str, str]],
) -> None:
    """The happy path writes a .txt and a .srt beside the input."""
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"RIFF")
    monkeypatch.setattr(sys, "argv", ["transcribe_fw.py", str(audio)])
    monkeypatch.setattr(fw, "_try_import", lambda _n: _Whisper())
    monkeypatch.setattr(fw, "download_model_with_progress", lambda _n: "/cache/m")
    monkeypatch.setattr(fw, "get_media_duration", lambda _i: 10.0)

    assert fw.main() == 0

    kinds = sorted(kind for kind, _ in recorded_writes)
    assert kinds == ["write_srt", "write_txt"]
    assert all(str(tmp_path) in path for _, path in recorded_writes)


def test_main_honours_an_explicit_outdir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    recorded_writes: list[tuple[str, str]],
) -> None:
    """--outdir redirects the outputs and creates the directory."""
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"RIFF")
    outdir = tmp_path / "out" / "nested"
    monkeypatch.setattr(
        sys, "argv", ["transcribe_fw.py", str(audio), "--outdir", str(outdir)]
    )
    monkeypatch.setattr(fw, "_try_import", lambda _n: _Whisper())
    monkeypatch.setattr(fw, "download_model_with_progress", lambda _n: "/cache/m")
    monkeypatch.setattr(fw, "get_media_duration", lambda _i: None)

    assert fw.main() == 0
    assert outdir.is_dir()
    assert all(str(outdir) in path for _, path in recorded_writes)


def test_main_continues_when_the_duration_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    recorded_writes: list[tuple[str, str]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An unprobeable media duration only costs the percentage display."""
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"RIFF")
    monkeypatch.setattr(sys, "argv", ["transcribe_fw.py", str(audio)])
    monkeypatch.setattr(fw, "_try_import", lambda _n: _Whisper())
    monkeypatch.setattr(fw, "download_model_with_progress", lambda _n: "/cache/m")
    monkeypatch.setattr(fw, "get_media_duration", lambda _i: None)

    with caplog.at_level(logging.INFO):
        assert fw.main() == 0

    assert "Media duration" not in caplog.text
