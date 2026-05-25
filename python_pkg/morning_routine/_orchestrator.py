"""Orchestrate the morning wake/workout flow as one sequential routine.

The wake alarm (``python_pkg.wake_alarm``) and the workout screen lock
(``python_pkg.screen_locker``) used to run as two independent
``graphical-session.target`` user services, each opening its own fullscreen
``-topmost`` Tk window. On a wake morning they could grab the screen at the same
time, so the alarm could end up hidden behind the workout lock (or vice versa).

This orchestrator makes them one coherent flow by running them as **sequential
subprocesses**: the alarm runs first and owns the fullscreen until it is
dismissed, then the workout lock runs. Only one fullscreen window is ever alive
at a time, so they can never collide. Each subprocess still self-gates (the
alarm only fires on alarm days when undismissed; the lock exits if a skip was
earned or the workout is already logged), so this is safe to run on every wake.

Usage:
    python -m python_pkg.morning_routine._orchestrator --with-alarm  # resume
    python -m python_pkg.morning_routine._orchestrator               # lock only
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys

_logger = logging.getLogger(__name__)

# Modules invoked as ``python -m <module> --production``.
ALARM_MODULE: str = "python_pkg.wake_alarm._alarm"
WORKOUT_LOCK_MODULE: str = "python_pkg.screen_locker.screen_lock"


def _run_module(module: str) -> int:
    """Run *module* as a blocking ``python -m`` subprocess in production mode.

    Args:
        module: Dotted module path to execute with ``python -m``.

    Returns:
        The subprocess exit code, or ``1`` when the process could not start.
    """
    cmd = [sys.executable, "-m", module, "--production"]
    _logger.info("morning-routine: running %s", module)
    try:
        result = subprocess.run(cmd, check=False)
    except OSError:
        _logger.warning("Failed to run %s", module, exc_info=True)
        return 1
    return result.returncode


def _run_alarm() -> int:
    """Run the wake alarm and block until it is dismissed (or self-exits)."""
    return _run_module(ALARM_MODULE)


def _run_workout_lock() -> int:
    """Run the workout screen lock after the alarm has been dealt with."""
    return _run_module(WORKOUT_LOCK_MODULE)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments for the orchestrator."""
    parser = argparse.ArgumentParser(description="Unified morning routine.")
    parser.add_argument(
        "--with-alarm",
        action="store_true",
        help="Run the wake alarm before the workout lock (used on resume).",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Production mode (kept for systemd/CLI symmetry).",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Entry point: optionally run the alarm, then always run the workout lock."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    args = _parse_args(sys.argv[1:])
    # Alarm first so it owns the fullscreen and escalates until dismissed; only
    # then hand off to the workout lock. Running them in this order in a single
    # process guarantees they never fight for the screen.
    if args.with_alarm:
        _run_alarm()
    _run_workout_lock()


if __name__ == "__main__":
    main()
