#!/usr/bin/env python3
"""Live progress reporting for transcribe_fw.

``_format_progress_line`` is pure - seconds processed plus media duration in,
a display string out - which is what makes the percentage clamp and the ETA
testable without loading a model.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import TYPE_CHECKING, Any

from _transcribe_output import hhmmss

if TYPE_CHECKING:
    import argparse

logger = logging.getLogger(__name__)

_PROGRESS_THROTTLE_SEC = 0.2
_SECONDS_PER_DAY = 60 * 60 * 24


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
            f"[PROGRESS] {hhmmss(processed)} / {hhmmss(total_duration)} ({pct:5.1f}%)"
        )
        if processed > 0:
            rate = processed / max(1e-6, elapsed)
            remaining = max(0.0, total_duration - processed)
            eta = remaining / max(1e-6, rate)
            if eta < _SECONDS_PER_DAY:
                line += f" ETA ~{hhmmss(eta)}"
        return line
    return f"[PROGRESS] processed {hhmmss(processed)}"
