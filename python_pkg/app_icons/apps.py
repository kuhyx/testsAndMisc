"""Registry of the Flutter apps that use the shared icon family.

Adding a new app here (plus a glyph in :mod:`python_pkg.app_icons.glyphs`) is
all that is needed for it to get an on-style icon. The accent is the one
shared family accent (`#B8862E`, from the `unified-design-system` skill) —
apps are distinguished by glyph shape, not color; do not give a new app its
own accent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True)
class AppIcon:
    """One app's icon configuration.

    Parameters:
    key (str): Short identifier used on the command line.
    repo (Path): Flutter project root, i.e. the directory holding pubspec.yaml.
    accent (str): Hex accent colour. Shared across every app in the family
        (the `unified-design-system` accent) — not app-specific.
    glyph (str): Glyph name from :data:`~python_pkg.app_icons.glyphs.GLYPHS`.
    icon_name (str): Basename for Linux hicolor/desktop installation.
    linux (bool): Whether the app has a Linux desktop target.
    """

    key: str
    repo: Path
    accent: str
    glyph: str
    icon_name: str
    linux: bool

    @property
    def asset_dir(self) -> Path:
        """Return the directory holding this app's icon source assets."""
        return self.repo / "assets" / "icon"


_HOME = Path.home()

APPS: Final[dict[str, AppIcon]] = {
    app.key: app
    for app in (
        AppIcon(
            key="dufs_client",
            # The live app: ~/dufs_client is a stale, remote-less checkout that
            # was superseded when dufs-cloud absorbed it (see testsAndMisc
            # CLAUDE.md). Same package name, so it is easy to icon the wrong one.
            repo=_HOME / "dufs-cloud" / "app",
            accent="#B8862E",
            glyph="cloud-down",
            icon_name="dufs-client",
            linux=False,
        ),
        AppIcon(
            key="focus_owner",
            # Absorbed into the phone-focus-mode monorepo on 2026-08-24; the
            # standalone ~/focus-owner clone is gone, as is its GitHub repo.
            repo=_HOME / "phone-focus-mode" / "focus-owner",
            accent="#B8862E",
            glyph="padlock-closed",
            icon_name="focus-owner",
            linux=False,
        ),
        AppIcon(
            key="workout_app",
            repo=_HOME / "screen-locker" / "stronglift_replacement" / "workout_app",
            accent="#B8862E",
            glyph="barbell",
            icon_name="workout-app",
            linux=False,
        ),
        AppIcon(
            key="wake_alarm_sync",
            repo=_HOME / "wake-alarm" / "phone_app",
            accent="#B8862E",
            glyph="clock",
            icon_name="wake-alarm-sync",
            linux=False,
        ),
        AppIcon(
            key="diet_guard_app",
            repo=_HOME / "diet-guard" / "app",
            accent="#B8862E",
            glyph="shield-cutlery",
            icon_name="diet-guard-app",
            linux=True,
        ),
        AppIcon(
            key="todo",
            repo=_HOME / "todo",
            accent="#B8862E",
            glyph="checklist",
            icon_name="todo",
            linux=True,
        ),
        AppIcon(
            key="untools",
            repo=_HOME / "untools",
            accent="#B8862E",
            glyph="decision-tree",
            icon_name="untools",
            # Desktop is the web build in a Chrome --app window, so there is
            # no GTK app to hand a hicolor PNG to.
            linux=False,
        ),
        AppIcon(
            key="habit_stack",
            repo=_HOME / "habit_stack",
            accent="#B8862E",
            glyph="chain-link",
            icon_name="habit-stack",
            linux=False,
        ),
        AppIcon(
            key="home_inventory",
            repo=_HOME / "home_inventory",
            accent="#B8862E",
            glyph="storage-box",
            icon_name="home-inventory",
            linux=True,
        ),
        AppIcon(
            key="epopeja_karta",
            repo=_HOME / "epopeja_karta",
            accent="#B8862E",
            glyph="quill-nib",
            icon_name="epopeja-karta",
            # A linux/ target exists, but only so the app can be driven on the
            # desktop during development. It is a character sheet you bring to
            # the table, so it ships no desktop entry and gets no hicolor set.
            linux=False,
        ),
        AppIcon(
            key="octoforge",
            # The Flutter app is a subdirectory of the repo: the repo root
            # holds the pure-Dart core and the tooling alongside it.
            repo=_HOME / "octoforge" / "octoforge" / "app",
            accent="#B8862E",
            glyph="anvil",
            icon_name="octoforge",
            # Unlike the other phone-first apps, this one is genuinely used on
            # the desktop too, so it gets the hicolor set and a desktop entry.
            linux=True,
        ),
        AppIcon(
            key="kuhylog",
            repo=_HOME / "kuhylog" / "kuhylog",
            accent="#B8862E",
            glyph="track-bars",
            icon_name="kuhylog",
            # Android is the real target (home-screen widget, quick-settings
            # tile); the Linux build exists for trying the UI without a phone,
            # so it still wants the hicolor set.
            linux=True,
        ),
        AppIcon(
            key="lyricanki",
            repo=_HOME / "lyricanki",
            accent="#B8862E",
            glyph="note-ascender",
            icon_name="lyricanki",
            # Mobile-primary by decision Q6: the pack builder is a Python tool
            # run on the desktop, but the Flutter app itself has no Linux target.
            linux=False,
        ),
    )
}


def get_app(key: str) -> AppIcon:
    """Look up an app by key.

    Parameters:
    key (str): App identifier, e.g. ``"todo"``.

    Returns:
    AppIcon: The matching configuration.

    Raises:
    KeyError: If no app with that key is registered.
    """
    try:
        return APPS[key]
    except KeyError:
        available = ", ".join(sorted(APPS))
        msg = f"unknown app {key!r}; available: {available}"
        raise KeyError(msg) from None
