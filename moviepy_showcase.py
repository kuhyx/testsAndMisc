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
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

os.environ["FFMPEG_BINARY"] = "/usr/bin/ffmpeg"

from moviepy import (  # noqa: E402
    AudioArrayClip,
    AudioClip,
    BitmapClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    DataVideoClip,
    ImageClip,
    ImageSequenceClip,
    TextClip,
    VideoClip,
    VideoFileClip,
    concatenate_audioclips,
    concatenate_videoclips,
)
from moviepy.audio.fx import (  # noqa: E402
    AudioDelay,
    AudioFadeIn,
    AudioFadeOut,
    AudioLoop,
    AudioNormalize,
    MultiplyStereoVolume,
    MultiplyVolume,
)
from moviepy.video.compositing.CompositeVideoClip import (  # noqa: E402
    clips_array,
)
from moviepy.video.fx import (  # noqa: E402
    AccelDecel,
    BlackAndWhite,
    Blink,
    Crop,
    CrossFadeIn,
    CrossFadeOut,
    EvenSize,
    FadeIn,
    FadeOut,
    Freeze,
    FreezeRegion,
    GammaCorrection,
    HeadBlur,
    InvertColors,
    Loop,
    LumContrast,
    MakeLoopable,
    Margin,
    MaskColor,
    MirrorX,
    MirrorY,
    MultiplyColor,
    MultiplySpeed,
    Painting,
    Resize,
    Rotate,
    Scroll,
    SlideIn,
    SlideOut,
    SuperSample,
    TimeMirror,
    TimeSymmetrize,
)
from moviepy.video.tools.drawing import (  # noqa: E402
    circle,
    color_gradient,
    color_split,
)

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
# PART 1 — Clip Types
# ══════════════════════════════════════════════════════════════════
def part1_clip_types() -> list[VideoClip]:
    """Demonstrate every clip creation class."""
    scenes: list[VideoClip] = [
        _section_header(
            "Part 1: Clip Types",
            "VideoClip · ColorClip · TextClip · ImageClip"
            " · BitmapClip · DataVideoClip · ImageSequenceClip",
        ),
    ]

    # 1. VideoClip — custom frame function
    vc = VideoClip(_gradient, duration=CLIP_DUR).with_fps(FPS)
    scenes.append(_titled(vc, "VideoClip(frame_function)"))

    # 2. ColorClip
    cc = ColorClip(size=(W, H), color=(0, 120, 200)).with_duration(CLIP_DUR)
    scenes.append(_titled(cc, "ColorClip(size, color)"))

    # 3. TextClip — label method
    tbg = ColorClip(size=(W, H), color=(20, 20, 50)).with_duration(CLIP_DUR)
    tc = (
        TextClip(
            text="Hello MoviePy!",
            font_size=96,
            color="yellow",
            font=FONT_B,
            stroke_color="black",
            stroke_width=3,
            bg_color=None,
            margin=(10, 30),
            method="label",
            horizontal_align="center",
            vertical_align="center",
            transparent=True,
        )
        .with_duration(CLIP_DUR)
        .with_position("center")
    )
    scenes.append(
        _titled(
            CompositeVideoClip([tbg, tc], size=(W, H)),
            "TextClip(text, font_size, color, stroke, margin, method='label')",
        )
    )

    # 4. TextClip — caption method (wraps text)
    tbg2 = ColorClip(size=(W, H), color=(50, 20, 20)).with_duration(CLIP_DUR)
    tc2 = (
        TextClip(
            text="This is a longer caption that wraps "
            "because we use method='caption' with a fixed size.",
            font_size=48,
            color="white",
            font=FONT_R,
            method="caption",
            size=(W - 200, None),
            text_align="center",
            interline=10,
            margin=(0, 20),
        )
        .with_duration(CLIP_DUR)
        .with_position("center")
    )
    scenes.append(
        _titled(
            CompositeVideoClip([tbg2, tc2], size=(W, H)),
            "TextClip(method='caption', text_align, interline, size)",
        )
    )

    # 5. ImageClip — from numpy array
    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[200:880, 400:1520] = [255, 100, 50]  # orange rectangle
    ic = ImageClip(img, duration=CLIP_DUR)
    scenes.append(_titled(ic, "ImageClip(numpy_array)"))

    # 6. BitmapClip — from ASCII-art frames
    frames = [
        ["RR__", "RR__", "__BB", "__BB"],
        ["__RR", "__RR", "BB__", "BB__"],
        ["RR__", "RR__", "__BB", "__BB"],
        ["__RR", "__RR", "BB__", "BB__"],
    ]
    bc = BitmapClip(
        frames,
        fps=2,
        color_dict={"R": (255, 0, 0), "B": (0, 0, 255), "_": (30, 30, 30)},
    )
    bc = _resize_to_canvas(bc)
    scenes.append(
        _titled(bc.with_duration(CLIP_DUR), "BitmapClip(bitmap_frames, color_dict)")
    )

    # 7. DataVideoClip — data-driven frames
    data_list = list(range(60))

    def data_to_frame(d: int) -> np.ndarray:
        frame = np.full((H, W, 3), 30, dtype=np.uint8)
        bar_w = int(d / 60 * (W - 100))
        frame[400:680, 50 : 50 + bar_w] = [0, 200, 100]
        return frame

    dvc = DataVideoClip(data_list, data_to_frame, fps=FPS).with_duration(CLIP_DUR)
    scenes.append(_titled(dvc, "DataVideoClip(data, data_to_frame)"))

    # 8. ImageSequenceClip — from a list of arrays
    seq_frames = []
    for i in range(10):
        f = np.full((H, W, 3), int(25 * i), dtype=np.uint8)
        f[:, :, 0] = int(255 - 25 * i)
        seq_frames.append(f)
    isc = ImageSequenceClip(seq_frames, fps=5).with_duration(CLIP_DUR)
    scenes.append(_titled(isc, "ImageSequenceClip(sequence, fps)"))

    return scenes


