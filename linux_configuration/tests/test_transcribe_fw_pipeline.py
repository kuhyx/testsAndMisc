"""Tests for transcribe_fw's argument parsing, model loading and pipeline.

``main`` is the entry point transcribe.sh calls, and its return codes are the
contract: 2 for a missing dependency or a missing input file, 0 on success.
faster_whisper is reached only through ``_try_import``, so no ML package is
needed here; the output writers are patched at the module boundary.
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


# --------------------------------------------------------------------------- #
# The optional-dependency import seam
# --------------------------------------------------------------------------- #
def test_try_import_returns_the_module_when_present() -> None:
    """The seam every other test patches works against a real module."""
    assert fw._try_import("json") is not None


def test_try_import_returns_none_for_a_missing_module() -> None:
    """A missing faster_whisper is None, which main() turns into exit 2."""
    assert fw._try_import("no_such_module_anywhere_12345") is None


# --------------------------------------------------------------------------- #
# _parse_args
# --------------------------------------------------------------------------- #
def test_parse_args_defaults_come_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """transcribe.sh configures the run through FW_* variables."""
    monkeypatch.setenv("FW_MODEL", "small")
    monkeypatch.setenv("FW_DEVICE", "cuda")
    monkeypatch.setenv("FW_COMPUTE", "int8")
    monkeypatch.setenv("FW_NUM_SPEAKERS", "4")
    monkeypatch.setattr(sys, "argv", ["transcribe_fw.py", "audio.wav"])

    args = fw._parse_args()

    assert args.model == "small"
    assert args.device == "cuda"
    assert args.compute_type == "int8"
    assert args.num_speakers == 4


def test_parse_args_command_line_beats_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit flag overrides the environment default."""
    monkeypatch.setenv("FW_MODEL", "small")
    monkeypatch.setattr(
        sys, "argv", ["transcribe_fw.py", "audio.wav", "--model", "large-v3"]
    )

    assert fw._parse_args().model == "large-v3"


def test_parse_args_rejects_an_unknown_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The device choices guard against a typo silently running on CPU."""
    monkeypatch.setattr(
        sys, "argv", ["transcribe_fw.py", "audio.wav", "--device", "tpu"]
    )

    with pytest.raises(SystemExit):
        fw._parse_args()


# --------------------------------------------------------------------------- #
# _load_whisper_model
# --------------------------------------------------------------------------- #
def test_load_whisper_model_uses_a_local_directory_as_is(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A model given as an existing directory is not downloaded again."""
    whisper = _Whisper()
    downloads: list[str] = []
    monkeypatch.setattr(fw, "download_model_with_progress", downloads.append)
    args = type("A", (), {"model": str(tmp_path)})()

    fw._load_whisper_model(whisper, args, "cpu", "float32")

    assert downloads == []
    assert whisper.calls == [
        {"path": str(tmp_path), "device": "cpu", "compute_type": "float32"}
    ]


def test_load_whisper_model_downloads_a_named_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A model name that is not a directory is fetched first."""
    whisper = _Whisper()
    monkeypatch.setattr(
        fw, "download_model_with_progress", lambda _name: "/cache/large-v3"
    )
    args = type("A", (), {"model": "large-v3"})()

    fw._load_whisper_model(whisper, args, "cuda", "float16")

    assert whisper.calls[0]["path"] == "/cache/large-v3"


# --------------------------------------------------------------------------- #
# _write_diarized_outputs
# --------------------------------------------------------------------------- #
def test_write_diarized_outputs_is_skipped_unless_requested(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Without --diarize the diarization pipeline is never entered."""
    called: list[str] = []
    monkeypatch.setattr(fw, "diarize_segments", lambda *_a, **_k: called.append("x"))
    args = type("A", (), {"diarize": False, "num_speakers": 2})()

    fw._write_diarized_outputs(args, "in.wav", tmp_path, "base", [])

    assert called == []


def test_write_diarized_outputs_writes_three_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A successful diarization writes .diar.txt, .diar.srt and .rttm."""
    segments = [_Segment(1.0), _Segment(2.0)]
    monkeypatch.setattr(fw, "diarize_segments", lambda *_a, **_k: ["A", "B"])
    written: list[str] = []
    for name in ("write_srt_with_speakers", "write_txt_with_speakers"):
        monkeypatch.setattr(fw, name, lambda _s, _l, path: written.append(path))
    monkeypatch.setattr(
        fw, "write_rttm", lambda _s, _l, path, **_k: written.append(path)
    )
    args = type("A", (), {"diarize": True, "num_speakers": 2})()

    fw._write_diarized_outputs(args, "in.wav", tmp_path, "base", segments)

    assert sorted(str(p).rpartition(".")[2] for p in written) == [
        "rttm",
        "srt",
        "txt",
    ]


def test_write_diarized_outputs_warns_on_mismatched_labels(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Fewer labels than segments falls back to plain output with a warning."""
    monkeypatch.setattr(fw, "diarize_segments", lambda *_a, **_k: ["only-one"])
    args = type("A", (), {"diarize": True, "num_speakers": 2})()

    with caplog.at_level(logging.WARNING):
        fw._write_diarized_outputs(
            args, "in.wav", tmp_path, "base", [_Segment(1.0), _Segment(2.0)]
        )

    assert "writing plain" in caplog.text


def test_write_diarized_outputs_warns_when_diarization_returns_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A failed diarization is a warning, not a crash."""
    monkeypatch.setattr(fw, "diarize_segments", lambda *_a, **_k: None)
    args = type("A", (), {"diarize": True, "num_speakers": 2})()

    with caplog.at_level(logging.WARNING):
        fw._write_diarized_outputs(args, "in.wav", tmp_path, "base", [_Segment(1.0)])

    assert "writing plain" in caplog.text
