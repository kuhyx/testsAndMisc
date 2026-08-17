"""Tests for transcribe_fw's progress reporting and device resolution.

``_format_progress_line`` is the piece a user actually watches during a long
transcription, and it is pure: given the seconds processed and the media
duration it returns a string. That makes the percentage, the ETA and the
suppression of a nonsensical ETA all directly assertable.
"""

from __future__ import annotations

import argparse
import logging
from typing import TYPE_CHECKING, Any

import _transcribe_progress as progress
import pytest
import transcribe_fw as fw

if TYPE_CHECKING:
    from collections.abc import Iterator


def _args(**overrides: object) -> argparse.Namespace:
    """A parsed-argument namespace with the defaults the CLI would supply."""
    defaults: dict[str, object] = {
        "device": "auto",
        "compute_type": "auto",
        "language": None,
        "no_progress": False,
        "diarize": False,
        "num_speakers": 2,
    }
    return argparse.Namespace(**{**defaults, **overrides})


class _Segment:
    """A faster_whisper segment, which the code only reads ``end`` from."""

    def __init__(self, end: float | None) -> None:
        self.end = end


class _Model:
    """A WhisperModel double yielding fixed segments."""

    def __init__(self, segments: list[_Segment]) -> None:
        self._segments = segments
        self.calls: list[dict[str, object]] = []

    def transcribe(self, inp: str, **kwargs: object) -> tuple[Iterator[Any], object]:
        """Return an iterator of segments plus an info object."""
        self.calls.append({"input": inp, **kwargs})
        info = argparse.Namespace(language="en", language_probability=0.99)
        return iter(self._segments), info


# --------------------------------------------------------------------------- #
# _resolve_device_and_compute
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("device", "compute", "expected"),
    [
        ("auto", "auto", ("cpu", "float32")),
        ("cuda", "auto", ("cuda", "float16")),
        ("cpu", "auto", ("cpu", "float32")),
        ("cuda", "int8", ("cuda", "int8")),
        ("cpu", "float16", ("cpu", "float16")),
    ],
)
def test_resolve_device_and_compute(
    device: str, compute: str, expected: tuple[str, str]
) -> None:
    """auto resolves to CPU, and the compute type follows the device."""
    resolved = fw._resolve_device_and_compute(
        _args(device=device, compute_type=compute)
    )

    assert resolved == expected


# --------------------------------------------------------------------------- #
# _format_progress_line
# --------------------------------------------------------------------------- #
def test_format_progress_line_reports_percent_and_eta() -> None:
    """Halfway through at 1x speed, the ETA equals the time already spent."""
    line = progress._format_progress_line(
        processed=50.0, total_duration=100.0, now=50.0, start_ts=0.0
    )

    assert "50.0%" in line
    assert "ETA" in line
    assert "00:00:50" in line


def test_format_progress_line_clamps_percent_to_100() -> None:
    """A segment ending past the reported duration cannot show 110%."""
    line = progress._format_progress_line(
        processed=110.0, total_duration=100.0, now=10.0, start_ts=0.0
    )

    assert "100.0%" in line


def test_format_progress_line_omits_an_absurd_eta() -> None:
    """An ETA of more than a day is suppressed rather than shown."""
    line = progress._format_progress_line(
        processed=0.001, total_duration=1_000_000.0, now=10.0, start_ts=0.0
    )

    assert "ETA" not in line


def test_format_progress_line_omits_eta_before_any_progress() -> None:
    """With nothing processed there is no rate to extrapolate from."""
    line = progress._format_progress_line(
        processed=0.0, total_duration=100.0, now=1.0, start_ts=0.0
    )

    assert "ETA" not in line
    assert "0.0%" in line


@pytest.mark.parametrize("duration", [None, 0.0])
def test_format_progress_line_falls_back_without_a_duration(
    duration: float | None,
) -> None:
    """An unknown media duration degrades to reporting elapsed audio only."""
    line = progress._format_progress_line(
        processed=42.0, total_duration=duration, now=10.0, start_ts=0.0
    )

    assert "processed" in line
    assert "%" not in line


# --------------------------------------------------------------------------- #
# _run_progress_loop
# --------------------------------------------------------------------------- #
def test_run_progress_loop_collects_every_segment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All segments are collected and the info object is passed through."""
    model = _Model([_Segment(1.0), _Segment(2.0), _Segment(3.0)])
    monkeypatch.setattr(progress.sys.stderr, "isatty", lambda: False)

    collected, info = progress._run_progress_loop(_args(), model, "in.wav", 3.0)

    assert len(collected) == 3
    assert info.language == "en"
    assert model.calls == [{"input": "in.wav", "language": None}]


def test_run_progress_loop_tolerates_a_segment_without_an_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A segment missing its end time does not break progress tracking."""
    model = _Model([_Segment(None), _Segment(5.0)])
    monkeypatch.setattr(progress.sys.stderr, "isatty", lambda: False)

    collected, _ = progress._run_progress_loop(_args(), model, "in.wav", 10.0)

    assert len(collected) == 2


def test_run_progress_loop_stays_silent_with_no_progress(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """--no-progress suppresses the progress lines entirely."""
    model = _Model([_Segment(1.0), _Segment(2.0)])
    monkeypatch.setattr(progress.sys.stderr, "isatty", lambda: False)

    with caplog.at_level(logging.INFO):
        progress._run_progress_loop(_args(no_progress=True), model, "in.wav", 2.0)

    assert "[PROGRESS]" not in caplog.text


def test_run_progress_loop_emits_progress_on_a_tty(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """On a terminal every segment redraws the line."""
    model = _Model([_Segment(1.0), _Segment(2.0)])
    monkeypatch.setattr(progress.sys.stderr, "isatty", lambda: True)

    with caplog.at_level(logging.INFO):
        progress._run_progress_loop(_args(), model, "in.wav", 2.0)

    assert "[PROGRESS]" in caplog.text


def test_run_progress_loop_throttles_when_not_a_tty(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Piped output is throttled, so a long run does not flood the log."""
    model = _Model([_Segment(float(i)) for i in range(10)])
    monkeypatch.setattr(progress.sys.stderr, "isatty", lambda: False)
    clock = iter([100.0, *[100.0] * 40])
    monkeypatch.setattr(progress.time, "time", lambda: next(clock))

    with caplog.at_level(logging.INFO):
        progress._run_progress_loop(_args(), model, "in.wav", 10.0)

    # Every timestamp is identical, so after the first line the throttle
    # window never elapses and no further progress lines are emitted.
    assert caplog.text.count("[PROGRESS]") == 1
