#!/usr/bin/env python3
"""Transcribe audio with faster-whisper and write .txt and .srt."""

from __future__ import annotations

import argparse
import contextlib
from datetime import timedelta
import importlib
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import types

    import numpy as np
    import numpy.typing as npt

logger = logging.getLogger(__name__)

# Constants
_BYTES_PER_KB = 1024
_NDIM_2D = 2
_SAMPLE_RATE_16K = 16000
_MIN_SAMPLES_DIAR = 1600
_PROGRESS_THROTTLE_SEC = 0.2
_SECONDS_PER_DAY = 60 * 60 * 24

# Model name to HF repo mapping
_MODEL_MAP: dict[str, str] = {
    "tiny": "Systran/faster-whisper-tiny",
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "base": "Systran/faster-whisper-base",
    "base.en": "Systran/faster-whisper-base.en",
    "small": "Systran/faster-whisper-small",
    "small.en": "Systran/faster-whisper-small.en",
    "medium": "Systran/faster-whisper-medium",
    "medium.en": "Systran/faster-whisper-medium.en",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
    "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
}


def _try_import(name: str) -> types.ModuleType | None:
    """Attempt to import a module, returning None on failure."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    fsize = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if fsize < _BYTES_PER_KB:
            return f"{fsize:.1f}{unit}"
        fsize /= _BYTES_PER_KB
    return f"{fsize:.1f}TB"


def _check_cache(
    repo_id: str,
) -> str | None:
    """Check HF cache for an already-downloaded model."""
    hh = _try_import("huggingface_hub")
    if hh is None:
        return None
    cache_path = hh.try_to_load_from_cache(
        repo_id, "model.bin"
    )
    if cache_path is not None:
        parent = str(Path(cache_path).parent)
        logger.info(
            "Model already cached, loading from: %s",
            parent,
        )
        return parent
    return None


def _download_files(
    repo_id: str,
    required_files: list[str],
) -> str:
    """Download required model files from HuggingFace."""
    hh = _try_import("huggingface_hub")
    if hh is None:
        msg = "huggingface_hub not available"
        raise RuntimeError(msg)

    logger.info(
        "Downloading model files from %s...",
        repo_id,
    )
    logger.info(
        "This may take several minutes for large "
        "models (~3GB for large-v3)",
    )

    _log_total_download_size(repo_id, required_files)

    downloaded = 0
    model_dir = ""
    start_time = time.time()

    for filename in required_files:
        file_start = time.time()
        logger.info("DOWNLOAD %s...", filename)
        try:
            local_path = hh.hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                resume_download=True,
            )
            elapsed = time.time() - file_start
            lp = Path(local_path)
            file_size = (
                lp.stat().st_size
                if lp.exists()
                else 0
            )
            logger.info(
                "done (%s, %.1fs)",
                format_bytes(file_size),
                elapsed,
            )
            downloaded += 1
            if downloaded == 1:
                model_dir = str(lp.parent)
        except OSError:
            logger.info("not found (optional)")
        except RuntimeError as exc:
            logger.info("error: %s", exc)

    total_time = time.time() - start_time
    logger.info("Download complete in %.1fs", total_time)
    return model_dir


def _log_total_download_size(
    repo_id: str, required_files: list[str]
) -> None:
    """Log total download size if available."""
    hh = _try_import("huggingface_hub")
    if hh is None:
        return
    with contextlib.suppress(OSError, RuntimeError):
        fs = hh.HfFileSystem()
        files_info = fs.ls(repo_id, detail=True)
        total_size = sum(
            f.get("size", 0)
            for f in files_info
            if f.get("name", "").split("/")[-1]
            in required_files
        )
        logger.info(
            "Total download size: ~%s",
            format_bytes(total_size),
        )


def download_model_with_progress(
    model_name: str,
) -> str:
    """Download model files from HuggingFace with progress.

    Returns the local path to the downloaded model.
    """
    hh = _try_import("huggingface_hub")
    if hh is None:
        logger.warning(
            "huggingface_hub not available, "
            "falling back to default download",
        )
        return model_name

    repo_id = _MODEL_MAP.get(model_name, model_name)

    if "/" not in repo_id and model_name not in _MODEL_MAP:
        repo_id = f"Systran/faster-whisper-{model_name}"

    logger.info("Checking model: %s", repo_id)

    required_files = [
        "config.json",
        "model.bin",
        "tokenizer.json",
        "vocabulary.txt",
    ]

    try:
        cached = _check_cache(repo_id)
        if cached is not None:
            return cached
        return _download_files(repo_id, required_files)
    except (OSError, RuntimeError) as exc:
        logger.warning(
            "Custom download failed (%s), "
            "falling back to default",
            exc,
        )
        return model_name


def format_timestamp(seconds: float) -> str:
    """Format seconds as SRT timestamp HH:MM:SS,mmm."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return (
        f"{hours:02d}:{minutes:02d}:"
        f"{secs:02d},{millis:03d}"
    )


