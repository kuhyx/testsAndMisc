"""MoviePy 2.x — Comprehensive Showcase of ALL Features.

Generates a video demonstrating every MoviePy class, method, effect,
and tool. Organised into sections:

  Part 1: Clip Types   (VideoClip, ColorClip, TextClip, ImageClip,
                         BitmapClip, DataVideoClip, ImageSequenceClip)
  Part 2: Clip Methods (subclipped, cropped, resized, rotated, with_position,
                         with_opacity, with_mask, image_transform, transform,
                         time_transform, with_speed_scaled, with_section_cut_out,
                         to_ImageClip, to_mask, to_RGB, with_background_color,
                         with_effects_on_subclip, with_layer_index)
  Part 3: Video Effects (all 34)
  Part 4: Audio         (AudioClip, AudioArrayClip, CompositeAudioClip,
                          all 7 audio effects)
  Part 5: Composition   (CompositeVideoClip, concatenate_videoclips, clips_array)
  Part 6: Drawing Tools (circle, color_gradient, color_split)
  Part 7: Output        (write_videofile params, write_gif, save_frame,
                          write_images_sequence)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import tempfile

from moviepy import (
    ColorClip,
    CompositeVideoClip,
    TextClip,
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx import FadeIn, FadeOut
import numpy as np

logger = logging.getLogger(__name__)

os.environ["FFMPEG_BINARY"] = "/usr/bin/ffmpeg"

# ── Constants ─────────────────────────────────────────────────────
W, H = 1920, 1080
FPS = 30
CLIP_DUR = 2.0  # duration of each demo clip
HEADER_DUR = 1.5  # duration of section headers
OUTPUT = "moviepy_showcase_full.mp4"
FONT_B = "/usr/share/fonts/noto/NotoSans-Bold.ttf"
FONT_R = "/usr/share/fonts/noto/NotoSans-Regular.ttf"

# ── Pre-computed gradient LUTs ────────────────────────────────────
_G_CH = (
    np.linspace(0, 255, H, dtype=np.uint8)[:, None]
    * np.ones(W, dtype=np.uint8)[None, :]
)
_B_CH = (
    np.ones(H, dtype=np.uint8)[:, None]
    * np.linspace(0, 255, W, dtype=np.uint8)[None, :]
)


def _gradient(t: float) -> np.ndarray:
    f = np.empty((H, W, 3), dtype=np.uint8)
    f[:, :, 0] = int(128 + 127 * np.sin(t * 2))
    f[:, :, 1] = _G_CH
    f[:, :, 2] = _B_CH
    return f


def _checkerboard(t: float) -> np.ndarray:
    sq = 60
    off = int(t * 40) % sq
    xs = np.arange(W, dtype=np.int32)[None, :]
    ys = np.arange(H, dtype=np.int32)[:, None]
    v = (((xs + off) // sq + (ys + off) // sq) % 2 * 255).astype(np.uint8)
    return np.dstack([v, v, v])


# ── Helpers ───────────────────────────────────────────────────────
def _base_clip(dur: float = CLIP_DUR) -> VideoClip:
    """Animated gradient as a reusable base clip."""
    return VideoClip(_gradient, duration=dur).with_fps(FPS)


def _label(
    text: str,
    size: int = 36,
    color: str = "white",
    pos: tuple[str, int] | tuple[str, str] = ("center", 40),
    dur: float = CLIP_DUR,
) -> TextClip:
    """Small label overlay (transparent bg)."""
    return (
        TextClip(
            text=text,
            font_size=size,
            color=color,
            font=FONT_R,
            margin=(0, 15),
        )
        .with_duration(dur)
        .with_position(pos)
    )


def _titled(clip: VideoClip, text: str) -> CompositeVideoClip:
    """Overlay a label onto a clip."""
    lbl = _label(text, dur=clip.duration)
    return CompositeVideoClip(
        [clip.with_duration(clip.duration), lbl],
        size=(W, H),
    )


def _section_header(title: str, subtitle: str = "") -> CompositeVideoClip:
    """Dark background with centred title text."""
    bg = ColorClip(size=(W, H), color=(15, 15, 40)).with_duration(HEADER_DUR)
    t = (
        TextClip(
            text=title,
            font_size=72,
            color="white",
            font=FONT_B,
            margin=(0, 30),
        )
        .with_duration(HEADER_DUR)
        .with_position(("center", 380))
    )
    parts: list[VideoClip] = [bg, t]
    if subtitle:
        s = (
            TextClip(
                text=subtitle,
                font_size=32,
                color="#aaaaaa",
                font=FONT_R,
                margin=(0, 15),
            )
            .with_duration(HEADER_DUR)
            .with_position(("center", 520))
        )
        parts.append(s)
    return CompositeVideoClip(parts, size=(W, H))


def _resize_to_canvas(clip: VideoClip) -> VideoClip:
    """Resize a clip to fit (W, H) and centre on black background."""
    cw, ch = clip.size
    scale = min(W / cw, H / ch)
    return clip.resized(
        width=int(cw * scale), height=int(ch * scale)
    ).with_background_color(size=(W, H), color=(0, 0, 0))


# ══════════════════════════════════════════════════════════════════
# ASSEMBLY — memory-safe: render each part to a temp file, then
# concatenate via VideoFileClip so only one part is in RAM at a time.
# ══════════════════════════════════════════════════════════════════
def _render_part(
    scenes: list[VideoClip],
    path: str,
    label: str,
) -> None:
    """Concatenate *scenes*, write to *path*, then close all clips."""
    logger.info("  Rendering %s (%d scenes) → %s", label, len(scenes), Path(path).name)
    part = concatenate_videoclips(scenes, method="compose", bg_color=(0, 0, 0))
    part.write_videofile(
        path,
        fps=FPS,
        codec="libx264",
        preset="ultrafast",
        audio=False,
        logger=None,
    )
    # Free memory
    part.close()
    for s in scenes:
        s.close()


def main() -> None:
    """Assemble all parts into the final showcase video."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Building MoviePy comprehensive showcase…")

    tmpdir = tempfile.mkdtemp(prefix="moviepy_showcase_")
    try:
        _build(tmpdir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _build(tmpdir: str) -> None:
    # ── Lazy imports to avoid circular dependency ────────────────
    # These submodules import constants from this module, so they
    # cannot be imported at the top level.
    from moviepy.audio.fx import MultiplyVolume

    from python_pkg.moviepy_showcase._moviepy_audio_output import (
        _make_sine,
        part4_audio,
        part5_composition,
        part6_drawing_tools,
        part7_output,
    )
    from python_pkg.moviepy_showcase._moviepy_clip_types import (
        part1_clip_types,
        part2_clip_methods,
    )
    from python_pkg.moviepy_showcase._moviepy_video_effects import (
        part3_video_effects,
    )

    # ── Render each part to its own temp file ─────────────────────
    # Title card
    title_bg = ColorClip(size=(W, H), color=(10, 10, 30)).with_duration(3.0)
    title_txt = (
        TextClip(
            text="MoviePy 2.x\nComplete Feature Showcase",
            font_size=80,
            color="white",
            font=FONT_B,
            method="caption",
            size=(W - 200, None),
            text_align="center",
            margin=(0, 40),
        )
        .with_duration(3.0)
        .with_position("center")
    )
    title_card = CompositeVideoClip([title_bg, title_txt], size=(W, H)).with_effects(
        [FadeIn(1.0)]
    )

    # Outro
    outro_bg = ColorClip(size=(W, H), color=(10, 10, 30)).with_duration(3.0)
    outro_txt = (
        TextClip(
            text="That's all of MoviePy 2.x!\n34 video effects · 7 audio effects\n"
            "11 clip types · drawing tools · composition",
            font_size=52,
            color="white",
            font=FONT_B,
            method="caption",
            size=(W - 200, None),
            text_align="center",
            margin=(0, 30),
        )
        .with_duration(3.0)
        .with_position("center")
    )
    outro = CompositeVideoClip([outro_bg, outro_txt], size=(W, H)).with_effects(
        [FadeOut(1.5)]
    )

    part_builders = [
        ("title", lambda: [title_card]),
        ("Part 1: Clip Types", part1_clip_types),
        ("Part 2: Clip Methods", part2_clip_methods),
        ("Part 3: Video Effects", part3_video_effects),
        ("Part 4: Audio", part4_audio),
        ("Part 5: Composition", part5_composition),
        ("Part 6: Drawing Tools", part6_drawing_tools),
        ("Part 7: Output Methods", part7_output),
        ("outro", lambda: [outro]),
    ]

    part_files: list[str] = []
    for i, (label, builder) in enumerate(part_builders):
        path = str(Path(tmpdir) / f"part_{i:02d}.mp4")
        scenes = builder()
        _render_part(scenes, path, label)
        part_files.append(path)

    # ── Load temp files as lightweight VideoFileClips & concat ─────
    logger.info("Concatenating all parts…")
    file_clips = [VideoFileClip(p) for p in part_files]
    final = concatenate_videoclips(file_clips, method="chain")

    # Background audio
    audio = _make_sine(330, final.duration).with_effects([MultiplyVolume(factor=0.5)])
    final = final.with_audio(audio)

    logger.info("Total duration: %.1fs", final.duration)
    logger.info("Writing %s (NVENC GPU)…", OUTPUT)

    final.write_videofile(
        OUTPUT,
        fps=FPS,
        codec="h264_nvenc",
        audio_codec="aac",
        threads=os.cpu_count(),
        ffmpeg_params=["-preset", "p4", "-rc", "constqp", "-qp", "18", "-b:v", "0"],
        logger="bar",
    )

    # Clean up
    final.close()
    for c in file_clips:
        c.close()

    size_mb = Path(OUTPUT).stat().st_size / (1024 * 1024)
    logger.info("✔ Saved %s (%.1f MB)", OUTPUT, size_mb)


if __name__ == "__main__":
    main()
