"""Output writers for transcription results (SRT, TXT, RTTM)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any


def format_timestamp(seconds: float) -> str:
    """Format seconds as SRT timestamp HH:MM:SS,mmm."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(segments: list[Any], srt_path: str) -> None:
    """Write segments to an SRT subtitle file."""
    with Path(srt_path).open("w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            start = format_timestamp(seg.start)
            end = format_timestamp(seg.end)
            text = (seg.text or "").strip()
            if not text:
                continue
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")


def write_txt(segments: list[Any], txt_path: str) -> None:
    """Write segments as plain text, one per line."""
    with Path(txt_path).open("w", encoding="utf-8") as f:
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
            f.write(f"{i}\n{start_ts} --> {end_ts}\n[{spk}] {text}\n\n")


def write_txt_with_speakers(
    segments: list[Any],
    labels: list[int],
    path: str,
) -> None:
    """Write plain text with speaker labels."""
    with Path(path).open("w", encoding="utf-8") as f:
        for seg, lab in zip(segments, labels, strict=False):
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
        for seg, lab in zip(segments, labels, strict=False):
            start = float(getattr(seg, "start", 0.0) or 0.0)
            end = float(getattr(seg, "end", start) or start)
            dur = max(0.0, end - start)
            name = f"SPK{lab + 1}"
            f.write(
                f"SPEAKER {file_id} 1 {start:.3f} {dur:.3f} <NA> <NA> {name} <NA>\n"
            )


def hhmmss(seconds: float) -> str:
    """Format seconds as HH:MM:SS string."""
    seconds = max(0.0, float(seconds))
    total_seconds = int(seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
