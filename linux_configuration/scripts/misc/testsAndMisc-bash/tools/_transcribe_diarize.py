"""Speaker diarization and audio processing utilities."""

from __future__ import annotations

import contextlib
import importlib
import logging
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import types

    import numpy as np
    import numpy.typing as npt

logger = logging.getLogger(__name__)

_NDIM_2D = 2
_SAMPLE_RATE_16K = 16000
_MIN_SAMPLES_DIAR = 1600


def _try_import(name: str) -> types.ModuleType | None:
    """Attempt to import a module, returning None on failure."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def _probe_with_ffmpeg_python(
    path: str,
) -> float | None:
    """Try ffmpeg-python to get duration."""
    ffmpeg_mod = _try_import("ffmpeg")
    if ffmpeg_mod is None:
        return None
    try:
        probe = ffmpeg_mod.probe(path)
        fmt = probe.get("format", {})
        if "duration" in fmt:
            return float(fmt["duration"])
    except (OSError, RuntimeError):
        pass
    return None


def _probe_with_ffprobe(path: str) -> float | None:
    """Try ffprobe CLI to get duration."""
    ffprobe_bin = shutil.which("ffprobe")
    if ffprobe_bin is None:
        return None
    try:
        out = subprocess.check_output(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default="
                "noprint_wrappers=1:nokey=1",
                path,
            ],
            stderr=subprocess.DEVNULL,
        )
        return float(out.decode().strip())
    except (
        OSError,
        subprocess.CalledProcessError,
        ValueError,
    ):
        return None


def get_media_duration(path: str) -> float | None:
    """Try to get media duration in seconds.

    Returns None if unavailable.
    """
    result = _probe_with_ffmpeg_python(path)
    if result is not None:
        return result
    return _probe_with_ffprobe(path)


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
    xp = np_mod.linspace(
        0.0, 1.0, num=x.shape[-1], endpoint=False
    )
    xq = np_mod.linspace(
        0.0, 1.0, num=n_out, endpoint=False
    )
    y = np_mod.interp(
        xq, xp, x.astype(np_mod.float32)
    )
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
    if (
        features.ndim != _NDIM_2D
        or features.shape[0] == 0
    ):
        return np_mod.zeros((0,), dtype=np_mod.int64)
    features = features / (
        np_mod.linalg.norm(
            features, axis=1, keepdims=True
        )
        + 1e-8
    )
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
        pad /= (
            np_mod.linalg.norm(
                pad, axis=1, keepdims=True
            )
            + 1e-8
        )
        centroids = np_mod.concatenate(
            [centroids, pad], axis=0
        )
    return _run_kmeans_iterations(
        np_mod, features, centroids, k, iters
    )


def _run_kmeans_iterations(
    np_mod: object,
    features: object,
    centroids: object,
    k: int,
    iters: int,
) -> object:
    """Run k-means iteration loop and return labels."""
    labels: object = None
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
        if np_mod.allclose(
            new_c, centroids, atol=1e-4
        ):
            break
        centroids = new_c
    return labels


def _ffmpeg_transcode_to_wav16_mono(
    src_path: str,
) -> str | None:
    """Transcode input to a temporary 16k mono WAV.

    Returns its path, or None if ffmpeg is unavailable.
    """
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin is None:
        return None
    with tempfile.NamedTemporaryFile(
        prefix="fw_diar_",
        suffix=".wav",
        delete=False,
    ) as tmp:
        tmp_path = tmp.name

    cmd = [
        ffmpeg_bin,
        "-y",
        "-v",
        "error",
        "-i",
        src_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        tmp_path,
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        with contextlib.suppress(OSError):
            Path(tmp_path).unlink()
        return None
    else:
        return tmp_path


def _cleanup_temp(path: str | None) -> None:
    """Remove a temporary file if it exists."""
    if path is not None:
        with contextlib.suppress(OSError):
            Path(path).unlink()


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
        alt = _ffmpeg_transcode_to_wav16_mono(
            audio_path
        )
        if alt is None:
            logger.warning(
                "Could not read audio for diarization "
                "and no ffmpeg fallback: %s",
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
        else:
            return wav, sr, alt
    else:
        return wav, sr, None


def _load_speaker_classifier(
    temp_to_cleanup: str | None,
) -> object | None:
    """Load the ECAPA speaker embedding classifier."""
    sb_inf = _try_import("speechbrain.inference")
    if sb_inf is None:
        return None
    try:
        cache_dir = (
            Path.home() / ".cache" / "speechbrain_ecapa"
        )
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
    else:
        return classifier


def _extract_embeddings(
    segments: list[Any],
    wav16: object,
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
            i1 = min(
                len(wav16), i0 + _MIN_SAMPLES_DIAR
            )
        seg_wav = torch_mod.tensor(
            wav16[i0:i1]
        ).unsqueeze(0)
        with torch_mod.no_grad():
            emb = (
                classifier.encode_batch(seg_wav)
                .squeeze(0)
                .squeeze(0)
                .cpu()
                .numpy()
            )
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
            "Diarization dependencies missing; "
            "skipping speaker labels.",
        )
        return None

    audio_result = _load_audio(audio_path)
    if audio_result is None:
        return None
    wav, sr, temp_to_cleanup = audio_result

    if wav.ndim == _NDIM_2D:
        wav = wav.mean(axis=1)
    wav16 = _resample_linear(
        wav, sr, _SAMPLE_RATE_16K
    )

    classifier = _load_speaker_classifier(
        temp_to_cleanup
    )
    if classifier is None:
        return None

    embs = _extract_embeddings(
        segments, wav16, classifier, torch_mod
    )

    if len(embs) == 0:
        return None
    labels = _kmeans_cosine(
        embs, k=max(1, int(num_speakers))
    )
    _cleanup_temp(temp_to_cleanup)
    return labels.tolist()
