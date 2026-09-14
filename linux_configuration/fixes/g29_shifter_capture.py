#!/usr/bin/env python3
"""Record and grade raw Logitech G29 HID reports: which gate registered when.

``--record SECONDS`` reads the wheel's hidraw node (needs root) and writes
``xxd -c 12`` format, reopening if the device re-binds (attaching a HID-BPF
program does exactly that; a plain ``xxd`` silently exits there). Otherwise
input is such a file, or ``-`` for stdin: prints the gear/X/Y runs, every gear
on/off edge with the hall value at that instant, and a per-gate miss count --
a *miss* is a dwell in a gate (by raw X/Y) holding >= MIN_DWELL reports with
the gear bit clear. Byte layout: 0-3 hat+buttons (gears 1-6,R = byte 2 bits
0-6), 9/10 = shifter X/Y, 11 = flags (0x40 = pushed down). docs/DOCS-g29-shifter.md
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

REPORT_HZ = 400  # observed report rate, for the timestamps only
REPORT_LEN = 12
GEAR_BYTE = 2
GEAR_NAMES = ("1st", "2nd", "3rd", "4th", "5th", "6th", "R")
X_LEFT_MAX = 96
X_CENTRE_MAX = 151
Y_BOTTOM_MAX = 65  # raw Y at/below this: bottom row (matches the BPF engage line)
Y_TOP_MIN = 160  # raw Y at/above this: top row (matches the BPF engage line)
MIN_DWELL = 100  # reports (~0.25 s) a gate must be held to count as an attempt
ROW_TOP, ROW_BOTTOM = 0, 1
COL_LEFT, COL_CENTRE, COL_RIGHT = 0, 1, 2
DOWN_FLAG = 0x40

HIDRAW_LINK = "/dev/input/by-id/usb-Logitech_G29_Driving_Force_Racing_Wheel-hidraw"
REOPEN_WAIT_S = 0.2

_LINE = re.compile(r"^[0-9a-f]+: ((?:[0-9a-f]{4} ?){6})")


def record(seconds: float, device: str, out: Path) -> int:
    """Stream reports to ``out`` in xxd format for ``seconds``; return 0."""
    deadline = time.monotonic() + seconds
    offset = 0
    # Line-buffered so a capture can be inspected while it is still running.
    with out.open("w", encoding="ascii", buffering=1) as sink:
        while time.monotonic() < deadline:
            try:
                with Path(device).open("rb") as src:
                    while time.monotonic() < deadline:
                        raw = src.read(REPORT_LEN)
                        if len(raw) != REPORT_LEN:
                            break  # device re-bound; reopen below
                        words = " ".join(
                            raw[i : i + 2].hex() for i in range(0, REPORT_LEN, 2)
                        )
                        sink.write(f"{offset:08x}: {words}\n")
                        offset += REPORT_LEN
            except OSError as exc:  # unplugged, or racing a re-bind
                sys.stderr.write(f"reopening {device}: {exc}\n")
            time.sleep(REOPEN_WAIT_S)
    sys.stderr.write(f"recorded {offset // REPORT_LEN} reports to {out}\n")
    return 0


@dataclass(frozen=True)
class Report:
    """One decoded 12-byte input report."""

    gears: int  # bitmask, bit i = GEAR_NAMES[i]
    x: int
    y: int
    down: bool

    @property
    def gate(self) -> str | None:
        """Gate the stick is physically in, by raw X/Y (None = neutral)."""
        if self.y >= Y_TOP_MIN:
            row = ROW_TOP
        elif self.y <= Y_BOTTOM_MAX:
            row = ROW_BOTTOM
        else:
            return None
        col = (
            COL_LEFT
            if self.x <= X_LEFT_MAX
            else COL_CENTRE
            if self.x <= X_CENTRE_MAX
            else COL_RIGHT
        )
        if row == ROW_BOTTOM and col == COL_RIGHT and self.down:
            return "R"
        return GEAR_NAMES[col * 2 + row]


def parse(lines: Iterable[str]) -> Iterator[Report]:
    """Yield a Report per well-formed xxd line; skip anything else."""
    for line in lines:
        match = _LINE.match(line)
        if not match:
            continue
        # The pattern matches exactly six 2-byte words, so this is REPORT_LEN.
        raw = bytes.fromhex(match.group(1).replace(" ", ""))
        yield Report(
            gears=raw[GEAR_BYTE] & 0x7F,
            x=raw[9],
            y=raw[10],
            down=bool(raw[11] & DOWN_FLAG),
        )


def gear_label(mask: int) -> str:
    """Comma-joined gear names for a bitmask, or ``none``."""
    return ",".join(n for i, n in enumerate(GEAR_NAMES) if mask >> i & 1) or "none"


@dataclass
class Run:
    """Consecutive reports sharing one gear mask, with the X/Y range seen."""

    start: int
    mask: int
    length: int = 0
    x_min: int = 255
    x_max: int = 0
    y_min: int = 255
    y_max: int = 0

    def add(self, r: Report) -> None:
        """Extend the run by one report."""
        self.length += 1
        self.x_min, self.x_max = min(self.x_min, r.x), max(self.x_max, r.x)
        self.y_min, self.y_max = min(self.y_min, r.y), max(self.y_max, r.y)


def runs(reports: list[Report]) -> list[Run]:
    """Collapse consecutive reports with the same gear mask into runs."""
    out: list[Run] = []
    for i, r in enumerate(reports):
        if not out or out[-1].mask != r.gears:
            out.append(Run(start=i, mask=r.gears))
        out[-1].add(r)
    return out


def edges(reports: list[Report]) -> Iterator[tuple[int, str, bool, Report]]:
    """Yield ``(index, gear, on, report)`` for every gear bit transition."""
    prev = 0
    for i, r in enumerate(reports):
        changed = prev ^ r.gears
        for bit, name in enumerate(GEAR_NAMES):
            if changed >> bit & 1:
                yield i, name, bool(r.gears >> bit & 1), r
        prev = r.gears


def misses(reports: list[Report]) -> dict[str, tuple[int, int]]:
    """Per gate ``(attempts, misses)``; a miss is a MIN_DWELL stretch, bit clear."""
    stats = {name: [0, 0] for name in GEAR_NAMES}
    gate: str | None = None
    length = clear_streak = 0
    missed = False

    def close() -> None:
        if gate is not None and length >= MIN_DWELL:
            stats[gate][0] += 1
            stats[gate][1] += missed

    for r in reports:
        if r.gate != gate:
            close()
            gate, length, clear_streak, missed = r.gate, 0, 0, False
        length += 1
        if gate is None:
            continue
        registered = bool(r.gears >> GEAR_NAMES.index(gate) & 1)
        clear_streak = 0 if registered else clear_streak + 1
        missed = missed or clear_streak >= MIN_DWELL
    close()
    return {k: (v[0], v[1]) for k, v in stats.items()}


MIN_PRINTED_RUN = 20


def report(reports: list[Report], *, show_runs: bool, show_edges: bool) -> int:
    """Write the analysis to stdout; return 1 if any gate had a miss."""
    out = sys.stdout
    out.write(f"reports: {len(reports)}\n")
    if show_runs:
        for run in runs(reports):
            if run.length < MIN_PRINTED_RUN:
                continue
            out.write(
                f"t={run.start / REPORT_HZ:7.1f}s {run.length:6d}"
                f" {gear_label(run.mask):<8} X={run.x_min:3d}..{run.x_max:3d}"
                f" Y={run.y_min:3d}..{run.y_max:3d}\n"
            )
    if show_edges:
        for index, name, on, rep in edges(reports):
            state = "ON " if on else "off"
            out.write(
                f"{index / REPORT_HZ:7.1f}s {name} {state} X={rep.x:3d} Y={rep.y:3d}\n"
            )
    failed = False
    for name, (attempts, missed) in misses(reports).items():
        if attempts:
            out.write(f"{name:>4}: {attempts:3d} attempts, {missed} missed\n")
            failed = failed or missed > 0
    return int(failed)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("capture", help="xxd -c 12 output file, or - for stdin")
    parser.add_argument("--runs", action="store_true", help="print gear runs")
    parser.add_argument("--edges", action="store_true", help="print on/off edges")
    parser.add_argument(
        "--record",
        type=float,
        metavar="SECONDS",
        help="record to the capture file for this long first (needs root)",
    )
    parser.add_argument(
        "--device",
        default=HIDRAW_LINK,
        help="hidraw node to record from (default: the G29 by-id link)",
    )
    args = parser.parse_args(argv)
    if args.record:
        record(args.record, args.device, Path(args.capture))
    if args.capture == "-":
        reports = list(parse(sys.stdin))
    else:
        with Path(args.capture).open(encoding="ascii") as source:
            reports = list(parse(source))
    return report(reports, show_runs=args.runs, show_edges=args.edges)


if __name__ == "__main__":
    sys.exit(main())
