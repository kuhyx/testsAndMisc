#!/usr/bin/env python3
"""Transcribe audio with faster-whisper and write .txt and .srt."""

from __future__ import annotations

import argparse
import importlib
import logging
import os
from pathlib import Path
import sys
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import types

logger = logging.getLogger(__name__)

# Constants
_PROGRESS_THROTTLE_SEC = 0.2
_SECONDS_PER_DAY = 60 * 60 * 24


def _try_import(name: str) -> types.ModuleType | None:
    """Attempt to import a module, returning None on failure."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=("Transcribe audio with faster-whisper " "and write .txt and .srt"),
    )
    parser.add_argument("input", help="Path to audio/video file")
    parser.add_argument(
        "--model",
        default=os.environ.get("FW_MODEL", "large-v3"),
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
        default=int(os.environ.get("FW_NUM_SPEAKERS", "2")),
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
        compute_type = "float16" if device == "cuda" else "float32"
    return device, compute_type


def _run_progress_loop(
    args: argparse.Namespace,
    model: object,
    inp: str,
    total_duration: float | None,
) -> tuple[list[Any], object]:
    """Transcribe with live progress output."""
    start_ts = time.time()
    iter_segments, info = model.transcribe(inp, language=args.language)
    collected: list[Any] = []
    processed = 0.0
    last_prt = 0.0
    tty = sys.stderr.isatty()

    for seg in iter_segments:
        collected.append(seg)
        if getattr(seg, "end", None) is not None:
            processed = max(processed, float(seg.end))
        now = time.time()
        if not args.no_progress and (tty or (now - last_prt) >= _PROGRESS_THROTTLE_SEC):
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
    from _transcribe_output import hhmmss

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
            remaining = max(0.0, total_duration - processed)
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

    from _transcribe_diarize import diarize_segments
    from _transcribe_output import (
        write_rttm,
        write_srt_with_speakers,
        write_txt_with_speakers,
    )

    labels = diarize_segments(
        inp,
        collected,
        num_speakers=args.num_speakers,
    )
    if labels is not None and len(labels) == len(collected):
        diar_srt = str(outdir / (base + ".diar.srt"))
        diar_txt = str(outdir / (base + ".diar.txt"))
        rttm_path = str(outdir / (base + ".rttm"))
        write_srt_with_speakers(collected, labels, diar_srt)
        write_txt_with_speakers(collected, labels, diar_txt)
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
            "Diarization failed or returned " "mismatched labels; writing plain.",
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
            "faster-whisper is not installed " "in this environment.",
        )
        return 2

    inp_path = Path(args.input).resolve()
    if not inp_path.exists():
        logger.error("Input file not found: %s", inp_path)
        return 2

    inp = str(inp_path)
    outdir = Path(args.outdir or str(inp_path.parent) or ".").resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    base = inp_path.stem
    srt_path = str(outdir / (base + ".srt"))
    txt_path = str(outdir / (base + ".txt"))

    device, compute_type = _resolve_device_and_compute(args)

    logger.info(
        "Loading model='%s', device='%s', " "compute_type='%s'",
        args.model,
        device,
        compute_type,
    )

    model_path: str = args.model
    if not Path(args.model).is_dir():
        from _transcribe_model import (
            download_model_with_progress,
        )

        model_path = download_model_with_progress(args.model)

    ct2_logger = logging.getLogger("faster_whisper")
    ct2_logger.setLevel(logging.INFO)

    logger.info("Initializing model...")
    model = fw.WhisperModel(
        model_path,
        device=device,
        compute_type=compute_type,
    )
    logger.info("Model loaded successfully.")

    from _transcribe_diarize import get_media_duration
    from _transcribe_output import hhmmss

    total_duration = get_media_duration(inp)
    if total_duration:
        logger.info(
            "Media duration: %s",
            hhmmss(total_duration),
        )

    collected, info = _run_progress_loop(args, model, inp, total_duration)

    logger.info(
        "Detected language: %s (prob=%s)",
        getattr(info, "language", None),
        getattr(info, "language_probability", None),
    )
    logger.info("Segments: %d", len(collected))

    _write_diarized_outputs(args, inp, outdir, base, collected)

    from _transcribe_output import write_srt, write_txt

    write_txt(collected, txt_path)
    write_srt(collected, srt_path)
    logger.info("Wrote: %s", txt_path)
    logger.info("Wrote: %s", srt_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
