#!/usr/bin/env python3
"""Background daemon for automatic brightness adjustment via ambient light sensor.

Reads the IIO ambient light sensor periodically and adjusts screen backlight
using brightnessctl. Designed to run as a systemd user service.

Usage:
    python -m python_pkg.brightness_controller.auto_brightness_daemon
    # or directly:
    ./auto_brightness_daemon.py

Control file: ~/.config/brightness-auto/enabled
    - Write "1" to enable auto-brightness, "0" to disable.
    - The daemon checks this file each cycle.
    - The GUI writes to this file to toggle auto mode.
"""

from __future__ import annotations

import logging
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

POLL_INTERVAL_S = 2.0
MIN_CHANGE_PERCENT = 2

# Smoothing: move at most this many % per tick to avoid jarring jumps.
MAX_STEP_PER_TICK = 5

_BRIGHTNESSCTL = shutil.which("brightnessctl") or "/usr/bin/brightnessctl"

# Minimum fields in brightnessctl machine-readable info output.
_MIN_BRIGHTNESSCTL_FIELDS = 4

CONFIG_DIR = Path.home() / ".config" / "brightness-auto"
ENABLED_FILE = CONFIG_DIR / "enabled"

# Lux-to-brightness mapping (must match the GUI curve).
LUX_CURVE: list[tuple[float, int]] = [
    (0.0, 10),
    (5.0, 40),
    (50.0, 75),
    (200.0, 90),
    (500.0, 95),
    (1000.0, 100),
    (5000.0, 100),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [auto-brightness] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _find_als_device() -> Path | None:
    """Find the first IIO ambient light sensor device path."""
    matches = list(Path("/sys/bus/iio/devices").glob("*/in_illuminance_raw"))
    if matches:
        return matches[0].parent
    return None


def _read_lux(als_path: Path) -> float:
    """Read current illuminance in lux from the ALS."""
    raw = float((als_path / "in_illuminance_raw").read_text().strip())
    try:
        scale = float((als_path / "in_illuminance_scale").read_text().strip())
    except (FileNotFoundError, ValueError):
        scale = 1.0
    try:
        offset = float((als_path / "in_illuminance_offset").read_text().strip())
    except (FileNotFoundError, ValueError):
        offset = 0.0
    return (raw + offset) * scale


def _lux_to_brightness(lux: float) -> int:
    """Map a lux reading to a screen brightness percentage using the curve."""
    if lux <= LUX_CURVE[0][0]:
        return LUX_CURVE[0][1]
    if lux >= LUX_CURVE[-1][0]:
        return LUX_CURVE[-1][1]

    for i in range(len(LUX_CURVE) - 1):
        lux_lo, bri_lo = LUX_CURVE[i]
        lux_hi, bri_hi = LUX_CURVE[i + 1]
        if lux_lo <= lux <= lux_hi:
            ratio = (lux - lux_lo) / (lux_hi - lux_lo)
            return int(bri_lo + ratio * (bri_hi - bri_lo))

    return LUX_CURVE[-1][1]


def _get_brightness() -> int:
    """Get current backlight brightness percentage."""
    result = subprocess.run(
        [_BRIGHTNESSCTL, "-m", "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    for line in result.stdout.strip().splitlines():
        parts = line.split(",")
        if len(parts) >= _MIN_BRIGHTNESSCTL_FIELDS and parts[1] == "backlight":
            return int(parts[3].rstrip("%"))
    return -1


def _set_brightness(percent: int) -> None:
    """Set backlight brightness percentage."""
    subprocess.run(
        [_BRIGHTNESSCTL, "-q", "set", f"{percent}%"],
        check=False,
    )


def _is_enabled() -> bool:
    """Check if auto-brightness is enabled via the control file."""
    try:
        return ENABLED_FILE.read_text().strip() == "1"
    except FileNotFoundError:
        return False


def _set_enabled(*, enabled: bool) -> None:
    """Write the enabled state to the control file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    ENABLED_FILE.write_text("1" if enabled else "0")


def _clamp(value: int, lo: int, hi: int) -> int:
    """Clamp value between lo and hi."""
    return max(lo, min(hi, value))


def main() -> None:
    """Main daemon loop."""
    als_path = _find_als_device()
    if als_path is None:
        log.error("No ambient light sensor found. Exiting.")
        sys.exit(1)

    log.info("ALS device: %s", als_path)
    log.info("Control file: %s", ENABLED_FILE)

    # Ensure the control file exists (default: enabled when started as service)
    if not ENABLED_FILE.exists():
        _set_enabled(enabled=True)
        log.info("Created control file with auto-brightness ENABLED.")

    # Handle SIGTERM gracefully for systemd
    running = True

    def _handle_signal(signum: int, _frame: object) -> None:
        nonlocal running
        log.info("Received signal %d, shutting down.", signum)
        running = False

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    log.info("Daemon started. Polling every %.1fs.", POLL_INTERVAL_S)

    while running:
        try:
            if _is_enabled():
                lux = _read_lux(als_path)
                target = _lux_to_brightness(lux)
                current = _get_brightness()

                if current >= 0 and abs(target - current) >= MIN_CHANGE_PERCENT:
                    # Smooth: step gradually toward the target
                    delta = target - current
                    step = _clamp(delta, -MAX_STEP_PER_TICK, MAX_STEP_PER_TICK)
                    new_val = _clamp(current + step, 0, 100)
                    _set_brightness(new_val)
                    log.info(
                        "lux=%.1f target=%d%% current=%d%% -> set %d%%",
                        lux,
                        target,
                        current,
                        new_val,
                    )
        except Exception:
            log.exception("Error in auto-brightness loop")

        time.sleep(POLL_INTERVAL_S)

    log.info("Daemon stopped.")


if __name__ == "__main__":
    main()
