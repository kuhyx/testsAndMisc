"""Tests for loading the ECAPA speaker-embedding classifier.

speechbrain is never installed in CI and is reached only through
``_try_import``, so the encoder is doubled here. A model that fails to load
must clean up any temporary audio the caller had already transcoded.
"""

from __future__ import annotations

import logging
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


# --------------------------------------------------------------------------- #
# _load_speaker_classifier
# --------------------------------------------------------------------------- #
def test_load_speaker_classifier_returns_none_without_speechbrain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without speechbrain there is no embedding model to load."""
    monkeypatch.setattr(diar, "_try_import", lambda _n: None)

    assert diar._load_speaker_classifier(None) is None


def test_load_speaker_classifier_loads_the_ecapa_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ECAPA model is loaded on CPU into a cache directory."""
    recorded: dict[str, object] = {}

    class _Encoder:
        @staticmethod
        def from_hparams(**kwargs: object) -> str:
            recorded.update(kwargs)
            return "classifier"

    module = type("M", (), {"EncoderClassifier": _Encoder})()
    monkeypatch.setattr(
        diar, "_try_import", _importer({"speechbrain.inference": module})
    )

    assert diar._load_speaker_classifier(None) == "classifier"
    assert recorded["source"] == "speechbrain/spkrec-ecapa-voxceleb"
    assert recorded["run_opts"] == {"device": "cpu"}


@pytest.mark.parametrize("error", [OSError("no net"), RuntimeError("bad weights")])
def test_load_speaker_classifier_cleans_up_after_a_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    error: Exception,
) -> None:
    """A model that will not load warns and removes the temp audio."""
    temp = tmp_path / "scratch.wav"
    temp.write_bytes(b"RIFF")

    class _Encoder:
        @staticmethod
        def from_hparams(**_kwargs: object) -> None:
            raise error

    module = type("M", (), {"EncoderClassifier": _Encoder})()
    monkeypatch.setattr(
        diar, "_try_import", _importer({"speechbrain.inference": module})
    )

    with caplog.at_level(logging.WARNING):
        assert diar._load_speaker_classifier(str(temp)) is None

    assert "Could not load speaker embedding model" in caplog.text
    assert not temp.exists()
