"""Generate distinct notification sounds for the Pomodoro app."""

from __future__ import annotations

import logging
import math
from pathlib import Path
import struct
import wave

logger = logging.getLogger(__name__)

SAMPLE_RATE = 44100


def _write_wav(path: Path, samples: list[int]) -> None:
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def _tone(freq: float, duration: float, volume: float = 0.7) -> list[int]:
    n = int(SAMPLE_RATE * duration)
    return [
        int(volume * 32767 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
        for i in range(n)
    ]


def _fade(samples: list[int], fade_ms: int = 20) -> list[int]:
    n = int(SAMPLE_RATE * fade_ms / 1000)
    out = list(samples)
    for i in range(min(n, len(out))):
        out[i] = int(out[i] * i / n)
    for i in range(min(n, len(out))):
        out[-(i + 1)] = int(out[-(i + 1)] * i / n)
    return out


def _silence(duration: float) -> list[int]:
    return [0] * int(SAMPLE_RATE * duration)


def work_done(out: Path) -> None:
    """End of pomodoro: upward three-note chime (C5-E5-G5)."""
    samples = (
        _fade(_tone(523.25, 0.2))
        + _silence(0.05)
        + _fade(_tone(659.25, 0.2))
        + _silence(0.05)
        + _fade(_tone(783.99, 0.4))
    )
    _write_wav(out, samples)


def short_break_done(out: Path) -> None:
    """End of short break: two gentle pings (G5-C6)."""
    samples = _fade(_tone(783.99, 0.15)) + _silence(0.08) + _fade(_tone(1046.50, 0.3))
    _write_wav(out, samples)


def long_break_start(out: Path) -> None:
    """Start of long break: descending celebration (G5-E5-C5-C4 long)."""
    samples = (
        _fade(_tone(783.99, 0.15))
        + _silence(0.04)
        + _fade(_tone(659.25, 0.15))
        + _silence(0.04)
        + _fade(_tone(523.25, 0.15))
        + _silence(0.04)
        + _fade(_tone(261.63, 0.6, volume=0.5))
    )
    _write_wav(out, samples)


def long_break_done(out: Path) -> None:
    """End of long break: wake-up alarm — rapid repeated beeps."""
    beep = _fade(_tone(880.0, 0.1))
    gap = _silence(0.08)
    samples = (beep + gap) * 4 + _fade(_tone(1046.50, 0.3))
    _write_wav(out, samples)


def main() -> None:
    """Generate all notification sounds and log file sizes."""
    out_dir = Path(__file__).resolve().parent.parent / "assets" / "sounds"
    out_dir.mkdir(parents=True, exist_ok=True)

    work_done(out_dir / "work_done.wav")
    short_break_done(out_dir / "short_break_done.wav")
    long_break_start(out_dir / "long_break_start.wav")
    long_break_done(out_dir / "long_break_done.wav")

    for f in sorted(out_dir.glob("*.wav")):
        logger.info("  %s (%d bytes)", f.name, f.stat().st_size)


if __name__ == "__main__":
    main()