def write_srt(
    segments: list[Any], srt_path: str
) -> None:
    """Write segments to an SRT subtitle file."""
    with Path(srt_path).open(
        "w", encoding="utf-8"
    ) as f:
        for i, seg in enumerate(segments, start=1):
            start = format_timestamp(seg.start)
            end = format_timestamp(seg.end)
            text = (seg.text or "").strip()
            if not text:
                continue
            f.write(
                f"{i}\n{start} --> {end}\n{text}\n\n"
            )


def write_txt(
    segments: list[Any], txt_path: str
) -> None:
    """Write segments as plain text, one per line."""
    with Path(txt_path).open(
        "w", encoding="utf-8"
    ) as f:
        for seg in segments:
            text = (seg.text or "").strip()
            if text:
                f.write(text + "\n")


def write_srt_with_speakers(
    segments: list[Any],
    labels: list[int],
    path: str,
) -> None:
    """Write SRT subtitles with speaker labels."""
    with Path(path).open("w", encoding="utf-8") as f:
        for i, (seg, lab) in enumerate(
            zip(segments, labels, strict=False),
            start=1,
        ):
            text = (seg.text or "").strip()
            if not text:
                continue
            spk = f"SPK{lab + 1}"
            start_ts = format_timestamp(seg.start)
            end_ts = format_timestamp(seg.end)
            f.write(
                f"{i}\n{start_ts} --> {end_ts}\n"
                f"[{spk}] {text}\n\n"
            )


def write_txt_with_speakers(
    segments: list[Any],
    labels: list[int],
    path: str,
) -> None:
    """Write plain text with speaker labels."""
    with Path(path).open("w", encoding="utf-8") as f:
        for seg, lab in zip(
            segments, labels, strict=False
        ):
            text = (seg.text or "").strip()
            if text:
                spk = f"SPK{lab + 1}"
                f.write(f"[{spk}] {text}\n")


def write_rttm(
    segments: list[Any],
    labels: list[int],
    path: str,
    file_id: str = "audio",
) -> None:
    """Write RTTM speaker diarization output."""
    with Path(path).open("w", encoding="utf-8") as f:
        for seg, lab in zip(
            segments, labels, strict=False
        ):
            start = float(
                getattr(seg, "start", 0.0) or 0.0
            )
            end = float(
                getattr(seg, "end", start) or start
            )
            dur = max(0.0, end - start)
            name = f"SPK{lab + 1}"
            f.write(
                f"SPEAKER {file_id} 1 "
                f"{start:.3f} {dur:.3f} "
                f"<NA> <NA> {name} <NA>\n"
            )


def hhmmss(seconds: float) -> str:
    """Format seconds as HH:MM:SS string."""
    seconds = max(0.0, float(seconds))
    total_seconds = int(seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


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


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Transcribe audio with faster-whisper "
            "and write .txt and .srt"
        ),
    )
    parser.add_argument(
        "input", help="Path to audio/video file"
    )
    parser.add_argument(
        "--model",
        default=os.environ.get(
            "FW_MODEL", "large-v3"
        ),
        help="Model size or path (default: large-v3)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Language code (e.g., en). None=auto",
    )
    parser.add_argument(
        "--device",
        default=os.environ.get("FW_DEVICE", "auto"),
        choices=["auto", "cpu", "cuda"],
        help="Device to run on",
    )
    parser.add_argument(
        "--compute-type",
        dest="compute_type",
        default=os.environ.get("FW_COMPUTE", "auto"),
        help="Compute type (auto,int8,float16,...)",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="Output dir (default: next to input)",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable live progress output",
    )
    parser.add_argument(
        "--diarize",
        action="store_true",
        help="Enable speaker diarization (labels)",
    )
    parser.add_argument(
        "--num-speakers",
        type=int,
        default=int(
            os.environ.get("FW_NUM_SPEAKERS", "2")
        ),
        help="Number of speakers (default: 2)",
    )
    return parser.parse_args()


def _resolve_device_and_compute(
    args: argparse.Namespace,
) -> tuple[str, str]:
    """Resolve device and compute_type from args."""
    device = args.device
    compute_type = args.compute_type
    if device == "auto":
        device = "cpu"
    if compute_type == "auto":
        compute_type = (
            "float16"
            if device == "cuda"
            else "float32"
        )
    return device, compute_type


