"""MoviePy showcase — Part 1 (Clip Types) and Part 2 (Clip Methods)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from moviepy import (
    BitmapClip,
    ColorClip,
    CompositeVideoClip,
    DataVideoClip,
    ImageClip,
    ImageSequenceClip,
    TextClip,
    VideoClip,
)
from moviepy.video.fx import InvertColors
from moviepy.video.tools.drawing import circle
import numpy as np

from moviepy_showcase import (
    CLIP_DUR,
    FONT_B,
    FONT_R,
    FPS,
    H,
    W,
    _base_clip,
    _gradient,
    _resize_to_canvas,
    _section_header,
    _titled,
)

if TYPE_CHECKING:
    from collections.abc import Callable


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
