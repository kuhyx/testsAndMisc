"""Build a contact sheet of the whole icon family for eyeballing.

Three rows are produced: full size, circle-masked (what a round launcher mask
does to the art), and a 48dp downscale (legibility at real home-screen size).
Reviewing all three together is the cheapest way to catch a glyph that only
works at poster size.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile

from python_pkg.app_icons import apps, glyphs, render, style

# Size each icon is drawn at in the contact sheet.
_TILE = 512
# Roughly a 48dp launcher icon on a high-density screen, then blown back up
# with nearest-neighbour so the pixel grid stays visible.
_SMALL = 96
_SMALL_ZOOM = 200


def _row(tiles: list[Path], destination: Path) -> None:
    """Montage a list of PNGs into a single horizontal strip.

    Parameters:
    tiles (list[Path]): Images to place, left to right.
    destination (Path): PNG path to write.
    """
    subprocess.run(
        [
            render.resolve_tool("magick"),
            "montage",
            *[str(tile) for tile in tiles],
            "-tile",
            f"{len(tiles)}x1",
            "-geometry",
            "+14+14",
            "-background",
            "#3a3a3a",
            str(destination),
        ],
        check=True,
        capture_output=True,
    )


def _circle_mask(source: Path, destination: Path) -> None:
    """Apply a round launcher mask to an icon.

    Parameters:
    source (Path): Full-size icon PNG.
    destination (Path): PNG path to write.
    """
    radius = _TILE // 2
    subprocess.run(
        [
            render.resolve_tool("magick"),
            str(source),
            "(",
            "-size",
            f"{_TILE}x{_TILE}",
            "xc:none",
            "-fill",
            "white",
            "-draw",
            f"circle {radius},{radius} {radius},0",
            ")",
            "-alpha",
            "set",
            "-compose",
            "DstIn",
            "-composite",
            str(destination),
        ],
        check=True,
        capture_output=True,
    )


def _downscale(source: Path, destination: Path) -> None:
    """Shrink an icon to launcher size and blow it back up for inspection.

    Parameters:
    source (Path): Full-size icon PNG.
    destination (Path): PNG path to write.
    """
    subprocess.run(
        [
            render.resolve_tool("magick"),
            str(source),
            "-resize",
            f"{_SMALL}x{_SMALL}",
            "-filter",
            "point",
            "-resize",
            f"{_SMALL_ZOOM}x{_SMALL_ZOOM}",
            str(destination),
        ],
        check=True,
        capture_output=True,
    )


def build_contact_sheet(keys: list[str], destination: Path) -> Path:
    """Render a three-row contact sheet for the given apps.

    Parameters:
    keys (list[str]): App keys to include, in display order.
    destination (Path): PNG path to write the sheet to.

    Returns:
    Path: The written sheet, for convenience.
    """
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        full: list[Path] = []
        masked: list[Path] = []
        small: list[Path] = []
        for key in keys:
            app = apps.get_app(key)
            glyph = glyphs.get_glyph(app.glyph)
            offset = render.centre_offset(glyph, app.accent)
            svg_text = render.build_svg(
                glyph, app.accent, with_background=True, offset=offset
            )
            tile = work / f"{key}.png"
            render.rasterise(svg_text, tile, _TILE)
            full.append(tile)
            masked_tile = work / f"{key}_masked.png"
            _circle_mask(tile, masked_tile)
            masked.append(masked_tile)
            small_tile = work / f"{key}_small.png"
            _downscale(tile, small_tile)
            small.append(small_tile)

        rows = [work / "row_full.png", work / "row_masked.png", work / "row_small.png"]
        for tiles, row_path in zip((full, masked, small), rows, strict=True):
            _row(tiles, row_path)

        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                render.resolve_tool("magick"),
                *[str(row) for row in rows],
                "-background",
                style.BACKGROUND,
                "-gravity",
                "center",
                "-append",
                str(destination),
            ],
            check=True,
            capture_output=True,
        )
    return destination
