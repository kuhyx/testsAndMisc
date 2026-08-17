"""Tests for the diarize_segments pipeline end to end.

torch and speechbrain are never installed in CI and are reached only through
``_try_import``, so both are doubled here. The embedding double returns a
direction per segment, which lets the clustering downstream be real numpy.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import _transcribe_diarize as diar
import numpy as np

if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from pathlib import Path

    import numpy.typing as npt
    import pytest


_SR_16K = 16000
_TWO_SPEAKERS = 2


class _Segment:
    """A transcription segment, of which only start and end are read."""

    def __init__(self, start: float | None, end: float | None) -> None:
        self.start = start
        self.end = end


class _Tensor:
    """A torch tensor double carrying the slice it was built from."""

    def __init__(self, data: npt.NDArray[np.float32]) -> None:
        self.data = data

    def unsqueeze(self, _dim: int) -> _Tensor:
        """torch tensors are reshaped before batching; the data is unchanged."""
        return self


class _Embedding:
    """The chain classifier.encode_batch(...).squeeze().squeeze().cpu().numpy()."""

    def __init__(self, vector: npt.NDArray[np.float32]) -> None:
        self._vector = vector

    def squeeze(self, _dim: int) -> _Embedding:
        return self

    def cpu(self) -> _Embedding:
        return self

    def numpy(self) -> npt.NDArray[np.float32]:
        """Return the embedding as the array the caller will cast."""
        return self._vector


class _Torch:
    """A torch module double providing tensor() and no_grad()."""

    def tensor(self, data: npt.NDArray[np.float32]) -> _Tensor:
        """Wrap a slice of audio the way torch.tensor would."""
        return _Tensor(data)

    def no_grad(self) -> AbstractContextManager[None]:
        """Return a context manager, as torch.no_grad() does."""

        class _Ctx:
            def __enter__(self) -> None:
                return None

            def __exit__(self, *_a: object) -> None:
                return None

        return _Ctx()


class _Classifier:
    """A speaker classifier double: one direction per call, recorded."""

    def __init__(self, vectors: list[npt.NDArray[np.float32]] | None = None) -> None:
        self.seen: list[int] = []
        self._vectors = vectors
        self._calls = 0

    def encode_batch(self, tensor: _Tensor) -> _Embedding:
        """Record the sample count and return the next canned embedding."""
        self.seen.append(len(tensor.data))
        if self._vectors is not None:
            vector = self._vectors[self._calls % len(self._vectors)]
        else:
            vector = np.array([1.0, 0.0], dtype=np.float32)
        self._calls += 1
        return _Embedding(vector)


def _importer(available: dict[str, object]) -> object:
    """Return a _try_import double resolving the named modules, plus numpy.

    numpy is a real declared dependency and the resampling and clustering
    code fetches it through the same seam, so it is always passed through -
    stubbing it would make the clustering assertions meaningless.
    """

    def _try(name: str) -> object | None:
        if name == "numpy":
            return np
        return available.get(name)

    return _try


# --------------------------------------------------------------------------- #
# diarize_segments
# --------------------------------------------------------------------------- #
def test_diarize_segments_labels_two_speakers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole pipeline turns four segments into two speaker labels."""
    wav = np.zeros(_SR_16K * 10, dtype=np.float32)
    monkeypatch.setattr(diar, "_try_import", _importer({"torch": _Torch()}))
    monkeypatch.setattr(diar, "_load_audio", lambda _p: (wav, _SR_16K, None))
    monkeypatch.setattr(
        diar,
        "_load_speaker_classifier",
        lambda _t: _Classifier(
            [
                np.array([1.0, 0.0], dtype=np.float32),
                np.array([0.0, 1.0], dtype=np.float32),
            ]
        ),
    )
    segments = [_Segment(float(i), float(i) + 1.0) for i in range(4)]

    labels = diar.diarize_segments("clip.wav", segments, num_speakers=_TWO_SPEAKERS)

    assert labels is not None
    assert len(labels) == len(segments)
    assert len(set(labels)) == _TWO_SPEAKERS


