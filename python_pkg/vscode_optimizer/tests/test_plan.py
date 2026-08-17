"""Tests for the pure planning layer: memory sizing, dict merges, the
settings plan, and the Electron GPU flags.

Nothing here touches the filesystem or a subprocess: every function under
test maps hardware plus current settings to a proposed change.
"""

from __future__ import annotations

import pytest

from python_pkg.vscode_optimizer import _optimize as opt


def _opts_by_key(opts: list[opt._Opt]) -> dict[str, object]:
    """Index a plan by setting key, for assertions that ignore ordering."""
    return {o.key: o.value for o in opts}


# --------------------------------------------------------------------------- #
# _ideal_mem
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("ram_mb", "expected"),
    [
        (32000, 4096),
        (28000, 4096),
        (27999, 2048),
        (14000, 2048),
        (13999, 1024),
        (7000, 1024),
        (6999, 512),
        (0, 512),
    ],
)
def test_ideal_mem_picks_the_band_for_the_installed_ram(
    ram_mb: int, expected: int
) -> None:
    """Each threshold is inclusive, and anything below the last one defaults."""
    assert opt._ideal_mem(ram_mb) == expected


# --------------------------------------------------------------------------- #
# _dict_merge_opt
# --------------------------------------------------------------------------- #
def test_dict_merge_opt_returns_none_when_every_key_is_present() -> None:
    """A superset of the ideal keys needs no change, whatever the values."""
    current = {"search.exclude": {"**/node_modules": True, "**/extra": False}}

    result = opt._dict_merge_opt(
        current, "search.exclude", {"**/node_modules": True}, "reason"
    )

    assert result is None


def test_dict_merge_opt_preserves_user_entries_while_adding_missing_ones() -> None:
    """The merge is additive: existing keys survive alongside the ideal set."""
    current = {"search.exclude": {"**/mine": True}}

    result = opt._dict_merge_opt(
        current, "search.exclude", {"**/node_modules": True}, "reason"
    )

    assert result is not None
    assert result.value == {"**/mine": True, "**/node_modules": True}
    assert result.current == {"**/mine": True}


def test_dict_merge_opt_replaces_a_non_dict_current_value() -> None:
    """A malformed setting (not an object) is treated as empty, not merged."""
    result = opt._dict_merge_opt(
        {"search.exclude": "oops"}, "search.exclude", {"**/x": True}, "reason"
    )

    assert result is not None
    assert result.value == {"**/x": True}
    assert result.current is None


def test_dict_merge_opt_reports_no_current_value_when_the_key_is_absent() -> None:
    """A missing key yields a plain add with nothing to show as 'before'."""
    result = opt._dict_merge_opt({}, "search.exclude", {"**/x": True}, "reason")

    assert result is not None
    assert result.current is None


# --------------------------------------------------------------------------- #
# _compute_opts
# --------------------------------------------------------------------------- #
def test_compute_opts_scales_threads_and_memory_to_the_hardware() -> None:
    """Physical cores drive search threads; RAM drives the large-file budget."""
    hw = opt._Hw(cpu_physical_cores=12, ram_total_mb=32000)

    plan = _opts_by_key(opt._compute_opts(hw, {}))

    assert plan["search.maxThreads"] == 12
    assert plan["files.maxMemoryForLargeFilesMB"] == 4096


def test_compute_opts_keeps_a_floor_under_search_threads() -> None:
    """A dual-core machine still gets the four-thread minimum."""
    hw = opt._Hw(cpu_physical_cores=2)

    plan = _opts_by_key(opt._compute_opts(hw, {}))

    assert plan["search.maxThreads"] == opt._MIN_THREADS


def test_compute_opts_enables_gpu_extras_for_a_dedicated_card() -> None:
    """A discrete GPU turns on terminal acceleration and smooth scrolling."""
    hw = opt._Hw(gpu_vendor="NVIDIA")

    plan = _opts_by_key(opt._compute_opts(hw, {}))

    assert plan["terminal.integrated.gpuAcceleration"] == "on"
    assert plan["editor.smoothScrolling"] is True
    assert plan["workbench.list.smoothScrolling"] is True
    assert plan["terminal.integrated.smoothScrolling"] is True


def test_compute_opts_leaves_gpu_extras_alone_without_a_dedicated_card() -> None:
    """Integrated or unknown graphics get no GPU-dependent settings."""
    plan = _opts_by_key(opt._compute_opts(opt._Hw(gpu_vendor="Intel"), {}))

    assert "terminal.integrated.gpuAcceleration" not in plan
    assert "editor.smoothScrolling" not in plan


def test_compute_opts_proposes_nothing_already_set() -> None:
    """Settings that already hold the ideal value are not re-proposed."""
    hw = opt._Hw(cpu_physical_cores=8, ram_total_mb=32000)
    current: dict[str, object] = {
        "search.maxThreads": 8,
        "files.maxMemoryForLargeFilesMB": 4096,
        "search.followSymlinks": False,
        "editor.guides.bracketPairs": "active",
        "diffEditor.maxComputationTime": 0,
        "editor.minimap.enabled": False,
        "files.watcherExclude": dict(opt._WATCHER_EX),
        "search.exclude": dict(opt._SEARCH_EX),
        "git.detectSubmodulesLimit": opt._SUBMOD_LIMIT,
    }

    assert opt._compute_opts(hw, current) == []


@pytest.mark.parametrize(
    ("current_limit", "proposed"),
    [
        (None, True),
        (10, True),
        (opt._SUBMOD_LIMIT, False),
        (99, False),
        ("many", False),
    ],
)
def test_compute_opts_raises_only_a_low_submodule_limit(
    current_limit: object, *, proposed: bool
) -> None:
    """The limit is raised when unset or too low, and left alone otherwise."""
    current: dict[str, object] = (
        {} if current_limit is None else {"git.detectSubmodulesLimit": current_limit}
    )

    plan = _opts_by_key(opt._compute_opts(opt._Hw(), current))

    assert ("git.detectSubmodulesLimit" in plan) is proposed


def test_compute_opts_records_the_previous_value_for_display() -> None:
    """Each proposed change carries the value it replaces, for the diff."""
    current: dict[str, object] = {"editor.minimap.enabled": True}

    minimap = next(
        o
        for o in opt._compute_opts(opt._Hw(), current)
        if o.key == "editor.minimap.enabled"
    )

    assert minimap.current is True
    assert minimap.value is False


# --------------------------------------------------------------------------- #
# _gpu_flags
# --------------------------------------------------------------------------- #
def test_gpu_flags_adds_a_video_decode_flag_only_for_nvidia() -> None:
    """NVIDIA gets the VAAPI extras on top of the shared rasterization flags."""
    nvidia = opt._gpu_flags(opt._Hw(gpu_vendor="NVIDIA"))
    amd = opt._gpu_flags(opt._Hw(gpu_vendor="AMD"))

    assert "--enable-gpu-rasterization" in nvidia
    assert "--enable-zero-copy" in nvidia
    assert any("VaapiVideoEncoder" in f for f in nvidia)
    assert not any("VaapiVideoEncoder" in f for f in amd)


def test_gpu_flags_gives_intel_a_reduced_set() -> None:
    """Intel gets rasterization and decode, but not zero-copy."""
    flags = opt._gpu_flags(opt._Hw(gpu_vendor="Intel"))

    assert "--enable-gpu-rasterization" in flags
    assert "--enable-zero-copy" not in flags


def test_gpu_flags_are_empty_for_an_unknown_gpu() -> None:
    """No flags are forced on hardware the script could not identify."""
    assert opt._gpu_flags(opt._Hw()) == []
