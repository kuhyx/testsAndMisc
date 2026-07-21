"""Write an app's icon assets and drive flutter_launcher_icons.

Three layers are produced per app:

``icon``
    Charcoal field plus accent glyph. Used as the legacy square launcher icon,
    as the Linux desktop icon, and as the master for previews.
``icon_foreground``
    Glyph only, transparent. The adaptive-icon foreground layer; the background
    layer is the flat charcoal declared in pubspec.yaml.
``icon_monochrome``
    Glyph only in white. Android 13+ recolours this for themed icons.

Both the SVG source and a 1024px PNG are written for each layer so a build never
needs rsvg-convert installed.
"""

from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING, Final

from python_pkg.app_icons import glyphs, render, style

# Matches a `flutter_launcher_icons:` block's `adaptive_icon_background:` line
# so it can be kept in sync with style.BACKGROUND without a full YAML
# round-trip (which would reformat the rest of the file).
_ADAPTIVE_BG_RE: Final[re.Pattern[str]] = re.compile(
    r'^(\s*adaptive_icon_background:\s*)"#[0-9A-Fa-f]{6}"(\s*)$', re.MULTILINE
)

if TYPE_CHECKING:
    from pathlib import Path

    from python_pkg.app_icons.apps import AppIcon

# (filename stem, draw the charcoal field, colour override)
_LAYERS: Final[tuple[tuple[str, bool, str | None], ...]] = (
    ("icon", True, None),
    ("icon_foreground", False, None),
    ("icon_monochrome", False, style.MONOCHROME),
)


def write_assets(app: AppIcon) -> list[Path]:
    """Write every icon layer for one app as SVG plus 1024px PNG.

    Parameters:
    app (AppIcon): App to generate assets for.

    Returns:
    list[Path]: Every file written, in creation order.
    """
    glyph = glyphs.get_glyph(app.glyph)
    offset = render.centre_offset(glyph, app.accent)
    written: list[Path] = []
    for stem, with_background, colour in _LAYERS:
        svg_text = render.build_svg(
            glyph,
            colour or app.accent,
            with_background=with_background,
            offset=offset,
        )
        svg_path = app.asset_dir / f"{stem}.svg"
        svg_path.parent.mkdir(parents=True, exist_ok=True)
        svg_path.write_text(svg_text, encoding="utf-8")
        png_path = app.asset_dir / f"{stem}.png"
        render.rasterise(svg_text, png_path, style.CANVAS)
        written.extend((svg_path, png_path))
    return written


def write_linux_icons(app: AppIcon, destination: Path) -> list[Path]:
    """Render the hicolor icon-theme PNGs for a Linux desktop target.

    Parameters:
    app (AppIcon): App to generate icons for; must have ``linux`` set.
    destination (Path): Directory to write ``<size>/<icon_name>.png`` into.

    Returns:
    list[Path]: Every PNG written.
    """
    glyph = glyphs.get_glyph(app.glyph)
    offset = render.centre_offset(glyph, app.accent)
    svg_text = render.build_svg(glyph, app.accent, with_background=True, offset=offset)
    written: list[Path] = []
    for size in style.LINUX_ICON_SIZES:
        png_path = destination / str(size) / f"{app.icon_name}.png"
        render.rasterise(svg_text, png_path, size)
        written.append(png_path)
    return written


def sync_pubspec_background(app: AppIcon) -> bool:
    """Rewrite pubspec.yaml's ``adaptive_icon_background`` to match style.BACKGROUND.

    flutter_launcher_icons reads the adaptive-icon background color from
    pubspec.yaml, not from this package -- a value that has to be kept in
    sync by hand has drifted before (six apps kept `#1B1D21` in pubspec.yaml
    after style.BACKGROUND moved to `#211D1B`, so the on-device icon stayed
    on the old color even though every generated asset was correct). This
    makes that class of drift impossible instead of relying on remembering
    to update it.

    Parameters:
    app (AppIcon): App whose pubspec.yaml should be synced.

    Returns:
    bool: True if the file was changed, False if it already matched.
    """
    pubspec_path = app.repo / "pubspec.yaml"
    original = pubspec_path.read_text(encoding="utf-8")
    updated = _ADAPTIVE_BG_RE.sub(rf'\1"{style.BACKGROUND}"\2', original, count=1)
    if updated == original:
        return False
    pubspec_path.write_text(updated, encoding="utf-8")
    return True


def run_flutter_launcher_icons(app: AppIcon) -> None:
    """Generate the Android mipmap set from the written assets.

    flutter_launcher_icons owns the error-prone part: five density buckets, the
    round variant, and the ``mipmap-anydpi-v26/ic_launcher.xml`` adaptive
    descriptor that none of these repos had before. Syncs pubspec.yaml's
    adaptive_icon_background first so the tool never reads a stale value.

    Parameters:
    app (AppIcon): App whose Flutter project should be processed.
    """
    sync_pubspec_background(app)
    subprocess.run(
        [render.resolve_tool("dart"), "run", "flutter_launcher_icons"],
        cwd=app.repo,
        check=True,
        capture_output=True,
    )
