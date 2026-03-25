"""Mock moviepy modules for all moviepy_showcase tests.

This module-level setup installs mock moviepy packages into sys.modules
so source modules can be imported without moviepy installed.
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest

_H, _W = 1080, 1920


def create_mock_clip(**overrides: float | tuple[int, int]) -> MagicMock:
    """Return a MagicMock that behaves enough like a moviepy clip."""
    clip = MagicMock()
    clip.duration = overrides.get("duration", 2.0)
    clip.size = overrides.get("size", (_W, _H))
    clip.fps = overrides.get("fps", 30)
    chain = [
        "with_fps",
        "with_duration",
        "with_position",
        "with_opacity",
        "with_mask",
        "with_audio",
        "with_effects",
        "with_background_color",
        "with_speed_scaled",
        "with_section_cut_out",
        "with_effects_on_subclip",
        "with_layer_index",
        "with_volume_scaled",
        "with_start",
        "subclipped",
        "cropped",
        "resized",
        "rotated",
        "image_transform",
        "transform",
        "time_transform",
        "to_ImageClip",
        "to_mask",
        "to_RGB",
    ]
    for name in chain:
        getattr(clip, name).return_value = clip
    return clip


# ── Build mock module tree ────────────────────────────────────────
mock_moviepy = MagicMock()

_clip_classes = [
    "VideoClip",
    "ColorClip",
    "TextClip",
    "ImageClip",
    "CompositeVideoClip",
    "VideoFileClip",
    "BitmapClip",
    "DataVideoClip",
    "ImageSequenceClip",
    "AudioClip",
    "AudioArrayClip",
    "CompositeAudioClip",
]
for _cls in _clip_classes:
    getattr(mock_moviepy, _cls).side_effect = lambda *_a, **_kw: create_mock_clip()

mock_moviepy.concatenate_videoclips.side_effect = lambda *_a, **_kw: create_mock_clip()
mock_moviepy.concatenate_audioclips.side_effect = lambda *_a, **_kw: create_mock_clip()
mock_moviepy.video.compositing.CompositeVideoClip.clips_array.side_effect = (
    lambda *_a, **_kw: create_mock_clip()
)

# Drawing tools must return real numpy arrays (used in numpy ops)
mock_moviepy.video.tools.drawing.circle.return_value = np.zeros(
    (_H, _W), dtype=np.float64
)
mock_moviepy.video.tools.drawing.color_gradient.return_value = np.zeros(
    (_H, _W), dtype=np.float64
)
mock_moviepy.video.tools.drawing.color_split.return_value = np.zeros(
    (_H, _W), dtype=np.float64
)

# ── Install into sys.modules ─────────────────────────────────────
_module_paths = [
    "moviepy",
    "moviepy.video",
    "moviepy.video.fx",
    "moviepy.video.compositing",
    "moviepy.video.compositing.CompositeVideoClip",
    "moviepy.video.tools",
    "moviepy.video.tools.drawing",
    "moviepy.audio",
    "moviepy.audio.fx",
]


def _install_moviepy_mocks() -> None:
    """(Re)install this conftest's moviepy mocks into sys.modules."""
    for _mod in _module_paths:
        parts = _mod.split(".")
        obj: Any = mock_moviepy
        for part in parts[1:]:
            obj = getattr(obj, part)
        sys.modules[_mod] = obj


_install_moviepy_mocks()


@pytest.fixture(autouse=True)
def _reinstall_moviepy_mocks() -> None:
    """Ensure our moviepy mocks are active even if another conftest overwrote."""
    _install_moviepy_mocks()
