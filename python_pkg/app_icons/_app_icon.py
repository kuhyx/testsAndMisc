"""The :class:`AppIcon` record, split out of :mod:`apps` for the 250-line cap."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


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
