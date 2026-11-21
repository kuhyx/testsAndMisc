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
    AppIcon(
        key="kartka",
        repo=_HOME / "src/kartka",
        accent="#B8862E",
        glyph="document-split",
        icon_name="kartka",
        # desktop/install_desktop_entry.sh installs desktop/icons/<size>/
        # kartka.png into hicolor; its header names `--linux-out desktop/icons`.
        linux=True,
    ),
    AppIcon(
        key="leetcode",
        repo=_HOME / "src/leetcode-guard/app",
        accent="#B8862E",
        glyph="code-brackets",
        icon_name="leetcode-guard-app",
        # tool/install_desktop.sh writes leetcode-guard-app.desktop. It points
        # Icon= at assets/icon/icon.png today, not at a hicolor set.
        linux=True,
    ),
    AppIcon(
        key="todoimpl",
        repo=_HOME / "src/todoImplementer/app",
        accent="#B8862E",
        glyph="screen-tick-play",
        icon_name="todoimpl",
        # Android only: no linux/ target and no desktop entry. The desktop
        # board is the separate web/ TypeScript app, not this Flutter build.
        linux=False,
    ),
    AppIcon(
        key="logo_review",
        repo=_HOME / "src/logo-review/app",
        accent="#B8862E",
        glyph="square-tick",
        icon_name="logo-review",
        # Android only: the desktop half is the server's own web page.
        linux=False,
    ),
    AppIcon(
        key="mahjong",
        repo=_HOME / "src/mahjong-teacher/app",
        accent="#B8862E",
        glyph="mahjong-tile",
        icon_name="mahjong",
        # Android only: the PC plays the same game in a normal browser.
        linux=False,
    ),
)
