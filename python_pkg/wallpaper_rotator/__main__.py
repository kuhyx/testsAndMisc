"""Entry point for the systemd timer: ``python3 -m python_pkg.wallpaper_rotator``."""

from __future__ import annotations

import logging

from python_pkg.wallpaper_rotator._tick import tick

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger(__name__).info("painted" if tick() else "unchanged")
