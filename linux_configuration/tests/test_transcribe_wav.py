"""Tests for the stdlib-only sine WAV generator.

transcribe.sh uses it to produce a self-test tone without pulling in numpy or
any audio library, so this exercises the real file it writes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
import wave

import transcribe_helpers as helpers

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


# --------------------------------------------------------------------------- #
# generate_sine_wav
# --------------------------------------------------------------------------- #
def test_generate_sine_wav_writes_a_readable_mono_16k_wav(tmp_path: Path) -> None:
    """The generated file is a real WAV with the documented parameters."""
    out = tmp_path / "tone.wav"

    assert helpers.generate_sine_wav(str(out)) is True

    with wave.open(str(out)) as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert wf.getnframes() == 16000 * 3


def test_generate_sine_wav_honours_its_parameters(tmp_path: Path) -> None:
    """Duration and sample rate change the frame count accordingly."""
    out = tmp_path / "tone.wav"

    helpers.generate_sine_wav(str(out), duration=1, sample_rate=8000)

    with wave.open(str(out)) as wf:
        assert wf.getframerate() == 8000
        assert wf.getnframes() == 8000


def test_generate_sine_wav_reports_failure_on_an_unwritable_path(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """An OSError is logged and reported as False rather than raised."""
    unwritable = tmp_path / "missing-dir" / "tone.wav"

    with caplog.at_level(logging.ERROR):
        result = helpers.generate_sine_wav(str(unwritable))

    assert result is False
    assert "Failed to generate WAV" in caplog.text
