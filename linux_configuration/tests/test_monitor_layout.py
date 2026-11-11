"""Tests for linux_configuration/features/monitor_layout.py (xrandr planner)."""

from __future__ import annotations

import io

import monitor_layout
from monitor_layout import Mode, parse_xrandr, pick_mode, plan
import pytest

AXES = "(normal left inverted right x axis y axis)"

# Real `xrandr --query` from 2026-11-11: DP-0 connected but switched off, the
# state that made kuhy's manual `xrandr --size` attempt fail.
DP0_OFF = f"""\
Screen 0: minimum 8 x 8, current 6400 x 1440, maximum 32767 x 32767
HDMI-0 connected 2560x1440+3840+0 {AXES} 698mm x 393mm
   2560x1440     59.95 + 143.98*  120.00
   3840x2160     59.94    50.00
   1920x1080    120.00   119.88   100.00    60.00    59.94    50.00
DP-0 connected primary {AXES}
   3840x2160     60.00 + 144.00   119.88   100.00    59.94    50.00
   2560x1440    144.00   120.00
   1920x1080    119.88    60.00    59.94    50.00
DP-1 disconnected {AXES}
DP-3 disconnected {AXES}
"""

# The same machine after the fix: both outputs at native size, max refresh.
BOTH_BEST = f"""\
Screen 0: minimum 8 x 8, current 6400 x 2160, maximum 32767 x 32767
HDMI-0 connected 2560x1440+3840+0 {AXES} 698mm x 393mm
   2560x1440     59.95 + 143.98*  120.00
   3840x2160     59.94    50.00
DP-0 connected primary 3840x2160+0+0 {AXES} 620mm x 340mm
   3840x2160     60.00 + 144.00*  119.88
DP-1 disconnected {AXES}
"""

# DP-0 unplugged while still holding a CRTC; HDMI-0 sits at +3840.
DP0_UNPLUGGED = f"""\
Screen 0: minimum 8 x 8, current 6400 x 2160, maximum 32767 x 32767
HDMI-0 connected 2560x1440+3840+0 {AXES} 698mm x 393mm
   2560x1440     59.95 + 143.98*  120.00
DP-0 disconnected primary 3840x2160+0+0 {AXES} 0mm x 0mm
"""

# A monitor whose EDID marks no preferred mode, with an interlaced mode too.
NO_PREFERRED = f"""\
Screen 0: minimum 8 x 8, current 3840 x 2160, maximum 32767 x 32767
DP-0 connected primary 3840x2160+0+0 {AXES} 620mm x 340mm
   3840x2160     60.00*+
DP-1 connected {AXES}
   1920x1080     60.00    75.00
   1920x1080i    120.00
   1280x1024     85.00
"""

HDMI_BEST = ["--output", "HDMI-0", "--mode", "2560x1440", "--rate", "143.98"]


class TestParse:
    """``parse_xrandr`` reads connection, primary, geometry and modes."""

    def test_connection_primary_and_geometry(self) -> None:
        """Off outputs have no geometry; on outputs report size and position."""
        outputs = {o.name: o for o in parse_xrandr(DP0_OFF)}
        assert outputs["DP-0"].connected
        assert outputs["DP-0"].primary
        assert outputs["DP-0"].geometry is None
        assert outputs["HDMI-0"].geometry == "2560x1440+3840+0"
        assert not outputs["DP-1"].connected

    def test_flags_separated_by_space(self) -> None:
        """``59.95 +`` marks 59.95 preferred; ``143.98*`` marks it current."""
        hdmi = next(o for o in parse_xrandr(DP0_OFF) if o.name == "HDMI-0")
        assert hdmi.preferred_size == (2560, 1440)
        assert hdmi.current == Mode(2560, 1440, "143.98")

    def test_combined_flags(self) -> None:
        """``60.00*+`` is both current and preferred."""
        dp0 = parse_xrandr(NO_PREFERRED)[0]
        assert dp0.current == Mode(3840, 2160, "60.00")
        assert dp0.preferred_size == (3840, 2160)


class TestPickMode:
    """Best mode = native (preferred) size at its highest refresh rate."""

    def test_native_size_beats_bigger_listed_size(self) -> None:
        """HDMI-0 lists 3840x2160@60 but its native 1440p@144 wins."""
        hdmi = next(o for o in parse_xrandr(DP0_OFF) if o.name == "HDMI-0")
        assert pick_mode(hdmi) == Mode(2560, 1440, "143.98")

    def test_highest_rate_at_preferred_size(self) -> None:
        """DP-0's preferred is 4K@60; 144 Hz at the same size is picked."""
        dp0 = next(o for o in parse_xrandr(DP0_OFF) if o.name == "DP-0")
        assert pick_mode(dp0) == Mode(3840, 2160, "144.00")

    def test_no_preferred_falls_back_to_largest_progressive(self) -> None:
        """Without ``+``: largest area, then fastest; interlaced skipped."""
        dp1 = parse_xrandr(NO_PREFERRED)[1]
        assert pick_mode(dp1) == Mode(1920, 1080, "75.00")


class TestPlan:
    """``plan`` returns xrandr args, or ``[]`` when nothing needs changing."""

    def test_turns_on_off_output_left_of_others(self) -> None:
        """The failing 2026-11-11 state: DP-0 on at 0x0, HDMI-0 to its right."""
        assert plan(parse_xrandr(DP0_OFF), "DP-0") == [
            "--output", "DP-0", "--mode", "3840x2160", "--rate", "144.00",
            "--pos", "0x0", "--primary",
            *HDMI_BEST, "--pos", "3840x0",
        ]  # fmt: skip

    def test_already_best_is_noop(self) -> None:
        """No xrandr call when every output already runs its best mode."""
        assert plan(parse_xrandr(BOTH_BEST), "DP-0") == []

    def test_unplugged_primary_is_turned_off_and_gap_closed(self) -> None:
        """HDMI-0 slides to 0x0 and becomes primary; DP-0 releases its CRTC."""
        assert plan(parse_xrandr(DP0_UNPLUGGED), "DP-0") == [
            *HDMI_BEST, "--pos", "0x0", "--primary",
            "--output", "DP-0", "--off",
        ]  # fmt: skip

    def test_unknown_primary_uses_first_connected(self) -> None:
        """A missing preferred primary falls back to xrandr order."""
        args = plan(parse_xrandr(DP0_OFF), "DP-9")
        assert args[:9] == [*HDMI_BEST, "--pos", "0x0", "--primary"]

    def test_nothing_connected_is_noop(self) -> None:
        """No connected output means no xrandr call at all."""
        assert plan(parse_xrandr("Screen 0: minimum 8 x 8\n"), "DP-0") == []


def test_main_prints_plan_for_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``xrandr | monitor_layout.py`` prints the plan without touching X."""
    monkeypatch.setattr(monitor_layout.sys, "stdin", io.StringIO(DP0_OFF))
    assert monitor_layout.main() == 0
    assert capsys.readouterr().out.split()[:3] == ["--output", "DP-0", "--mode"]