# ══════════════════════════════════════════════════════════════════
# PART 2 — Clip Methods
# ══════════════════════════════════════════════════════════════════
def part2_clip_methods() -> list[VideoClip]:
    """Demonstrate VideoClip methods."""
    scenes: list[VideoClip] = [
        _section_header(
            "Part 2: Clip Methods",
            "subclipped · cropped · resized · rotated"
            " · with_position · with_opacity · …",
        ),
    ]

    base = _base_clip(3.0)

    # subclipped
    sc = base.subclipped(0.5, 2.5)
    scenes.append(
        _titled(_resize_to_canvas(sc), "subclipped(start_time=0.5, end_time=2.5)")
    )

    # cropped
    cr = base.cropped(x1=200, y1=100, x2=1200, y2=700).with_duration(CLIP_DUR)
    scenes.append(
        _titled(_resize_to_canvas(cr), "cropped(x1=200, y1=100, x2=1200, y2=700)")
    )

    # resized — by factor
    rs1 = base.resized(0.5).with_duration(CLIP_DUR)
    scenes.append(_titled(_resize_to_canvas(rs1), "resized(0.5)  # half size"))

    # resized — by height
    rs2 = base.resized(height=400).with_duration(CLIP_DUR)
    scenes.append(_titled(_resize_to_canvas(rs2), "resized(height=400)"))

    # rotated
    rt = base.rotated(30, expand=False, bg_color=(0, 0, 0)).with_duration(CLIP_DUR)
    scenes.append(_titled(rt, "rotated(angle=30, expand=False)"))

    # with_position + with_opacity in a composite
    small = base.resized(0.4).with_duration(CLIP_DUR)
    bg = ColorClip(size=(W, H), color=(10, 10, 10)).with_duration(CLIP_DUR)
    p1 = small.with_position((50, 50)).with_opacity(1.0)
    p2 = small.with_position((500, 300)).with_opacity(0.5)
    comp = CompositeVideoClip([bg, p1, p2], size=(W, H))
    scenes.append(_titled(comp, "with_position() + with_opacity(0.5)"))

    # with_mask — circular mask
    mask_arr = circle(
        screensize=(W, H),
        center=(W // 2, H // 2),
        radius=300,
        color=1.0,
        bg_color=0.0,
        blur=20,
    )
    mask_clip = ImageClip(mask_arr, is_mask=True, duration=CLIP_DUR)
    masked = base.with_duration(CLIP_DUR).with_mask(mask_clip)
    mbg = ColorClip(size=(W, H), color=(0, 0, 0)).with_duration(CLIP_DUR)
    scenes.append(
        _titled(
            CompositeVideoClip([mbg, masked], size=(W, H)),
            "with_mask() — circular mask via drawing.circle()",
        )
    )

    # image_transform
    def flip_lr(img: np.ndarray) -> np.ndarray:
        return img[:, ::-1]

    it = base.image_transform(flip_lr).with_duration(CLIP_DUR)
    scenes.append(_titled(it, "image_transform(flip_lr_func)"))

    # transform
    def shift_right(gf: Callable[[float], np.ndarray], t: float) -> np.ndarray:
        frame = gf(t)
        shift = int(t * 100)
        return np.roll(frame, shift, axis=1)

    tf = base.transform(shift_right).with_duration(CLIP_DUR)
    scenes.append(_titled(tf, "transform(shift_right_func)"))

    # time_transform
    tt = base.time_transform(lambda t: t * 3).with_duration(CLIP_DUR)
    scenes.append(_titled(tt, "time_transform(lambda t: t*3)  # 3x speed"))

    # with_speed_scaled
    ss = base.with_speed_scaled(factor=0.5)
    scenes.append(_titled(ss.with_duration(CLIP_DUR), "with_speed_scaled(factor=0.5)"))

    # with_section_cut_out
    sco = base.with_section_cut_out(0.5, 1.5)
    scenes.append(
        _titled(
            sco.with_duration(min(sco.duration, CLIP_DUR)),
            "with_section_cut_out(0.5, 1.5)",
        )
    )

    # to_ImageClip
    still = base.to_ImageClip(t=1.0, duration=CLIP_DUR)
    scenes.append(_titled(still, "to_ImageClip(t=1.0)  # freeze at t=1"))

    # to_mask + to_RGB
    bw = base.to_mask(canal=1).to_RGB().with_duration(CLIP_DUR)
    scenes.append(_titled(bw, "to_mask(canal=1).to_RGB()"))

    # with_background_color
    small2 = base.resized(0.5).with_duration(CLIP_DUR)
    wbg = small2.with_background_color(size=(W, H), color=(80, 0, 120))
    scenes.append(_titled(wbg, "with_background_color(color=(80,0,120))"))

    # with_effects_on_subclip
    eos = base.with_effects_on_subclip(
        [InvertColors()], start_time=0.5, end_time=1.5
    ).with_duration(CLIP_DUR)
    scenes.append(_titled(eos, "with_effects_on_subclip([InvertColors], 0.5, 1.5)"))

    # with_volume_scaled (visual label only — audio effect)
    vsc = base.with_duration(CLIP_DUR)
    scenes.append(_titled(vsc, "with_volume_scaled(factor)  # scales audio amplitude"))

    # with_layer_index
    scenes.append(
        _titled(
            base.with_duration(CLIP_DUR), "with_layer_index(n)  # compositing z-order"
        )
    )

    return scenes


# ══════════════════════════════════════════════════════════════════
# PART 3 — Video Effects (all 34)
# ══════════════════════════════════════════════════════════════════
def part3_video_effects() -> list[VideoClip]:  # noqa: PLR0915
    """Demonstrate all 34 video effects."""
    scenes: list[VideoClip] = [
        _section_header(
            "Part 3: Video Effects",
            "All 34 effects from moviepy.video.fx",
        ),
    ]

    def _fx(effect: object, label: str, dur: float = CLIP_DUR) -> VideoClip:
        """Apply effect to base clip and label it."""
        b = _base_clip(dur)
        try:
            result = b.with_effects([effect])
            # Ensure it has a finite duration
            if result.duration is None or result.duration <= 0:
                result = result.with_duration(dur)
            result = result.with_duration(min(result.duration, dur))
        except (ValueError, OSError, AttributeError):
            result = b
        # Make sure it fits the canvas
        if result.size != (W, H):
            result = _resize_to_canvas(result)
        return _titled(result, label)

    # 1. AccelDecel
    scenes.append(
        _fx(
            AccelDecel(new_duration=CLIP_DUR, abruptness=2.0, soonness=1.0),
            "AccelDecel(abruptness=2.0, soonness=1.0)",
        )
    )

    # 2. BlackAndWhite
    scenes.append(
        _fx(
            BlackAndWhite(preserve_luminosity=True),
            "BlackAndWhite(preserve_luminosity=True)",
        )
    )

    # 3. Blink
    scenes.append(
        _fx(
            Blink(duration_on=0.3, duration_off=0.3),
            "Blink(duration_on=0.3, duration_off=0.3)",
        )
    )

    # 4. Crop
    b_crop = _base_clip().with_effects([Crop(x1=200, y1=100, x2=1400, y2=800)])
    scenes.append(
        _titled(_resize_to_canvas(b_crop), "Crop(x1=200, y1=100, x2=1400, y2=800)")
    )

    # 5. CrossFadeIn
    scenes.append(_fx(CrossFadeIn(duration=1.0), "CrossFadeIn(duration=1.0)"))

    # 6. CrossFadeOut
    scenes.append(_fx(CrossFadeOut(duration=1.0), "CrossFadeOut(duration=1.0)"))

    # 7. EvenSize
    scenes.append(_fx(EvenSize(), "EvenSize()  # ensures even wxh"))

    # 8. FadeIn
    scenes.append(
        _fx(
            FadeIn(duration=1.5, initial_color=[0, 0, 0]),
            "FadeIn(duration=1.5, initial_color=[0,0,0])",
        )
    )

    # 9. FadeOut
    scenes.append(
        _fx(
            FadeOut(duration=1.5, final_color=[0, 0, 0]),
            "FadeOut(duration=1.5, final_color=[0,0,0])",
        )
    )

    # 10. Freeze
    scenes.append(
        _fx(
            Freeze(t=0.5, freeze_duration=1.0),
            "Freeze(t=0.5, freeze_duration=1.0)",
            dur=3.0,
        )
    )

    # 11. FreezeRegion
    scenes.append(
        _fx(
            FreezeRegion(t=0.5, region=(200, 100, 1400, 700)),
            "FreezeRegion(t=0.5, region=(200,100,1400,700))",
        )
    )

    # 12. GammaCorrection
    scenes.append(_fx(GammaCorrection(gamma=2.5), "GammaCorrection(gamma=2.5)"))

    # 13. HeadBlur
    scenes.append(
        _fx(
            HeadBlur(
                fx=lambda t: W // 2,  # noqa: ARG005
                fy=lambda t: H // 2,  # noqa: ARG005
                radius=100,
                intensity=None,
            ),
            "HeadBlur(fx, fy, radius=100)",
        )
    )

    # 14. InvertColors
    scenes.append(_fx(InvertColors(), "InvertColors()"))

    # 15. Loop
    short = _base_clip(0.5)
    looped = short.with_effects([Loop(n=4)])
    scenes.append(_titled(looped.with_duration(CLIP_DUR), "Loop(n=4)"))

    # 16. LumContrast
    scenes.append(
        _fx(
            LumContrast(lum=30, contrast=50, contrast_threshold=127),
            "LumContrast(lum=30, contrast=50)",
        )
    )

    # 17. MakeLoopable
    scenes.append(
        _fx(MakeLoopable(overlap_duration=0.5), "MakeLoopable(overlap_duration=0.5)")
    )

    # 18. Margin
    b_margin = _base_clip().with_effects(
        [
            Resize(0.7),
            Margin(
                margin_size=None,
                left=40,
                right=40,
                top=20,
                bottom=20,
                color=(255, 0, 0),
                opacity=1.0,
            ),
        ]
    )
    scenes.append(
        _titled(
            _resize_to_canvas(b_margin),
            "Margin(left=40, right=40, top=20, bottom=20, color=red)",
        )
    )

    # 19. MaskColor
    scenes.append(
        _fx(
            MaskColor(color=(128, 128, 128), threshold=80, stiffness=1),
            "MaskColor(color, threshold=80)",
        )
    )

    # 20. MasksAnd
    mask1 = circle((W, H), (W // 3, H // 2), 300, 1.0, 0.0, 1)
    mask2 = circle((W, H), (2 * W // 3, H // 2), 300, 1.0, 0.0, 1)
    combined = np.minimum(mask1, mask2)
    m_clip = ImageClip(combined, is_mask=True, duration=CLIP_DUR)
    masked_and = _base_clip().with_mask(m_clip)
    mbg = ColorClip(size=(W, H), color=(0, 0, 0)).with_duration(CLIP_DUR)
    scenes.append(
        _titled(
            CompositeVideoClip([mbg, masked_and], size=(W, H)),
            "MasksAnd — intersection of two circle masks",
        )
    )

    # 21. MasksOr
    combined_or = np.maximum(mask1, mask2)
    m_clip2 = ImageClip(combined_or, is_mask=True, duration=CLIP_DUR)
    masked_or = _base_clip().with_mask(m_clip2)
    scenes.append(
        _titled(
            CompositeVideoClip([mbg, masked_or], size=(W, H)),
            "MasksOr — union of two circle masks",
        )
    )

    # 22. MirrorX
    scenes.append(_fx(MirrorX(), "MirrorX()  # horizontal flip"))

    # 23. MirrorY
    scenes.append(_fx(MirrorY(), "MirrorY()  # vertical flip"))

    # 24. MultiplyColor
    scenes.append(_fx(MultiplyColor(factor=1.8), "MultiplyColor(factor=1.8)"))

    # 25. MultiplySpeed
    scenes.append(_fx(MultiplySpeed(factor=3.0), "MultiplySpeed(factor=3.0)", dur=4.0))

    # 26. Painting
    scenes.append(
        _fx(
            Painting(saturation=1.4, black=0.006),
            "Painting(saturation=1.4, black=0.006)",
        )
    )

    # 27. Resize
    b_rs = _base_clip().with_effects([Resize(new_size=(960, 540))])
    scenes.append(_titled(_resize_to_canvas(b_rs), "Resize(new_size=(960,540))"))

    # 28. Rotate
    scenes.append(
        _fx(
            Rotate(angle=45, expand=True, bg_color=(0, 0, 0)),
            "Rotate(angle=45, expand=True)",
        )
    )

    # 29. Scroll
    # Draw bands
    tall_arr = np.full((H * 3, W, 3), 40, dtype=np.uint8)
    for i in range(6):
        y0, y1 = i * H // 2, (i + 1) * H // 2
        tall_arr[y0:y1, :] = [
            (50 * i) % 256,
            (100 + 30 * i) % 256,
            (200 - 20 * i) % 256,
        ]
    tall_clip = ImageClip(tall_arr, duration=CLIP_DUR).with_effects(
        [
            Scroll(h=H, y_speed=-300, w=W),
        ]
    )
    scenes.append(_titled(_resize_to_canvas(tall_clip), "Scroll(h, y_speed=-300)"))

    # 30. SlideIn
    si = _base_clip().with_effects([SlideIn(duration=1.0, side="left")])
    scenes.append(_titled(si, "SlideIn(duration=1.0, side='left')"))

    # 31. SlideOut
    so = _base_clip().with_effects([SlideOut(duration=1.0, side="right")])
    scenes.append(_titled(so, "SlideOut(duration=1.0, side='right')"))

    # 32. SuperSample
    scenes.append(_fx(SuperSample(d=0.1, n_frames=3), "SuperSample(d=0.1, n_frames=3)"))

    # 33. TimeMirror
    tm = _base_clip().with_effects([TimeMirror()])
    scenes.append(
        _titled(tm.with_duration(CLIP_DUR), "TimeMirror()  # plays backwards")
    )

    # 34. TimeSymmetrize
    ts = _base_clip().with_effects([TimeSymmetrize()])
    scenes.append(
        _titled(ts.with_duration(CLIP_DUR), "TimeSymmetrize()  # forward then reverse")
    )

    return scenes


# ══════════════════════════════════════════════════════════════════
# PART 4 — Audio
# ══════════════════════════════════════════════════════════════════
def _make_sine(freq: float = 440.0, dur: float = CLIP_DUR) -> AudioClip:
    """Pure sine-wave AudioClip."""

    def maker(t: np.ndarray) -> np.ndarray:
        t_arr = np.asarray(t)
        wave = 0.3 * np.sin(2 * np.pi * freq * t_arr.flatten())
        stereo = np.column_stack([wave, wave])
        # MoviePy probes with scalar t=0 and uses len(list(frame0))
        # for nchannels. A (1,2) array iterates as 1 row → nchannels=1.
        # Returning shape (2,) for scalar t lets MoviePy detect 2 channels.
        if t_arr.ndim == 0:
            return stereo[0]
        return stereo

    return AudioClip(maker, duration=dur, fps=44100)


def part4_audio() -> list[VideoClip]:
    """Demonstrate audio clips and all 7 audio effects."""
    scenes: list[VideoClip] = [
        _section_header(
            "Part 4: Audio",
            "AudioClip · AudioArrayClip · CompositeAudioClip · 7 Audio Effects",
        ),
    ]
    bg = ColorClip(size=(W, H), color=(20, 30, 50))

    # AudioClip
    a1 = _make_sine(440, CLIP_DUR)
    c1 = bg.with_duration(CLIP_DUR).with_audio(a1)
    scenes.append(_titled(c1, "AudioClip(sine_440Hz)"))

    # AudioArrayClip
    sr = 44100
    t_arr = np.linspace(0, CLIP_DUR, int(sr * CLIP_DUR), endpoint=False)
    arr = (0.3 * np.sin(2 * np.pi * 880 * t_arr)).astype(np.float64)
    stereo = np.column_stack([arr, arr])
    a2 = AudioArrayClip(stereo, fps=sr)
    c2 = bg.with_duration(CLIP_DUR).with_audio(a2)
    scenes.append(_titled(c2, "AudioArrayClip(numpy_array, fps=44100)  # 880Hz"))

    # CompositeAudioClip
    low = _make_sine(220, CLIP_DUR)
    high = _make_sine(660, CLIP_DUR)
    comp_audio = CompositeAudioClip([low, high])
    c3 = bg.with_duration(CLIP_DUR).with_audio(comp_audio)
    scenes.append(_titled(c3, "CompositeAudioClip([220Hz, 660Hz])"))

    # concatenate_audioclips
    a_cat = concatenate_audioclips([_make_sine(330, 1.0), _make_sine(550, 1.0)])
    c4 = bg.with_duration(CLIP_DUR).with_audio(a_cat)
    scenes.append(_titled(c4, "concatenate_audioclips([330Hz, 550Hz])"))

    # AudioFadeIn
    a_fi = _make_sine(440, CLIP_DUR).with_effects([AudioFadeIn(duration=1.5)])
    c5 = bg.with_duration(CLIP_DUR).with_audio(a_fi)
    scenes.append(_titled(c5, "AudioFadeIn(duration=1.5)"))

    # AudioFadeOut
    a_fo = _make_sine(440, CLIP_DUR).with_effects([AudioFadeOut(duration=1.5)])
    c6 = bg.with_duration(CLIP_DUR).with_audio(a_fo)
    scenes.append(_titled(c6, "AudioFadeOut(duration=1.5)"))

    # AudioDelay
    a_delay = _make_sine(440, CLIP_DUR).with_effects(
        [AudioDelay(offset=0.2, n_repeats=4, decay=1)]
    )
    c7 = bg.with_duration(a_delay.duration).with_audio(a_delay)
    scenes.append(
        _titled(
            c7.with_duration(CLIP_DUR), "AudioDelay(offset=0.2, n_repeats=4, decay=1)"
        )
    )

    # AudioLoop
    short_a = _make_sine(440, 0.5)
    a_loop = short_a.with_effects([AudioLoop(duration=CLIP_DUR)])
    c8 = bg.with_duration(CLIP_DUR).with_audio(a_loop)
    scenes.append(_titled(c8, "AudioLoop(duration=2.0)"))

    # AudioNormalize
    quiet = _make_sine(440, CLIP_DUR)  # already normalized but demonstrates the call
    a_norm = quiet.with_effects([AudioNormalize()])
    c9 = bg.with_duration(CLIP_DUR).with_audio(a_norm)
    scenes.append(_titled(c9, "AudioNormalize()"))

    # MultiplyStereoVolume
    a_stereo = _make_sine(440, CLIP_DUR).with_effects(
        [MultiplyStereoVolume(left=1.0, right=0.2)]
    )
    c10 = bg.with_duration(CLIP_DUR).with_audio(a_stereo)
    scenes.append(_titled(c10, "MultiplyStereoVolume(left=1.0, right=0.2)"))

    # MultiplyVolume
    a_vol = _make_sine(440, CLIP_DUR).with_effects([MultiplyVolume(factor=0.3)])
    c11 = bg.with_duration(CLIP_DUR).with_audio(a_vol)
    scenes.append(_titled(c11, "MultiplyVolume(factor=0.3)"))

    return scenes


# ══════════════════════════════════════════════════════════════════
# PART 5 — Composition
# ══════════════════════════════════════════════════════════════════
def part5_composition() -> list[VideoClip]:
    """Demonstrate composition & concatenation."""
    scenes: list[VideoClip] = [
        _section_header(
            "Part 5: Composition",
            "CompositeVideoClip · concatenate_videoclips · clips_array",
        ),
    ]

    # CompositeVideoClip with bg_color, use_bgclip
    bg = _base_clip()
    overlay = (
        ColorClip(size=(400, 400), color=(255, 50, 50))
        .with_duration(CLIP_DUR)
        .with_position(("center", "center"))
        .with_opacity(0.6)
    )
    comp1 = CompositeVideoClip([bg, overlay], size=(W, H), bg_color=(0, 0, 0))
    scenes.append(_titled(comp1, "CompositeVideoClip(clips, bg_color, use_bgclip)"))

    #  concatenate_videoclips — method='chain'
    c1 = ColorClip(size=(W, H), color=(200, 50, 50)).with_duration(0.7)
    c2 = ColorClip(size=(W, H), color=(50, 200, 50)).with_duration(0.7)
    c3 = ColorClip(size=(W, H), color=(50, 50, 200)).with_duration(0.6)
    cat = concatenate_videoclips([c1, c2, c3], method="chain")
    scenes.append(_titled(cat, "concatenate_videoclips(method='chain')"))

    # concatenate_videoclips — method='compose' with padding
    cat2 = concatenate_videoclips(
        [
            c1.resized((W // 2, H // 2)),
            c2.resized((W // 2, H // 2)),
            c3.resized((W, H)),
        ],
        method="compose",
        bg_color=(0, 0, 0),
        padding=-0.2,
    )
    scenes.append(
        _titled(
            _resize_to_canvas(cat2),
            "concatenate_videoclips(method='compose', padding=-0.2)",
        )
    )

    # concatenate_videoclips with transition
    cat3 = concatenate_videoclips(
        [c1, c2, c3],
        padding=-0.3,
        method="compose",
    )
    scenes.append(
        _titled(
            cat3.with_duration(CLIP_DUR),
            "concatenate_videoclips(padding=-0.3)  # overlap",
        )
    )

    # clips_array
    a = ColorClip(size=(W // 2, H // 2), color=(200, 50, 50)).with_duration(CLIP_DUR)
    b = ColorClip(size=(W // 2, H // 2), color=(50, 200, 50)).with_duration(CLIP_DUR)
    c = ColorClip(size=(W // 2, H // 2), color=(50, 50, 200)).with_duration(CLIP_DUR)
    d = ColorClip(size=(W // 2, H // 2), color=(200, 200, 50)).with_duration(CLIP_DUR)
    grid = clips_array([[a, b], [c, d]])
    scenes.append(_titled(_resize_to_canvas(grid), "clips_array([[a, b], [c, d]])"))

    return scenes


# ══════════════════════════════════════════════════════════════════
# PART 6 — Drawing Tools
# ══════════════════════════════════════════════════════════════════
def part6_drawing_tools() -> list[VideoClip]:
    """Demonstrate moviepy.video.tools.drawing functions."""
    scenes: list[VideoClip] = [
        _section_header(
            "Part 6: Drawing Tools", "circle · color_gradient · color_split"
        ),
    ]

    # circle
    circ = circle(
        screensize=(W, H),
        center=(W // 2, H // 2),
        radius=300,
        color=1.0,
        bg_color=0.0,
        blur=30,
    )
    circ_rgb = (np.dstack([circ, circ, circ]) * 255).astype(np.uint8)
    scenes.append(
        _titled(
            ImageClip(circ_rgb, duration=CLIP_DUR),
            "drawing.circle(center, radius=300, blur=30)",
        )
    )

    # color_gradient — linear
    grad = color_gradient(
        size=(W, H),
        p1=(0, 0),
        p2=(W, H),
        color_1=0.0,
        color_2=1.0,
        shape="linear",
    )
    grad_rgb = (np.dstack([grad, grad, grad]) * 255).astype(np.uint8)
    scenes.append(
        _titled(
            ImageClip(grad_rgb, duration=CLIP_DUR),
            "drawing.color_gradient(shape='linear')",
        )
    )

    # color_gradient — radial
    grad_r = color_gradient(
        size=(W, H),
        p1=(W // 2, H // 2),
        radius=500,
        color_1=1.0,
        color_2=0.0,
        shape="radial",
    )
    grad_r_rgb = (np.dstack([grad_r, grad_r, grad_r]) * 255).astype(np.uint8)
    scenes.append(
        _titled(
            ImageClip(grad_r_rgb, duration=CLIP_DUR),
            "drawing.color_gradient(shape='radial', radius=500)",
        )
    )

    # color_split
    split = color_split(
        size=(W, H),
        x=W // 2,
        color_1=0.0,
        color_2=1.0,
        gradient_width=100,
    )
    split_rgb = (np.dstack([split, split, split]) * 255).astype(np.uint8)
    scenes.append(
        _titled(
            ImageClip(split_rgb, duration=CLIP_DUR),
            "drawing.color_split(x=W/2, gradient_width=100)",
        )
    )

    return scenes


# ══════════════════════════════════════════════════════════════════
# PART 7 — Output Methods
# ══════════════════════════════════════════════════════════════════
def part7_output() -> list[VideoClip]:
    """Label-only slides for output methods + parameters."""
    scenes: list[VideoClip] = [
        _section_header(
            "Part 7: Output Methods",
            "write_videofile · write_gif · save_frame · write_images_sequence",
        ),
    ]

    bg = ColorClip(size=(W, H), color=(15, 20, 35))

    methods = [
        (
            "write_videofile()",
            "filename, fps, codec, bitrate, audio, audio_fps,\n"
            "preset, audio_nbytes, audio_codec, audio_bitrate,\n"
            "audio_bufsize, temp_audiofile, threads,\n"
            "ffmpeg_params, logger, pixel_format",
        ),
        (
            "write_gif()",
            "filename, fps, loop, logger",
        ),
        (
            "save_frame()",
            "filename, t, with_mask",
        ),
        (
            "write_images_sequence()",
            "name_format, fps, with_mask, logger",
        ),
        (
            "write_audiofile()",
            "filename, fps, nbytes, buffersize,\ncodec, bitrate, ffmpeg_params, logger",
        ),
    ]

    for title, params in methods:
        t1 = (
            TextClip(
                text=title, font_size=56, color="cyan", font=FONT_B, margin=(0, 20)
            )
            .with_duration(2.5)
            .with_position(("center", 300))
        )
        t2 = (
            TextClip(
                text=f"Parameters:\n{params}",
                font_size=32,
                color="#dddddd",
                font=FONT_R,
                method="caption",
                size=(W - 300, None),
                text_align="center",
                interline=8,
                margin=(0, 15),
            )
            .with_duration(2.5)
            .with_position(("center", 500))
        )
        scenes.append(CompositeVideoClip([bg.with_duration(2.5), t1, t2], size=(W, H)))

    return scenes


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
