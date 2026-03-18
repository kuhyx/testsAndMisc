"""MoviePy showcase — Part 3 (all 34 Video Effects)."""

from __future__ import annotations

from moviepy import (
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
)
from moviepy.video.fx import (
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
from moviepy.video.tools.drawing import circle
import numpy as np

from python_pkg.moviepy_showcase.moviepy_showcase import (
    CLIP_DUR,
    H,
    W,
    _base_clip,
    _resize_to_canvas,
    _section_header,
    _titled,
)


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


def _part3_effects_1_to_17() -> list[VideoClip]:
    """Video effects 1-17: AccelDecel through MakeLoopable."""
    scenes: list[VideoClip] = []

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
                fx=lambda _: W // 2,
                fy=lambda _: H // 2,
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

    return scenes


def _part3_effects_18_to_34() -> list[VideoClip]:
    """Video effects 18-34: Margin through TimeSymmetrize."""
    scenes: list[VideoClip] = []

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


def part3_video_effects() -> list[VideoClip]:
    """Demonstrate all 34 video effects."""
    scenes: list[VideoClip] = [
        _section_header(
            "Part 3: Video Effects",
            "All 34 effects from moviepy.video.fx",
        ),
    ]
    scenes.extend(_part3_effects_1_to_17())
    scenes.extend(_part3_effects_18_to_34())
    return scenes