def test_diarize_segments_warns_without_torch(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """No torch means speaker labels are skipped, not an error."""
    monkeypatch.setattr(diar, "_try_import", lambda _n: None)

    with caplog.at_level(logging.WARNING):
        assert diar.diarize_segments("clip.wav", [_Segment(0.0, 1.0)]) is None

    assert "skipping speaker labels" in caplog.text


def test_diarize_segments_gives_up_when_the_audio_cannot_be_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unreadable audio ends diarization before any model is loaded."""
    monkeypatch.setattr(diar, "_try_import", _importer({"torch": _Torch()}))
    monkeypatch.setattr(diar, "_load_audio", lambda _p: None)

    assert diar.diarize_segments("clip.wav", [_Segment(0.0, 1.0)]) is None


def test_diarize_segments_gives_up_without_a_classifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing embedding model ends diarization."""
    wav = np.zeros(_SR_16K, dtype=np.float32)
    monkeypatch.setattr(diar, "_try_import", _importer({"torch": _Torch()}))
    monkeypatch.setattr(diar, "_load_audio", lambda _p: (wav, _SR_16K, None))
    monkeypatch.setattr(diar, "_load_speaker_classifier", lambda _t: None)

    assert diar.diarize_segments("clip.wav", [_Segment(0.0, 1.0)]) is None


def test_diarize_segments_returns_none_for_no_segments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No segments means no embeddings and so no labels."""
    wav = np.zeros(_SR_16K, dtype=np.float32)
    monkeypatch.setattr(diar, "_try_import", _importer({"torch": _Torch()}))
    monkeypatch.setattr(diar, "_load_audio", lambda _p: (wav, _SR_16K, None))
    monkeypatch.setattr(diar, "_load_speaker_classifier", lambda _t: _Classifier())

    assert diar.diarize_segments("clip.wav", []) is None


def test_diarize_segments_downmixes_stereo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 2-D stereo array is averaged to mono before resampling."""
    stereo = np.zeros((_SR_16K * 2, 2), dtype=np.float32)
    monkeypatch.setattr(diar, "_try_import", _importer({"torch": _Torch()}))
    monkeypatch.setattr(diar, "_load_audio", lambda _p: (stereo, _SR_16K, None))
    monkeypatch.setattr(diar, "_load_speaker_classifier", lambda _t: _Classifier())

    labels = diar.diarize_segments("clip.wav", [_Segment(0.0, 1.0)], num_speakers=1)

    assert labels == [0]


def test_diarize_segments_removes_the_temp_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A transcoded temp WAV is deleted once labels are computed."""
    temp = tmp_path / "scratch.wav"
    temp.write_bytes(b"RIFF")
    wav = np.zeros(_SR_16K * 2, dtype=np.float32)
    monkeypatch.setattr(diar, "_try_import", _importer({"torch": _Torch()}))
    monkeypatch.setattr(diar, "_load_audio", lambda _p: (wav, _SR_16K, str(temp)))
    monkeypatch.setattr(diar, "_load_speaker_classifier", lambda _t: _Classifier())

    diar.diarize_segments("clip.wav", [_Segment(0.0, 1.0)], num_speakers=1)

    assert not temp.exists()


def test_diarize_segments_treats_zero_speakers_as_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """num_speakers=0 would break k-means, so it is floored at one."""
    wav = np.zeros(_SR_16K * 2, dtype=np.float32)
    monkeypatch.setattr(diar, "_try_import", _importer({"torch": _Torch()}))
    monkeypatch.setattr(diar, "_load_audio", lambda _p: (wav, _SR_16K, None))
    monkeypatch.setattr(diar, "_load_speaker_classifier", lambda _t: _Classifier())

    assert diar.diarize_segments("clip.wav", [_Segment(0.0, 1.0)], num_speakers=0) == [
        0
    ]
