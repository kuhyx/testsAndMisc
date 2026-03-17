"""MoviePy showcase — Part 4 (Audio), 5 (Composition), 6 (Drawing), 7 (Output)."""

from __future__ import annotations

from moviepy import (
    AudioArrayClip,
    AudioClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoClip,
    concatenate_audioclips,
    concatenate_videoclips,
)
from moviepy.audio.fx import (
    AudioDelay,
    AudioFadeIn,
    AudioFadeOut,
    AudioLoop,
    AudioNormalize,
    MultiplyStereoVolume,
    MultiplyVolume,
)
from moviepy.video.compositing.CompositeVideoClip import clips_array
from moviepy.video.tools.drawing import (
    circle,
    color_gradient,
    color_split,
)
import numpy as np

from moviepy_showcase import (
    CLIP_DUR,
    FONT_B,
    FONT_R,
    H,
    W,
    _base_clip,
    _resize_to_canvas,
    _section_header,
    _titled,
)


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
