"""Tests for speaker-embedding extraction and the diarize_segments pipeline.

torch and speechbrain are never installed in CI and are reached only through
``_try_import``, so both are doubled here. The embedding double returns a
direction per segment, which lets the clustering downstream be real numpy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import _transcribe_diarize as diar
import numpy as np

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    import numpy.typing as npt


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
# _extract_embeddings
# --------------------------------------------------------------------------- #
def test_extract_embeddings_returns_one_vector_per_segment() -> None:
    """Every segment yields exactly one embedding, in order."""
    wav = np.zeros(_SR_16K * 10, dtype=np.float32)
    segments = [_Segment(0.0, 1.0), _Segment(1.0, 2.0), _Segment(2.0, 3.0)]
    classifier = _Classifier()

    embeddings = diar._extract_embeddings(segments, wav, classifier, _Torch())

    assert len(embeddings) == 3
    assert all(e.dtype == np.float32 for e in embeddings)


def test_extract_embeddings_pads_around_each_segment() -> None:
    """A 50 ms pad each side widens the slice beyond the segment itself."""
    wav = np.zeros(_SR_16K * 10, dtype=np.float32)
    classifier = _Classifier()

    diar._extract_embeddings([_Segment(1.0, 2.0)], wav, classifier, _Torch())

    # 1 s of audio plus 0.05 s of padding at each end.
    assert classifier.seen == [int(_SR_16K * 1.1)]


def test_extract_embeddings_enforces_a_minimum_slice() -> None:
    """A very short segment is widened so the encoder has enough samples."""
    wav = np.zeros(_SR_16K * 10, dtype=np.float32)
    classifier = _Classifier()

    diar._extract_embeddings([_Segment(1.0, 1.001)], wav, classifier, _Torch())

    assert classifier.seen[0] >= diar._MIN_SAMPLES_DIAR


def test_extract_embeddings_handles_a_segment_with_no_duration() -> None:
    """An end at or before the start is given a default 0.2 s span."""
    wav = np.zeros(_SR_16K * 10, dtype=np.float32)
    classifier = _Classifier()

    diar._extract_embeddings([_Segment(5.0, 5.0)], wav, classifier, _Torch())

    assert classifier.seen[0] >= diar._MIN_SAMPLES_DIAR


def test_extract_embeddings_treats_missing_times_as_zero() -> None:
    """A segment with None timings starts at the beginning rather than failing."""
    wav = np.zeros(_SR_16K * 10, dtype=np.float32)
    classifier = _Classifier()

    embeddings = diar._extract_embeddings(
        [_Segment(None, None)], wav, classifier, _Torch()
    )

    assert len(embeddings) == 1


def test_extract_embeddings_clamps_to_the_end_of_the_audio() -> None:
    """A segment running past the recording is clipped to what exists."""
    wav = np.zeros(_SR_16K, dtype=np.float32)
    classifier = _Classifier()

    diar._extract_embeddings([_Segment(0.5, 100.0)], wav, classifier, _Torch())

    assert classifier.seen[0] <= len(wav)


def test_extract_embeddings_widens_a_slice_below_the_minimum() -> None:
    """A segment shorter than the padding still reaches the minimum width.

    The padded slice of a 1 ms segment is 1600 samples exactly at the start of
    the file, so this uses a segment at offset 0 where only one side is padded
    and the widening branch is the one that has to fire.
    """
    wav = np.zeros(_SR_16K * 10, dtype=np.float32)
    classifier = _Classifier()

    diar._extract_embeddings([_Segment(0.0, 0.001)], wav, classifier, _Torch())

    assert classifier.seen[0] == diar._MIN_SAMPLES_DIAR
