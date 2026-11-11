#!/usr/bin/env python3
"""Plan an xrandr layout: every monitor at its best mode, side by side.

Pure functions only (text in, argument list out) so the policy is testable
without an X server; ``monitor_autoconfig.py`` does the I/O. Run directly,
``xrandr --query | monitor_layout.py`` prints the plan for any xrandr dump.

Policy, agreed 2026-11-11:
- best mode = the monitor's native (EDID-preferred, ``+``) size at the
  highest refresh rate offered for that size. A bigger listed size is a
  downscale, not "better". Without a preferred mode: largest area, then
  fastest, interlaced modes skipped.
- layout = one row at y=0; the preferred primary (default DP-0) leftmost,
  the rest in xrandr order to its right. If it is absent, the first
  connected output is primary.
- disconnected outputs that still hold a CRTC are switched off, so no gap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import sys

_HEADER = re.compile(
    r"^(?P<name>\S+) (?P<state>connected|disconnected)(?P<primary> primary)?"
    r"(?: (?P<geometry>\d+x\d+\+\d+\+\d+))?"
)
_MODE_LINE = re.compile(r"^\s+(?P<w>\d+)x(?P<h>\d+)(?P<suffix>\S*)\s+(?P<rates>.*)$")
# "59.95 +", "143.98*", "60.00*+": the + may sit one space after the rate.
_RATE = re.compile(r"(?P<rate>\d+\.\d+)(?P<current>\*?) ?(?P<preferred>\+?)")


@dataclass(frozen=True)
class Mode:
    """One resolution + refresh rate, rate kept as xrandr prints it."""

    width: int
    height: int
    rate: str

    @property
    def size(self) -> str:
        """``WxH`` as xrandr's ``--mode`` expects."""
        return f"{self.width}x{self.height}"


@dataclass
class Output:
    """One xrandr output and the modes its monitor offers."""

    name: str
    connected: bool
    primary: bool
    geometry: str | None
    modes: list[Mode] = field(default_factory=list)
    current: Mode | None = None
    preferred_size: tuple[int, int] | None = None


def _add_mode_line(output: Output, match: re.Match[str]) -> None:
    """Record every rate of one mode line, plus its ``*``/``+`` flags."""
    width, height = int(match["w"]), int(match["h"])
    interlaced = match["suffix"].startswith("i")
    for rate in _RATE.finditer(match["rates"]):
        mode = Mode(width, height, rate["rate"])
        if not interlaced:
            output.modes.append(mode)
        if rate["current"]:
            output.current = mode
        if rate["preferred"]:
            output.preferred_size = (width, height)


def parse_xrandr(text: str) -> list[Output]:
    """Parse ``xrandr --query`` output into outputs, in xrandr order."""
    outputs: list[Output] = []
    for line in text.splitlines():
        header = _HEADER.match(line)
        if header:
            outputs.append(
                Output(
                    name=header["name"],
                    connected=header["state"] == "connected",
                    primary=bool(header["primary"]),
                    geometry=header["geometry"],
                )
            )
            continue
        mode_line = _MODE_LINE.match(line)
        if mode_line and outputs:
            _add_mode_line(outputs[-1], mode_line)
    return outputs


def pick_mode(output: Output) -> Mode | None:
    """Native size at max refresh; else largest area at max refresh."""
    candidates = output.modes
    if output.preferred_size:
        native = [m for m in candidates if (m.width, m.height) == output.preferred_size]
        candidates = native or candidates
    if not candidates:
        return None
    return max(candidates, key=lambda m: (m.width * m.height, float(m.rate)))


def _ordered(outputs: list[Output], primary: str) -> list[tuple[Output, Mode]]:
    """Connected outputs with a usable mode, preferred primary first."""
    usable = [(o, m) for o in outputs if o.connected and (m := pick_mode(o))]
    usable.sort(key=lambda pair: pair[0].name != primary)
    return usable


def plan(outputs: list[Output], primary: str) -> list[str]:
    """Return the xrandr arguments to reach the policy, ``[]`` if already there."""
    row = _ordered(outputs, primary)
    args: list[str] = []
    changed = False
    x = 0
    for index, (output, mode) in enumerate(row):
        is_primary = index == 0
        args += ["--output", output.name, "--mode", mode.size, "--rate", mode.rate]
        args += ["--pos", f"{x}x0"] + (["--primary"] if is_primary else [])
        wanted_geometry = f"{mode.size}+{x}+0"
        changed |= output.current != mode or output.geometry != wanted_geometry
        changed |= output.primary != is_primary
        x += mode.width
    for output in outputs:
        if not output.connected and output.geometry:
            args += ["--output", output.name, "--off"]
            changed = True
    return args if changed else []


def main() -> int:
    """Print the plan for ``xrandr --query`` text read from stdin."""
    sys.stdout.write(" ".join(plan(parse_xrandr(sys.stdin.read()), "DP-0")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
