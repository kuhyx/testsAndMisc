"""Later registry entries, split out of :mod:`apps` for the 250-line cap.

Which file an entry lives in carries no meaning; :data:`apps.APPS` merges both.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from python_pkg.app_icons._app_icon import AppIcon

_HOME = Path.home()

MORE_APPS: Final[tuple[AppIcon, ...]] = (
    AppIcon(
        key="tutor",
        repo=_HOME / "src/tutor/app",
        accent="#B8862E",
        glyph="lightbulb",
        icon_name="tutor",
        # Desktop is the web build in a Chrome --app window, as for todo
        # and home_inventory, whose desktop entries use the hicolor set.
        linux=True,
    ),
    AppIcon(
        key="tunedeck",
        repo=_HOME / "src/tunedeck",
        accent="#B8862E",
        glyph="headphones",
        icon_name="tunedeck",
        # Desktop is a web build behind a local wrapper in a Chrome --app
        # window (see the repo's SPEC.md), so it gets the hicolor set too.
        linux=True,
    ),
    AppIcon(
        key="sufler",
        repo=_HOME / "src/sufler",
        accent="#B8862E",
        glyph="prompt-bubble",
        icon_name="sufler",
        # packaging/sufler.desktop (Icon=sufler) installs the hicolor set
        # from packaging/icons via the PKGBUILD.
        linux=True,
    ),
    AppIcon(
        key="macro_cam",
        repo=_HOME / "src/macro-cam",
        accent="#B8862E",
        glyph="camera",
        icon_name="macro-cam",
        # Android only: no linux/ target and no desktop entry.
        linux=False,
    ),
)
