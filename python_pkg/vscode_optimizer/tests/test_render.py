"""Tests for the terminal output: the hardware summary and the plan listing.

These assert on the informational content of each line rather than its exact
decoration, so the ANSI escapes stay free to change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.vscode_optimizer import _render as opt
from python_pkg.vscode_optimizer._types import _Hw, _Opt

if TYPE_CHECKING:
    import pytest


def test_show_hw_reports_every_detected_component(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CPU, RAM, GPU and disk each appear, with RAM converted to GB."""
    hw = _Hw(
        cpu_model="AMD Ryzen 9 7900X3D",
        cpu_physical_cores=12,
        cpu_logical_cores=24,
        cpu_max_mhz=5662.6,
        ram_total_mb=30000,
        gpu_vendor="NVIDIA",
        gpu_model="GeForce RTX 3090",
        gpu_vram_mb=24576,
        disk_type="nvme",
    )

    opt._show_hw(hw)

    out = capsys.readouterr().out
    assert "AMD Ryzen 9 7900X3D" in out
    assert "12 cores / 24 threads" in out
    assert "5663 MHz" in out
    assert "29 GB" in out
    assert "NVIDIA - GeForce RTX 3090" in out
    assert "24576 MB VRAM" in out
    assert "NVME" in out


def test_show_hw_omits_vram_when_it_is_unknown(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A card whose VRAM could not be read shows no empty parentheses."""
    opt._show_hw(_Hw(gpu_vendor="AMD", gpu_model="Radeon"))

    assert "VRAM" not in capsys.readouterr().out


def test_show_plan_lists_new_flags_and_settings(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each proposed change is numbered and shows before -> after."""
    opts = [
        _Opt(
            key="editor.minimap.enabled",
            value=False,
            reason="Minimap costs GPU",
            current=True,
        )
    ]

    opt._show_plan(opts, ["--enable-zero-copy"], [])

    out = capsys.readouterr().out
    assert "--enable-zero-copy" in out
    assert "1. editor.minimap.enabled" in out
    assert "Minimap costs GPU" in out
    assert "true" in out
    assert "false" in out
    assert "2 change(s) proposed" in out


def test_show_plan_says_flags_are_already_present(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Flags that are all already set are reported, not listed as additions."""
    opt._show_plan([], ["--enable-zero-copy"], ["--enable-zero-copy"])

    out = capsys.readouterr().out
    assert "already present" in out
    assert "+ --enable-zero-copy" not in out


def test_show_plan_reports_a_fully_optimized_configuration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With nothing to change, the plan says so and proposes no count."""
    opt._show_plan([], [], [])

    out = capsys.readouterr().out
    assert "All settings already optimized" in out
    assert "change(s) proposed" not in out


def test_show_plan_renders_an_addition_with_no_previous_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A setting that was never set shows a dash as its 'before'."""
    opt._show_plan([_Opt("search.maxThreads", 12, "cores")], [], [])

    assert "-" in capsys.readouterr().out


def test_show_plan_truncates_very_long_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A large exclude dict is clipped so one setting cannot flood the screen."""
    big = {f"**/dir{i}": True for i in range(50)}

    opt._show_plan([_Opt("files.watcherExclude", big, "exclude", big)], [], [])

    for line in capsys.readouterr().out.splitlines():
        assert len(line) < 200
