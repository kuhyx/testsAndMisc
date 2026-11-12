#!/usr/bin/env python3
"""Keep every connected monitor at its best mode, re-applied on hotplug.

Runs as the ``monitor-autoconfig`` systemd user service (installed by
``setup_monitor_autoconfig.sh``). It listens for X RandR output-change
events instead of a udev rule: no root, nothing in /etc, and a systemd
unit cannot be (re)started from a udev ``change`` event reliably.

Usage:
    monitor_autoconfig.py              # apply now, then watch for hotplug
    monitor_autoconfig.py --once       # apply now and exit
    monitor_autoconfig.py --dry-run    # print the xrandr command only
"""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Protocol

from monitor_layout import parse_xrandr, plan

if TYPE_CHECKING:
    from collections.abc import Callable

    from monitor_layout import Output

# Xlib.ext.randr.RROutputChangeNotifyMask; fires on connect and disconnect.
# CRTC events are left out on purpose: they fire on every mode switch, so
# listening to them would undo a game's or kuhy's own deliberate xrandr change.
OUTPUT_CHANGE_MASK = 4
# A freshly plugged monitor can take a moment before its EDID modes show up.
SETTLE_SECONDS = 1.0
# How many settle periods to wait for a connected monitor to list any mode.
MODE_TRIES = 5
# At boot the user manager starts this unit while LightDM's greeter still owns
# :0, so X refuses us until kuhy logs in. Wait for that instead of exiting:
# exiting burned the restart limit in 15 s on 2026-11-12 and left DP-2 dark.
CONNECT_WAIT = 2.0


class _Root(Protocol):
    """Root window: takes the RandR event mask."""

    def xrandr_select_input(self, mask: int) -> object:
        """Subscribe to RandR events."""


class _Screen(Protocol):
    """Screen: exposes its root window."""

    root: _Root


class Display(Protocol):
    """The slice of ``Xlib.display.Display`` the watcher uses."""

    def screen(self) -> _Screen:
        """Default screen; its ``root`` window takes the event mask."""

    def next_event(self) -> object:
        """Block until the next X event arrives."""

    def pending_events(self) -> int:
        """Number of events already queued."""

    def xrandr_query_version(self) -> object:
        """RandR version handshake."""


def _run(argv: list[str]) -> str:
    """Run a command, return stdout; raise on non-zero exit."""
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def _settle() -> None:
    """Give a just-plugged monitor time to publish its EDID modes."""
    time.sleep(SETTLE_SECONDS)


def _query(
    run: Callable[[list[str]], str], settle: Callable[[], None], tries: int
) -> list[Output]:
    """Query xrandr, re-asking while a connected monitor still lists no mode."""
    outputs = parse_xrandr(run(["xrandr", "--query"]))
    for _ in range(tries - 1):
        if all(o.modes for o in outputs if o.connected):
            break
        settle()
        outputs = parse_xrandr(run(["xrandr", "--query"]))
    return outputs


def apply_once(
    primary: str | None,
    run: Callable[[list[str]], str] = _run,
    settle: Callable[[], None] = _settle,
    tries: int = MODE_TRIES,
) -> bool:
    """Apply the best layout; return whether xrandr had to change anything."""
    args = plan(_query(run, settle, tries), primary)
    if not args:
        return False
    run(["xrandr", *args])
    sys.stdout.write(" ".join(["applied: xrandr", *args]) + "\n")
    sys.stdout.flush()
    return True


def _safe_apply(
    primary: str | None, run: Callable[[list[str]], str], settle: Callable[[], None]
) -> None:
    """Apply, but log a failed xrandr instead of dying.

    One bad monitor must not stop every later hotplug from being handled.
    """
    try:
        apply_once(primary, run, settle)
    except subprocess.CalledProcessError as error:
        sys.stderr.write(f"xrandr failed ({error.returncode}): {error.stderr}\n")


def _open_display(sleep: Callable[[float], None] = time.sleep) -> Display:
    """Connect to ``$DISPLAY``, waiting as long as X refuses (greeter, no login).

    Xlib is imported lazily so the tests never need it.
    """
    xlib_display = importlib.import_module("Xlib.display")
    refused = importlib.import_module("Xlib.error").DisplayConnectionError
    while True:
        try:
            display: Display = xlib_display.Display()
        except refused:
            sleep(CONNECT_WAIT)
        else:
            return display


def watch(
    primary: str | None,
    display: Display | None = None,
    run: Callable[[list[str]], str] = _run,
    settle: Callable[[], None] = _settle,
) -> None:
    """Apply now, then once per burst of RandR output events, forever."""
    display = display or _open_display()
    # Without announcing RandR >= 1.2 the server never sends output events.
    display.xrandr_query_version()
    display.screen().root.xrandr_select_input(OUTPUT_CHANGE_MASK)
    _safe_apply(primary, run, settle)
    while True:
        display.next_event()
        settle()
        # Our own xrandr call and multi-output plugs emit several events;
        # drain them so one burst costs one re-plan.
        while display.pending_events():
            display.next_event()
        _safe_apply(primary, run, settle)


def main(argv: list[str] | None = None, run: Callable[[list[str]], str] = _run) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--primary", default=None, help="leftmost primary (default: biggest)"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="apply and exit")
    mode.add_argument("--dry-run", action="store_true", help="print, change nothing")
    args = parser.parse_args(argv)
    if args.dry_run:
        planned = plan(_query(run, _settle, MODE_TRIES), args.primary)
        sys.stdout.write(" ".join(["xrandr", *planned]) + "\n")
    elif args.once:
        apply_once(args.primary, run)
    else:
        watch(args.primary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
