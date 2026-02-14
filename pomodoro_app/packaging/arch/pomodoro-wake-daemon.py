#!/usr/bin/env python3
"""Pomodoro wake daemon.

Listens for UDP wake broadcasts from the Pomodoro app and automatically
launches the app on:
  - the local desktop (if not already running)
  - connected Android devices via ADB (if available)

Intended to run as a systemd user service so that opening the app on any
device opens it everywhere.
"""

from __future__ import annotations

import json
import logging
import shutil
import socket
import subprocess
import time

WAKE_PORT = 41235
APP_PROCESS = "pomodoro_app"
APP_COMMAND = "pomodoro-app"
ANDROID_PACKAGE = "com.kuhy.pomodoro_app"
ANDROID_ACTIVITY = ".MainActivity"

# Minimum seconds between consecutive launches to avoid rapid re-triggers.
LAUNCH_COOLDOWN = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [pomodoro-wake] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def is_app_running() -> bool:
    """Check whether the Pomodoro app is running locally."""
    pgrep = shutil.which("pgrep")
    if pgrep is None:
        return False
    try:
        result = subprocess.run(
            [pgrep, "-f", APP_PROCESS],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0


def launch_local() -> None:
    """Launch the Pomodoro app on the local desktop."""
    if is_app_running():
        log.info("Local app already running, skipping launch")
        return
    cmd = shutil.which(APP_COMMAND)
    if cmd is None:
        log.warning("%s not found on PATH", APP_COMMAND)
        return
    log.info("Launching local app: %s", cmd)
    subprocess.Popen(
        [cmd],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def get_adb_devices() -> list[str]:
    """Return list of connected ADB device serial numbers."""
    adb = shutil.which("adb")
    if adb is None:
        return []
    try:
        result = subprocess.run(
            [adb, "devices"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    devices: list[str] = []
    for line in result.stdout.strip().splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":  # noqa: PLR2004
            devices.append(parts[0])
    return devices


def _launch_on_device(adb: str, serial: str, component: str) -> None:
    """Launch the Pomodoro app on a single Android device."""
    log.info("Launching on Android device %s", serial)
    cmd = [adb, "-s", serial, "shell", "am", "start", "-n", component]
    try:
        subprocess.run(cmd, capture_output=True, timeout=10, check=False)
    except subprocess.TimeoutExpired:
        log.warning("Timeout launching on %s", serial)


def launch_android(devices: list[str]) -> None:
    """Launch the Pomodoro app on connected Android devices."""
    adb = shutil.which("adb")
    if adb is None:
        return
    component = f"{ANDROID_PACKAGE}/{ANDROID_ACTIVITY}"
    for serial in devices:
        _launch_on_device(adb, serial, component)


def _handle_wake(sock: socket.socket, last_launch: float) -> float:
    """Handle a single wake signal. Returns updated last_launch time."""
    try:
        data, addr = sock.recvfrom(4096)
    except OSError:
        return last_launch
    try:
        msg = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return last_launch
    if msg.get("action") != "wake":
        return last_launch
    device_id = msg.get("deviceId", "unknown")
    log.info("Received wake from %s (%s)", device_id, addr[0])
    now = time.monotonic()
    if now - last_launch < LAUNCH_COOLDOWN:
        log.info("Cooldown active, skipping launch")
        return last_launch
    launch_local()
    launch_android(get_adb_devices())
    return now


def main() -> None:
    """Run the wake daemon loop."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", WAKE_PORT))
    log.info("Listening for wake signals on UDP port %d", WAKE_PORT)
    last_launch = 0.0
    while True:
        last_launch = _handle_wake(sock, last_launch)


if __name__ == "__main__":
    main()