def _run_progress_loop(
    args: argparse.Namespace,
    model: object,
    inp: str,
    total_duration: float | None,
) -> tuple[list[Any], object]:
    """Transcribe with live progress output."""
    start_ts = time.time()
    iter_segments, info = model.transcribe(
        inp, language=args.language
    )
    collected: list[Any] = []
    processed = 0.0
    last_prt = 0.0
    tty = sys.stderr.isatty()

    for seg in iter_segments:
        collected.append(seg)
        if getattr(seg, "end", None) is not None:
            processed = max(
                processed, float(seg.end)
            )
        now = time.time()
        if not args.no_progress and (
            tty
            or (now - last_prt)
            >= _PROGRESS_THROTTLE_SEC
        ):
            last_prt = now
            line = _format_progress_line(
                processed,
                total_duration,
                now,
                start_ts,
            )
            if tty:
                logger.info("\r%s", line)
            else:
                logger.info("%s", line)

    if not args.no_progress and tty:
        logger.info("")

    return collected, info


def _format_progress_line(
    processed: float,
    total_duration: float | None,
    now: float,
    start_ts: float,
) -> str:
    """Format a progress line string."""
    if total_duration and total_duration > 0:
        pct = max(
            0.0,
            min(
                100.0,
                (processed / total_duration) * 100.0,
            ),
        )
        elapsed = now - start_ts
        line = (
            f"[PROGRESS] {hhmmss(processed)} / "
            f"{hhmmss(total_duration)} "
            f"({pct:5.1f}%)"
        )
        if processed > 0:
            rate = processed / max(1e-6, elapsed)
            remaining = max(
                0.0, total_duration - processed
            )
            eta = remaining / max(1e-6, rate)
            if eta < _SECONDS_PER_DAY:
                line += f" ETA ~{hhmmss(eta)}"
        return line
    return f"[PROGRESS] processed {hhmmss(processed)}"


def _write_diarized_outputs(
    args: argparse.Namespace,
    inp: str,
    outdir: Path,
    base: str,
    collected: list[Any],
) -> None:
    """Optionally diarize and write speaker outputs."""
    if not args.diarize:
        return
    labels = diarize_segments(
        inp,
        collected,
        num_speakers=args.num_speakers,
    )
    if labels is not None and len(labels) == len(
        collected
    ):
        diar_srt = str(outdir / (base + ".diar.srt"))
        diar_txt = str(outdir / (base + ".diar.txt"))
        rttm_path = str(outdir / (base + ".rttm"))
        write_srt_with_speakers(
            collected, labels, diar_srt
        )
        write_txt_with_speakers(
            collected, labels, diar_txt
        )
        write_rttm(
            collected,
            labels,
            rttm_path,
            file_id=base,
        )
        logger.info("Wrote: %s", diar_txt)
        logger.info("Wrote: %s", diar_srt)
        logger.info("Wrote: %s", rttm_path)
    else:
        logger.warning(
            "Diarization failed or returned "
            "mismatched labels; writing plain.",
        )


def main() -> int:
    """Run the main transcription pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    args = _parse_args()

    fw = _try_import("faster_whisper")
    if fw is None:
        logger.error(
            "faster-whisper is not installed "
            "in this environment.",
        )
        return 2

    inp_path = Path(args.input).resolve()
    if not inp_path.exists():
        logger.error("Input file not found: %s", inp_path)
        return 2

    inp = str(inp_path)
    outdir = Path(
        args.outdir or str(inp_path.parent) or "."
    ).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    base = inp_path.stem
    srt_path = str(outdir / (base + ".srt"))
    txt_path = str(outdir / (base + ".txt"))

    device, compute_type = (
        _resolve_device_and_compute(args)
    )

    logger.info(
        "Loading model='%s', device='%s', "
        "compute_type='%s'",
        args.model,
        device,
        compute_type,
    )

    model_path: str = args.model
    if not Path(args.model).is_dir():
        model_path = download_model_with_progress(
            args.model
        )

    ct2_logger = logging.getLogger("faster_whisper")
    ct2_logger.setLevel(logging.INFO)

    logger.info("Initializing model...")
    model = fw.WhisperModel(
        model_path,
        device=device,
        compute_type=compute_type,
    )
    logger.info("Model loaded successfully.")

    total_duration = get_media_duration(inp)
    if total_duration:
        logger.info(
            "Media duration: %s",
            hhmmss(total_duration),
        )

    collected, info = _run_progress_loop(
        args, model, inp, total_duration
    )

    logger.info(
        "Detected language: %s (prob=%s)",
        getattr(info, "language", None),
        getattr(info, "language_probability", None),
    )
    logger.info("Segments: %d", len(collected))

    _write_diarized_outputs(
        args, inp, outdir, base, collected
    )

    write_txt(collected, txt_path)
    write_srt(collected, srt_path)
    logger.info("Wrote: %s", txt_path)
    logger.info("Wrote: %s", srt_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
