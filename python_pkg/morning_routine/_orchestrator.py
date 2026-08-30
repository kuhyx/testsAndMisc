"""Run the morning workout lock, started at the phone's alarm time.

This used to sequence two fullscreen Tk windows: the PC wake alarm first, then
the workout screen lock. The PC no longer wakes anyone -- the phone does, and
`wake_alarm._alarm` has been deleted -- so there is only one leg left and no
collision left to prevent.

What still points here: `wake-alarm-trigger.timer` ticks every minute and
starts `morning-routine.service` at the synced alarm time
(`wake_alarm._constants.TRIGGER_TARGET_UNIT`). Keeping this indirection means
that unit name stays true, and the workout lock keeps its own gates.

``screen_locker`` is pip-installed into system Python's user site-packages by
its own install.sh, so ``python -m <module>`` resolves it with no extra
``PYTHONPATH``/``cwd`` plumbing here.

Usage:
    python -m python_pkg.morning_routine._orchestrator
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys

from python_pkg.shared.logging_setup import configure_logging

_logger = logging.getLogger(__name__)

# Modules invoked as ``python -m <module> --production``.
WORKOUT_LOCK_MODULE: str = "screen_locker.screen_lock"


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


def _run_workout_lock() -> int:
    """Run the workout screen lock after the alarm has been dealt with."""
    return _run_module(WORKOUT_LOCK_MODULE)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments for the orchestrator."""
    parser = argparse.ArgumentParser(description="Unified morning routine.")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Production mode (kept for systemd/CLI symmetry).",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Entry point: run the workout lock."""
    configure_logging()
    _parse_args(sys.argv[1:])
    _run_workout_lock()


if __name__ == "__main__":
    main()
