#!/usr/bin/env python3
"""Resampling and cosine k-means, the maths behind speaker labelling.

numpy is fetched through ``_try_import`` rather than imported at module
scope, so this file remains importable on a machine without it - which is
what lets the transcribe tools be unit-tested in CI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from _transcribe_media import _try_import

if TYPE_CHECKING:
    import types

    import numpy as np
    import numpy.typing as npt

_NDIM_2D = 2


def _resample_linear(
    x: npt.NDArray[np.float32],
    src_sr: int,
    tgt_sr: int,
) -> npt.NDArray[np.float32]:
    """Linearly resample 1-D audio array."""
    np_mod = _try_import("numpy")
    if np_mod is None:
        msg = "numpy is required for resampling"
        raise RuntimeError(msg)

    if src_sr == tgt_sr:
        return x
    ratio = float(tgt_sr) / float(src_sr)
    n_out = max(1, round(x.shape[-1] * ratio))
    xp = np_mod.linspace(0.0, 1.0, num=x.shape[-1], endpoint=False)
    xq = np_mod.linspace(0.0, 1.0, num=n_out, endpoint=False)
    y = np_mod.interp(xq, xp, x.astype(np_mod.float32))
    return y.astype(np_mod.float32)


def _kmeans_cosine(
    embs: list[Any],
    k: int,
    iters: int = 50,
    seed: int = 0,
) -> npt.NDArray[np.int64]:
    """Cluster embeddings with cosine-similarity k-means."""
    np_mod = _try_import("numpy")
    if np_mod is None:
        msg = "numpy is required for clustering"
        raise RuntimeError(msg)

    rng = np_mod.random.default_rng(seed)
    features = np_mod.asarray(embs, dtype=np_mod.float32)
    if features.ndim != _NDIM_2D or features.shape[0] == 0:
        return np_mod.zeros((0,), dtype=np_mod.int64)
    features = features / (np_mod.linalg.norm(features, axis=1, keepdims=True) + 1e-8)
    idxs = rng.choice(
        features.shape[0],
        size=min(k, features.shape[0]),
        replace=False,
    )
    centroids = features[idxs]
    if centroids.shape[0] < k:
        pad = rng.standard_normal(
            size=(
                k - centroids.shape[0],
                features.shape[1],
            )
        ).astype(np_mod.float32)
        pad /= np_mod.linalg.norm(pad, axis=1, keepdims=True) + 1e-8
        centroids = np_mod.concatenate([centroids, pad], axis=0)
    return _run_kmeans_iterations(np_mod, features, centroids, k, iters)


def _run_kmeans_iterations(
    np_mod: types.ModuleType,
    features: npt.NDArray[np.float32],
    centroids: npt.NDArray[np.float32],
    k: int,
    iters: int,
) -> npt.NDArray[np.intp]:
    """Run k-means iteration loop and return labels."""
    labels: Any = None
    for _ in range(iters):
        sims = features @ centroids.T
        labels = sims.argmax(axis=1)
        new_c = np_mod.zeros_like(centroids)
        for j in range(k):
            sel = features[labels == j]
            if sel.shape[0] == 0:
                new_c[j] = centroids[j]
            else:
                v = sel.mean(axis=0)
                v /= np_mod.linalg.norm(v) + 1e-8
                new_c[j] = v
        if np_mod.allclose(new_c, centroids, atol=1e-4):
            break
        centroids = new_c
    return labels
