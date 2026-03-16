"""Shared constants and helper functions for Q23 segmentation video."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np

os.environ["FFMPEG_BINARY"] = "/usr/bin/ffmpeg"

from moviepy import (
    ColorClip,
    CompositeVideoClip,
    TextClip,
    VideoClip,
)
from moviepy.video.fx import FadeIn, FadeOut

# ── Constants ─────────────────────────────────────────────────────
W, H = 1280, 720
FPS = 24
STEP_DUR = 7.0
HEADER_DUR = 4.0
FONT_B = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/TTF/DejaVuSans.ttf"
OUTPUT_DIR = Path(__file__).resolve().parent / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = str(OUTPUT_DIR / "q23_segmentation.mp4")

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

BG_COLOR = (15, 20, 35)
rng = np.random.default_rng(42)


def _tc(**kwargs: object) -> TextClip:
    """TextClip wrapper that adds enough bottom margin to prevent clipping."""
    fs = kwargs.get("font_size", 24)
    m = int(fs) // 3 + 2
    kwargs["margin"] = (0, m)
    return TextClip(**kwargs)


def _make_header(
    title: str, subtitle: str, duration: float = HEADER_DUR
) -> CompositeVideoClip:
    bg = ColorClip(size=(W, H), color=BG_COLOR).with_duration(duration)
    t = (
        _tc(
            text=title,
            font_size=48,
            color="white",
            font=FONT_B,
        )
        .with_duration(duration)
        .with_position(("center", 260))
    )
    s = (
        _tc(
            text=subtitle,
            font_size=24,
            color="#90CAF9",
            font=FONT_R,
        )
        .with_duration(duration)
        .with_position(("center", 340))
    )
    return CompositeVideoClip([bg, t, s], size=(W, H)).with_effects(
        [FadeIn(0.5), FadeOut(0.5)]
    )


def _text_slide(
    lines: list[tuple[str, int, str, str, tuple[str | int, str | int]]],
    duration: float = STEP_DUR,
) -> CompositeVideoClip:
    """Create a slide with multiple text elements."""
    bg = ColorClip(size=(W, H), color=BG_COLOR).with_duration(duration)
    clips: list[VideoClip] = [bg]
    for text, font_size, color, font, pos in lines:
        tc = (
            _tc(
                text=text,
                font_size=font_size,
                color=color,
                font=font,
            )
            .with_duration(duration)
            .with_position(pos)
        )
        clips.append(tc)
    return CompositeVideoClip(clips, size=(W, H)).with_effects(
        [FadeIn(0.3), FadeOut(0.3)]
    )


def _compose_slide(
    base_clip: VideoClip,
    labels: list[tuple[str, int, str, str, tuple[int, int]]],
    duration: float,
) -> CompositeVideoClip:
    """Overlay text labels on an animated base clip."""
    text_clips: list[VideoClip] = [base_clip]
    for text, fs, color, font, pos in labels:
        tc = (
            _tc(text=text, font_size=fs, color=color, font=font)
            .with_duration(duration)
            .with_position(pos)
        )
        text_clips.append(tc)
    return CompositeVideoClip(text_clips, size=(W, H)).with_effects(
        [FadeIn(0.3), FadeOut(0.3)]
    )
