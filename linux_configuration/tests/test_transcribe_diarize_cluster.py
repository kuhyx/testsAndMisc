"""Tests for the resampling and cosine k-means used to label speakers.

numpy is a declared dependency (meta/requirements.txt), so these run against
the real library rather than a double: clustering that "works" against a
mocked numpy would prove nothing about whether two speakers get two labels.
"""

from __future__ import annotations

import _transcribe_cluster as diar
import numpy as np
import pytest

_SR_16K = 16000
_TWO_SPEAKERS = 2


# --------------------------------------------------------------------------- #
# _resample_linear
# --------------------------------------------------------------------------- #
def test_resample_linear_returns_the_input_unchanged_at_the_same_rate() -> None:
    """Resampling to the rate it already has is a no-op."""
    audio = np.linspace(0.0, 1.0, num=100, dtype=np.float32)

    result = diar._resample_linear(audio, _SR_16K, _SR_16K)

    assert result is audio


def test_resample_linear_downsamples_to_the_expected_length() -> None:
    """Halving the rate halves the sample count."""
    audio = np.linspace(0.0, 1.0, num=1000, dtype=np.float32)

    result = diar._resample_linear(audio, 32000, _SR_16K)

    assert result.shape[0] == 500
    assert result.dtype == np.float32


def test_resample_linear_upsamples_to_the_expected_length() -> None:
    """Doubling the rate doubles the sample count."""
    audio = np.linspace(0.0, 1.0, num=100, dtype=np.float32)

    assert diar._resample_linear(audio, 8000, _SR_16K).shape[0] == 200


def test_resample_linear_preserves_a_constant_signal() -> None:
    """Linear interpolation of a flat signal stays flat."""
    audio = np.full(100, 0.5, dtype=np.float32)

    result = diar._resample_linear(audio, 8000, _SR_16K)

    assert np.allclose(result, 0.5)


def test_resample_linear_never_returns_an_empty_array() -> None:
    """An extreme downsample still yields at least one sample."""
    audio = np.linspace(0.0, 1.0, num=10, dtype=np.float32)

    assert diar._resample_linear(audio, 48000, 1).shape[0] >= 1


def test_resample_linear_requires_numpy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without numpy the failure is explicit rather than an AttributeError."""
    monkeypatch.setattr(diar, "_try_import", lambda _n: None)

    with pytest.raises(RuntimeError, match="numpy is required"):
        diar._resample_linear(np.zeros(10, dtype=np.float32), 8000, _SR_16K)


# --------------------------------------------------------------------------- #
# _kmeans_cosine
# --------------------------------------------------------------------------- #
def test_kmeans_cosine_separates_two_opposed_clusters() -> None:
    """Embeddings pointing in two directions get two distinct labels."""
    rng = np.random.default_rng(0)
    group_a = np.tile([1.0, 0.0], (10, 1)) + rng.normal(0, 0.01, (10, 2))
    group_b = np.tile([0.0, 1.0], (10, 1)) + rng.normal(0, 0.01, (10, 2))
    embeddings = list(np.vstack([group_a, group_b]).astype(np.float32))

    labels = diar._kmeans_cosine(embeddings, k=_TWO_SPEAKERS)

    assert len(set(labels.tolist())) == _TWO_SPEAKERS
    assert len(set(labels[:10].tolist())) == 1
    assert len(set(labels[10:].tolist())) == 1
    assert labels[0] != labels[10]


def test_kmeans_cosine_ignores_magnitude() -> None:
    """Cosine clustering keys on direction, so scale must not matter."""
    embeddings = [
        np.array([1.0, 0.0], dtype=np.float32),
        np.array([100.0, 0.0], dtype=np.float32),
        np.array([0.0, 1.0], dtype=np.float32),
        np.array([0.0, 50.0], dtype=np.float32),
    ]

    labels = diar._kmeans_cosine(embeddings, k=_TWO_SPEAKERS).tolist()

    assert labels[0] == labels[1]
    assert labels[2] == labels[3]
    assert labels[0] != labels[2]


def test_kmeans_cosine_is_deterministic_for_a_fixed_seed() -> None:
    """The same input twice gives the same labels, so runs are reproducible."""
    rng = np.random.default_rng(1)
    embeddings = list(rng.normal(size=(20, 8)).astype(np.float32))

    first = diar._kmeans_cosine(embeddings, k=3, seed=7).tolist()
    second = diar._kmeans_cosine(embeddings, k=3, seed=7).tolist()

    assert first == second


def test_kmeans_cosine_returns_empty_for_no_embeddings() -> None:
    """A file with no segments produces no labels."""
    assert diar._kmeans_cosine([], k=_TWO_SPEAKERS).shape == (0,)


def test_kmeans_cosine_returns_empty_for_the_wrong_dimensionality() -> None:
    """A 1-D input is not a stack of embeddings and is rejected."""
    assert diar._kmeans_cosine([1.0, 2.0, 3.0], k=_TWO_SPEAKERS).shape == (0,)


def test_kmeans_cosine_pads_when_asked_for_more_speakers_than_segments() -> None:
    """Requesting 5 speakers from 2 segments still returns one label each."""
    embeddings = [
        np.array([1.0, 0.0], dtype=np.float32),
        np.array([0.0, 1.0], dtype=np.float32),
    ]

    labels = diar._kmeans_cosine(embeddings, k=5)

    assert labels.shape == (2,)


def test_kmeans_cosine_labels_every_segment_with_one_speaker() -> None:
    """k=1 assigns every segment the same label."""
    rng = np.random.default_rng(2)
    embeddings = list(rng.normal(size=(6, 4)).astype(np.float32))

    assert set(diar._kmeans_cosine(embeddings, k=1).tolist()) == {0}


def test_kmeans_cosine_requires_numpy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without numpy the failure is explicit."""
    monkeypatch.setattr(diar, "_try_import", lambda _n: None)

    with pytest.raises(RuntimeError, match="numpy is required"):
        diar._kmeans_cosine([np.zeros(4, dtype=np.float32)], k=1)


# --------------------------------------------------------------------------- #
# _run_kmeans_iterations
# --------------------------------------------------------------------------- #
def test_run_kmeans_iterations_converges_and_stops_early() -> None:
    """Already-separated data converges on the first pass and breaks out."""
    features = np.array(
        [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]], dtype=np.float32
    )
    centroids = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)

    labels = diar._run_kmeans_iterations(np, features, centroids, 2, 50)

    assert labels.tolist() == [0, 0, 1, 1]


def test_run_kmeans_iterations_keeps_an_empty_cluster_centroid() -> None:
    """A centroid that attracts no points is carried forward, not zeroed."""
    features = np.array([[1.0, 0.0], [1.0, 0.0]], dtype=np.float32)
    centroids = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)

    labels = diar._run_kmeans_iterations(np, features, centroids, 2, 5)

    assert labels.tolist() == [0, 0]


def test_run_kmeans_iterations_returns_none_when_asked_for_no_iterations() -> None:
    """A zero-iteration run never assigns labels; the loop body is skipped."""
    features = np.array([[1.0, 0.0]], dtype=np.float32)
    centroids = np.array([[1.0, 0.0]], dtype=np.float32)

    assert diar._run_kmeans_iterations(np, features, centroids, 1, 0) is None
