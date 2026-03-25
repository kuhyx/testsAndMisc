"""Shared fixtures and moviepy mocking for praca_magisterska_video tests."""

from __future__ import annotations

import contextlib
import importlib
import importlib.util as _ilu
from pathlib import Path
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import numpy as np
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

# Add the source directory to sys.path so bare imports like
# ``from _q24_common import ...`` resolve correctly.
_SRC_DIR = str(Path(__file__).resolve().parent.parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# Also add generate_images/ so bare imports like ``from _pubsub_common import ...``
# used by sub-modules within that directory resolve correctly.
_GEN_DIR = str(Path(__file__).resolve().parent.parent / "generate_images")
if _GEN_DIR not in sys.path:
    sys.path.insert(0, _GEN_DIR)


def _make_moviepy_mocks() -> dict[str, ModuleType | MagicMock]:
    """Build a mapping of module names to mocks for moviepy and heavy deps."""
    mocks: dict[str, ModuleType | MagicMock] = {}

    # Main moviepy module
    moviepy_mod = MagicMock()

    # VideoClip: needs to accept make_frame callable -> return mock with methods
    def _video_clip_factory(
        make_frame: Callable[[float], np.ndarray] | None = None,
        duration: float | None = None,
        **_kw: object,
    ) -> MagicMock:
        clip = MagicMock()
        clip.make_frame = make_frame
        clip.duration = duration
        clip.with_fps.return_value = clip
        clip.with_duration.return_value = clip
        clip.with_position.return_value = clip
        clip.with_effects.return_value = clip
        # If there is a make_frame callable, call it to exercise branches
        if callable(make_frame) and duration is not None:
            frame = make_frame(0.0)
            assert isinstance(frame, np.ndarray)
            # Call at ~40% progress to hit mid-range branches (e.g. for/else break)
            make_frame(duration * 0.4)
            # Also call at ~70% progress for branch coverage
            make_frame(duration * 0.75)
            # Also call near end
            make_frame(duration * 0.99)
        return clip

    moviepy_mod.VideoClip = _video_clip_factory

    def _color_clip_factory(
        _size: tuple[int, int] | None = None,
        _color: tuple[int, ...] | None = None,
        **_kw: object,
    ) -> MagicMock:
        clip = MagicMock()
        clip.with_duration.return_value = clip
        return clip

    moviepy_mod.ColorClip = _color_clip_factory

    def _text_clip_factory(**_kw: object) -> MagicMock:
        clip = MagicMock()
        clip.with_duration.return_value = clip
        clip.with_position.return_value = clip
        return clip

    moviepy_mod.TextClip = _text_clip_factory

    def _composite_factory(
        _clips: list[MagicMock] | None = None,
        _size: tuple[int, int] | None = None,
        **_kw: object,
    ) -> MagicMock:
        clip = MagicMock()
        clip.with_effects.return_value = clip
        clip.with_duration.return_value = clip
        clip.write_videofile = MagicMock()
        return clip

    moviepy_mod.CompositeVideoClip = _composite_factory

    def _concat_factory(
        _clips: list[MagicMock] | None = None,
        _method: str | None = None,
        **_kw: object,
    ) -> MagicMock:
        clip = MagicMock()
        clip.write_videofile = MagicMock()
        return clip

    moviepy_mod.concatenate_videoclips = _concat_factory

    mocks["moviepy"] = moviepy_mod
    mocks["moviepy.video"] = MagicMock()
    mocks["moviepy.video.fx"] = MagicMock()

    return mocks


# Install mocks at import time so module-level code in source files works.
_MOVIEPY_MOCKS = _make_moviepy_mocks()
for _name, _mock in _MOVIEPY_MOCKS.items():
    sys.modules[_name] = _mock


# ---------------------------------------------------------------------------
# Handle the _q24_common name collision.
# Both _SRC_DIR (top-level) and _GEN_DIR (generate_images/) contain a
# file called ``_q24_common.py`` with different contents.
#  * top-level  → moviepy video helpers  (W, H, BG_COLOR, FONT_B, …)
#  * gen_images → matplotlib draw helpers (draw_box, draw_arrow, …)
#
# Strategy:
#  1. Load the generate_images version and cache it as bare ``_q24_common``
#     so generate_images sub-modules (imported in _BARE_MODULES below)
#     find the right one when they do ``from _q24_common import draw_box``.
#  2. After _BARE_MODULES are all imported, swap ``_q24_common`` in
#     sys.modules to the top-level version so that top-level source
#     modules (``_q24_classical.py``, etc.) find ``BG_COLOR`` etc.
#  3. Register both under their full package paths for coverage.
# ---------------------------------------------------------------------------

# Load generate_images _q24_common first.
_gen_q24_spec = _ilu.spec_from_file_location(
    "_q24_common",
    str(Path(_GEN_DIR) / "_q24_common.py"),
)
assert _gen_q24_spec is not None
assert _gen_q24_spec.loader is not None
_q24_common_gen = _ilu.module_from_spec(_gen_q24_spec)
# Register BEFORE exec so @dataclass can resolve __module__ in Python 3.14+.
sys.modules["_q24_common"] = _q24_common_gen
_gen_q24_spec.loader.exec_module(_q24_common_gen)

# Load top-level _q24_common.
_top_q24_spec = _ilu.spec_from_file_location(
    "_q24_common_top",
    str(Path(_SRC_DIR) / "_q24_common.py"),
)
assert _top_q24_spec is not None
assert _top_q24_spec.loader is not None
_q24_common_top = _ilu.module_from_spec(_top_q24_spec)
# Register BEFORE exec so @dataclass can resolve __module__ in Python 3.14+.
sys.modules["_q24_common_top"] = _q24_common_top
_top_q24_spec.loader.exec_module(_q24_common_top)


# Register generate_images sub-modules under their full package paths so
# coverage can track them correctly.  The bare names are resolved via
# _GEN_DIR added to sys.path above.
_GEN_PKG = "python_pkg.praca_magisterska_video.generate_images"
_BARE_MODULES = [
    "_pubsub_common",
    "_pubsub_qos",
    "_pubsub_topic_content",
    "_pubsub_type_hierarchical",
    "_q20_common",
    "_q20_batch_and_windows",
    "_q20_time_monitoring_sessions",
    "_q20_platforms",
    "_q20_architectures",
    "_q20_late_and_decisions",
    "generate_pubsub_diagrams",
    "generate_q20_diagrams",
    "_q23_common",
    "_q23_architectures",
    "_q23_diy_unet",
    "_q23_mean_shift_ncuts",
    "_q23_mnemonics",
    "_q23_nn_basics",
    "_q23_otsu_watershed",
    "_q23_receptive_transformer",
    "_q23_region_diy",
    "generate_q23_diagrams",
    "_q24_fpn_tasks_cnn",
    "_q24_haar_integral_svm",
    "_q24_hog_classical",
    "_q24_iou_nms_detector",
    "_q24_modern_pipelines",
    "_q24_rcnn_yolo",
    "generate_q24_diagrams",
    "_q31_common",
    "_q31_criteria_comparison",
    "_q31_ev_spectrum",
    "_q31_hurwicz_mnemonic",
    "_q31_regret_matrix",
    "generate_q31_diagrams",
    "_q9_common",
    "_q9_basics",
    "_q9_classic_sync",
    "_q9_ipc",
    "_q9_race_deadlock",
    "generate_q9_all_diagrams",
    "_q9q12_common",
    "_q9q12_network_flow",
    "_q9q12_network_graph",
    "_q9q12_processes",
    "generate_q9_q12_diagrams",
    "generate_robot_lang_diagrams",
    "_robot_movement_ros",
    "_robot_pyramid_vendor",
    "_robot_ros_rapid",
    "_sched_common",
    "_sched_complexity_edd",
    "_sched_graham",
    "_sched_johnson",
    "_sched_spt_flow_job",
    "generate_scheduling_diagrams",
]
for _bare in _BARE_MODULES:
    with contextlib.suppress(ImportError):
        _mod = importlib.import_module(_bare)
        sys.modules.setdefault(f"{_GEN_PKG}.{_bare}", _mod)

# Now swap _q24_common to the top-level version so that top-level source
# modules (``_q24_classical.py`` etc.) find BG_COLOR, W, H, etc.
sys.modules["_q24_common"] = _q24_common_top
sys.modules.setdefault(
    "python_pkg.praca_magisterska_video._q24_common", _q24_common_top
)
sys.modules.setdefault(f"{_GEN_PKG}._q24_common", _q24_common_gen)


def reload_module(module_name: str) -> ModuleType:
    """Force re-import of a module to re-execute its module-level code."""
    mod = importlib.import_module(module_name)
    return importlib.reload(mod)


@pytest.fixture
def _no_savefig(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent matplotlib from writing files to disk."""
    import matplotlib.figure
    import matplotlib.pyplot as plt
    import matplotlib.table

    monkeypatch.setattr(matplotlib.figure.Figure, "savefig", lambda *_a, **_kw: None)
    monkeypatch.setattr(plt, "savefig", lambda *_a, **_kw: None)

    # Source files use auto_set_font_size(auto=False) but matplotlib 3.10+
    # renamed the parameter to ``value``.
    _orig = matplotlib.table.Table.auto_set_font_size

    def _compat_auto_set_font_size(
        self: matplotlib.table.Table,
        *,
        value: bool = True,
        **_kw: object,
    ) -> None:
        _orig(self, value)

    monkeypatch.setattr(
        matplotlib.table.Table,
        "auto_set_font_size",
        _compat_auto_set_font_size,
    )
