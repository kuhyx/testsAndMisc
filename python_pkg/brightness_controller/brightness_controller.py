#!/usr/bin/env python3
"""Lightweight GUI brightness/backlight controller using brightnessctl.

Supports automatic brightness adjustment via ambient light sensor (IIO).
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from typing import NamedTuple

WINDOW_WIDTH = 420
WINDOW_HEIGHT = 340
SLIDER_LENGTH = 300
POLL_INTERVAL_MS = 2000
AUTO_POLL_MS = 1000
STEP_PERCENT = 5

ICON_SUN = "\u2600"
ICON_DIM = "\u25d1"
ICON_AUTO = "\u26a1"

CONFIG_DIR = Path.home() / ".config" / "brightness-auto"
ENABLED_FILE = CONFIG_DIR / "enabled"

_BRIGHTNESSCTL = shutil.which("brightnessctl") or "/usr/bin/brightnessctl"

# Minimum field counts in brightnessctl machine-readable output.
_MIN_DEVICE_LIST_FIELDS = 5
_MIN_INFO_FIELDS = 4

# Lux-to-brightness mapping curve (lux_threshold, brightness_percent).
# Interpolated linearly between points.
# Covers: pitch dark → dim indoor → office → bright indoor → daylight.
LUX_CURVE: list[tuple[float, int]] = [
    (0.0, 10),
    (5.0, 40),
    (50.0, 75),
    (200.0, 90),
    (500.0, 95),
    (1000.0, 100),
    (5000.0, 100),
]


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


class Device(NamedTuple):
    """Represents a backlight/LED brightness device."""

    name: str
    device_class: str
    current: int
    percent: str
    max_brightness: int


def _run_brightnessctl(*args: str) -> str:
    """Run brightnessctl with given arguments and return stdout."""
    result = subprocess.run(
        [_BRIGHTNESSCTL, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def _get_devices() -> list[Device]:
    """List available brightness devices using machine-readable output.

    Only returns backlight devices (filters out keyboard LEDs, LAN LEDs, etc.).
    """
    output = _run_brightnessctl("-l", "-m")
    devices: list[Device] = []
    for line in output.splitlines():
        parts = line.split(",")
        if len(parts) >= _MIN_DEVICE_LIST_FIELDS and parts[1] == "backlight":
            devices.append(
                Device(
                    name=parts[0],
                    device_class=parts[1],
                    current=int(parts[3].rstrip("%")),
                    percent=parts[3],
                    max_brightness=int(parts[4]),
                )
            )
    return devices


def _get_brightness(device: str) -> int:
    """Get current brightness percentage for a device."""
    output = _run_brightnessctl("-d", device, "-m", "get")
    if not output:
        return -1
    # Machine-readable "get" returns just the raw value; use "info" instead
    info = _run_brightnessctl("-d", device, "-m", "info")
    for line in info.splitlines():
        parts = line.split(",")
        if len(parts) >= _MIN_INFO_FIELDS:
            return int(parts[3].rstrip("%"))
    return -1


def _set_brightness(device: str, percent: int) -> None:
    """Set brightness to a percentage for a device."""
    _run_brightnessctl("-d", device, "set", f"{percent}%")


class BrightnessController:
    """Main GUI application for controlling brightness."""

    def __init__(self) -> None:
        """Initialize the brightness controller GUI."""
        self.root = tk.Tk()
        self.root.title(f"{ICON_SUN} Brightness Controller")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(width=False, height=False)
        self.root.configure(bg="#2b2b2b")

        self._updating_slider = False
        self.devices = _get_devices()
        self.current_device: str = ""

        # Ambient light sensor
        self.als_path = _find_als_device()
        self.auto_mode = self._read_daemon_state()

        self._build_ui()
        self._select_default_device()
        self._sync_auto_ui()
        self._poll_brightness()
        if self.als_path:
            self._poll_als()

    def _build_ui(self) -> None:
        """Build the entire UI layout."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#2b2b2b")
        style.configure(
            "TLabel",
            background="#2b2b2b",
            foreground="#e0e0e0",
            font=("sans-serif", 11),
        )
        style.configure(
            "Title.TLabel",
            background="#2b2b2b",
            foreground="#f0c040",
            font=("sans-serif", 14, "bold"),
        )
        style.configure(
            "Pct.TLabel",
            background="#2b2b2b",
            foreground="#ffffff",
            font=("sans-serif", 28, "bold"),
        )
        style.configure("TButton", font=("sans-serif", 12), padding=6)
        style.configure("Horizontal.TScale", background="#2b2b2b")

        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        # Title row
        title_frame = ttk.Frame(main)
        title_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(
            title_frame, text=f"{ICON_SUN} Brightness Controller", style="Title.TLabel"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Device selector (only shown if multiple backlight devices exist)
        device_names = [d.name for d in self.devices]
        self.device_var = tk.StringVar()

        if len(device_names) > 1:
            device_frame = ttk.Frame(main)
            device_frame.pack(fill=tk.X, pady=(0, 8))
            ttk.Label(device_frame, text="Device:").pack(side=tk.LEFT, padx=(0, 8))
            self.device_combo = ttk.Combobox(
                device_frame,
                textvariable=self.device_var,
                values=device_names,
                state="readonly",
                width=30,
            )
            self.device_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.device_combo.bind("<<ComboboxSelected>>", self._on_device_change)

        # Percentage display
        self.pct_var = tk.StringVar(value="—%")
        ttk.Label(main, textvariable=self.pct_var, style="Pct.TLabel").pack(pady=(4, 2))

        # Slider row
        slider_frame = ttk.Frame(main)
        slider_frame.pack(fill=tk.X, pady=4)

        ttk.Label(slider_frame, text=ICON_DIM, font=("sans-serif", 16)).pack(
            side=tk.LEFT, padx=(0, 6)
        )

        self.slider_var = tk.IntVar(value=50)
        self.slider = ttk.Scale(
            slider_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.slider_var,
            length=SLIDER_LENGTH,
            command=self._on_slider_move,
        )
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        ttk.Label(slider_frame, text=ICON_SUN, font=("sans-serif", 16)).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        # Buttons row
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(btn_frame, text=f"- {STEP_PERCENT}%", command=self._decrease).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(btn_frame, text="25%", command=lambda: self._set_pct(25)).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_frame, text="50%", command=lambda: self._set_pct(50)).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_frame, text="75%", command=lambda: self._set_pct(75)).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_frame, text="100%", command=lambda: self._set_pct(100)).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_frame, text=f"+ {STEP_PERCENT}%", command=self._increase).pack(
            side=tk.LEFT, padx=(4, 0)
        )

        # Auto-brightness row (only shown if ALS is available)
        if self.als_path:
            auto_frame = ttk.Frame(main)
            auto_frame.pack(fill=tk.X, pady=(10, 0))

            self.auto_btn_var = tk.StringVar(value=f"{ICON_AUTO} Auto: OFF")
            self.auto_btn = ttk.Button(
                auto_frame, textvariable=self.auto_btn_var, command=self._toggle_auto
            )
            self.auto_btn.pack(side=tk.LEFT, padx=(0, 10))

            self.lux_var = tk.StringVar(value="")
            ttk.Label(auto_frame, textvariable=self.lux_var).pack(side=tk.LEFT)

    def _select_default_device(self) -> None:
        """Auto-select the first backlight device, or first device overall."""
        if not self.devices:
            self.pct_var.set("No devices")
            return

        # Prefer backlight devices
        default = self.devices[0]
        for dev in self.devices:
            if dev.device_class == "backlight":
                default = dev
                break

        self.device_var.set(default.name)
        self.current_device = default.name
        self._refresh_brightness()

    def _on_device_change(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        """Handle device selection change."""
        self.current_device = self.device_var.get()
        self._refresh_brightness()

    def _refresh_brightness(self) -> None:
        """Read current brightness and update UI."""
        if not self.current_device:
            return
        pct = _get_brightness(self.current_device)
        if pct < 0:
            self.pct_var.set("Error")
            return
        self._updating_slider = True
        self.slider_var.set(pct)
        self._updating_slider = False
        self.pct_var.set(f"{pct}%")

    def _on_slider_move(self, value: str) -> None:
        """Handle slider drag — set brightness in real time."""
        if self._updating_slider or not self.current_device:
            return
        # Manual slider movement disables auto mode
        if self.auto_mode:
            self._set_auto(enabled=False)
        pct = int(float(value))
        self.pct_var.set(f"{pct}%")
        _set_brightness(self.current_device, pct)

    def _set_pct(self, percent: int) -> None:
        """Set brightness to an exact percentage."""
        if not self.current_device:
            return
        _set_brightness(self.current_device, percent)
        self._refresh_brightness()

    def _decrease(self) -> None:
        """Decrease brightness by the step amount."""
        if not self.current_device:
            return
        current = _get_brightness(self.current_device)
        new_val = max(0, current - STEP_PERCENT)
        _set_brightness(self.current_device, new_val)
        self._refresh_brightness()

    def _increase(self) -> None:
        """Increase brightness by the step amount."""
        if not self.current_device:
            return
        current = _get_brightness(self.current_device)
        new_val = min(100, current + STEP_PERCENT)
        _set_brightness(self.current_device, new_val)
        self._refresh_brightness()

    def _toggle_auto(self) -> None:
        """Toggle automatic brightness mode via the daemon control file."""
        self._set_auto(enabled=not self.auto_mode)

    @staticmethod
    def _read_daemon_state() -> bool:
        """Read the daemon's enabled state from the control file."""
        try:
            return ENABLED_FILE.read_text().strip() == "1"
        except FileNotFoundError:
            return False

    def _set_auto(self, *, enabled: bool) -> None:
        """Enable or disable automatic brightness mode via the daemon."""
        self.auto_mode = enabled
        # Write to the shared control file so the daemon picks it up
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        ENABLED_FILE.write_text("1" if enabled else "0")
        self._sync_auto_ui()

    def _sync_auto_ui(self) -> None:
        """Update the auto button and slider state to match current mode."""
        if not self.als_path:
            return
        if self.auto_mode:
            self.auto_btn_var.set(f"{ICON_AUTO} Auto: ON")
            self.slider.state(["disabled"])
        else:
            self.auto_btn_var.set(f"{ICON_AUTO} Auto: OFF")
            self.slider.state(["!disabled"])

    def _poll_als(self) -> None:
        """Read the ambient light sensor and display lux. Sync UI with daemon state."""
        if self.als_path:
            try:
                lux = _read_lux(self.als_path)
                self.lux_var.set(f"{ICON_SUN} {lux:.1f} lux")
            except (OSError, ValueError):
                self.lux_var.set("sensor error")
            # Sync auto mode from daemon control file (in case changed externally)
            daemon_state = self._read_daemon_state()
            if daemon_state != self.auto_mode:
                self.auto_mode = daemon_state
                self._sync_auto_ui()
        self.root.after(AUTO_POLL_MS, self._poll_als)

    def _poll_brightness(self) -> None:
        """Periodically sync brightness from the system (for external changes)."""
        if not self.auto_mode:
            self._refresh_brightness()
        self.root.after(POLL_INTERVAL_MS, self._poll_brightness)

    def run(self) -> None:
        """Start the main event loop."""
        self.root.mainloop()


def main() -> None:
    """Entry point."""
    # Quick check for brightnessctl
    try:
        subprocess.run(
            [_BRIGHTNESSCTL, "--version"],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        sys.stderr.write(
            "Error: brightnessctl not found."
            " Install it with: sudo pacman -S brightnessctl\n"
        )
        sys.exit(1)

    app = BrightnessController()
    app.run()


if __name__ == "__main__":
    main()
