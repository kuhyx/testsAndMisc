#!/usr/bin/env python3
"""Speaker diarization: embed each segment, then cluster the embeddings.

Every heavy dependency (torch, speechbrain, soundfile) is reached through
``_try_import``, so a machine without them degrades to no speaker labels
rather than failing the transcription.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from _transcribe_cluster import _kmeans_cosine, _resample_linear
from _transcribe_media import (
    _cleanup_temp,
    _ffmpeg_transcode_to_wav16_mono,
    _try_import,
)

if TYPE_CHECKING:
    import types

    import numpy as np
    import numpy.typing as npt

logger = logging.getLogger(__name__)

_NDIM_2D = 2
_SAMPLE_RATE_16K = 16000
_MIN_SAMPLES_DIAR = 1600


def _load_audio(
    audio_path: str,
) -> tuple[Any, int, str | None] | None:
    """Load audio, with ffmpeg fallback.

    Returns (wav, sample_rate, temp_path) or None.
    """
    sf = _try_import("soundfile")
    if sf is None:
        return None

    try:
        wav, sr = sf.read(
            audio_path,
            dtype="float32",
            always_2d=False,
        )
    except OSError as exc:
        alt = _ffmpeg_transcode_to_wav16_mono(audio_path)
        if alt is None:
            logger.warning(
                "Could not read audio for diarization and no ffmpeg fallback: %s",
                exc,
            )
            return None
        try:
            wav, sr = sf.read(
                alt,
                dtype="float32",
                always_2d=False,
            )
        except OSError as exc2:
            logger.warning(
                "Could not read transcoded audio: %s",
                exc2,
            )
            _cleanup_temp(alt)
            return None
        return wav, sr, alt
    return wav, sr, None


def _load_speaker_classifier(
    temp_to_cleanup: str | None,
) -> object | None:
    """Load the ECAPA speaker embedding classifier."""
    sb_inf = _try_import("speechbrain.inference")
    if sb_inf is None:
        return None
    try:
        cache_dir = Path.home() / ".cache" / "speechbrain_ecapa"
        classifier = sb_inf.EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            run_opts={"device": "cpu"},
            savedir=str(cache_dir),
        )
    except (OSError, RuntimeError) as exc:
        logger.warning(
            "Could not load speaker embedding model: %s",
            exc,
        )
        _cleanup_temp(temp_to_cleanup)
        return None
    return classifier


def _extract_embeddings(
    segments: list[Any],
    wav16: npt.NDArray[np.float32],
    classifier: object,
    torch_mod: types.ModuleType,
) -> list[Any]:
    """Extract speaker embeddings per segment."""
    embs: list[Any] = []
    for seg in segments:
        s = float(getattr(seg, "start", 0.0) or 0.0)
        e = float(getattr(seg, "end", s) or s)
        if e <= s:
            e = s + 0.2
        i0 = int(s * _SAMPLE_RATE_16K)
        i1 = int(e * _SAMPLE_RATE_16K)
        pad = int(0.05 * _SAMPLE_RATE_16K)
        i0 = max(0, i0 - pad)
        i1 = min(len(wav16), i1 + pad)
        if i1 - i0 < _MIN_SAMPLES_DIAR:
            i1 = min(len(wav16), i0 + _MIN_SAMPLES_DIAR)
        seg_wav = torch_mod.tensor(wav16[i0:i1]).unsqueeze(0)
        with torch_mod.no_grad():
            emb = classifier.encode_batch(seg_wav).squeeze(0).squeeze(0).cpu().numpy()
        embs.append(emb.astype("float32"))
    return embs


def diarize_segments(
    audio_path: str,
    segments: list[Any],
    num_speakers: int = 2,
) -> list[int] | None:
    """Compute speaker embeddings per segment and cluster.

    Returns speaker labels aligned with segments,
    or None on failure.
    """
    torch_mod = _try_import("torch")
    if torch_mod is None:
        logger.warning(
            "Diarization dependencies missing; skipping speaker labels.",
        )
        return None

    audio_result = _load_audio(audio_path)
    if audio_result is None:
        return None
    wav, sr, temp_to_cleanup = audio_result

    if wav.ndim == _NDIM_2D:
        wav = wav.mean(axis=1)
    wav16 = _resample_linear(wav, sr, _SAMPLE_RATE_16K)

    classifier = _load_speaker_classifier(temp_to_cleanup)
    if classifier is None:
        return None

    embs = _extract_embeddings(segments, wav16, classifier, torch_mod)

    if len(embs) == 0:
        return None
    labels = _kmeans_cosine(embs, k=max(1, int(num_speakers)))
    _cleanup_temp(temp_to_cleanup)
    return labels.tolist()
