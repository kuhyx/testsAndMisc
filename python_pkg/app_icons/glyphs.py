"""Per-app glyph artwork for the shared icon family.

A glyph is a raw SVG fragment drawn in the 1024x1024 master canvas. It does not
need to be perfectly positioned: :mod:`python_pkg.app_icons.render` measures the
rendered ink and recentres the fragment, so every icon in the family sits at the
same optical height.

Fragments inherit ``fill="none"``, ``stroke``, ``stroke-width`` and round caps
from the wrapping group. A fragment that needs a filled silhouette instead
overrides those locally and uses :data:`~python_pkg.app_icons.style.ACCENT_MARKER`
for its colour.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Glyph:
    """One app's artwork.

    Parameters:
    name (str): Stable identifier, used as the ``--glyph`` CLI value.
    description (str): What the glyph depicts, for ``--list`` output.
    body (str): SVG fragment drawn in the 1024x1024 master canvas.
    """

    name: str
    description: str
    body: str


# A cloud silhouette outline with a download arrow underneath: a client that
# pulls files off a remote dufs server.
_CLOUD_DOWN = """\
    <g transform="translate(296,196) scale(18)" stroke-width="4">
      <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 \
2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 \
0-2.64-2.05-4.78-4.65-4.96z"/>
    </g>
    <path d="M 512 628 L 512 744"/>
    <path d="M 444 676 L 512 744 L 580 676"/>"""

# Bar, two plates and two collars. Plate spacing is well above the minimum
# negative space so the bar does not fill in at launcher size.
_BARBELL = """\
    <path d="M 268 512 L 756 512"/>
    <path d="M 364 356 L 364 668"/>
    <path d="M 660 356 L 660 668"/>
    <path d="M 268 432 L 268 592"/>
    <path d="M 756 432 L 756 592"/>"""

# Plain clock face. Deliberately no bell "ears": at launcher size they read as
# noise rather than as an alarm clock.
_CLOCK = """\
    <circle cx="512" cy="512" r="244"/>
    <path d="M 512 512 L 512 350"/>
    <path d="M 512 512 L 636 512"/>"""

# Shield outline guarding filled cutlery. The fork is paired with a knife on
# purpose: a lone three-tine fork reads as a trident at small sizes.
_SHIELD_CUTLERY = """\
    <path d="M 512 275 L 752 366 L 752 544 C 752 655 646 723 512 753 \
C 378 723 272 655 272 544 L 272 366 Z"/>
    <g transform="translate(356,362) scale(13)" fill="{{ACCENT}}" stroke="none">
      <path d="M11 9H9V2H7v7H5V2H3v7c0 2.12 1.66 3.84 3.75 3.97V22h2.5v-9.03\
C11.34 12.84 13 11.12 13 9V2h-2v7z"/>
      <path d="M16 12h2.5v10H21V2c-2.76 0-5 2.24-5 5v5z"/>
    </g>"""

# Two ticked-off list rows. More specific to a notes/todo app than a lone
# checkmark, and still legible at 48dp.
_CHECKLIST = """\
    <path d="M 272 372 L 346 446 L 478 314"/>
    <path d="M 594 400 L 752 400"/>
    <path d="M 272 620 L 346 694 L 478 562"/>
    <path d="M 594 648 L 752 648"/>"""

# Two interlocking stadium (pill-ring) outlines, both rotated -45 deg and
# offset along the anti-diagonal so their strokes overlap in the middle --
# reads as both "habit-stacking" (linked items) and "don't break the chain".
# Ring height is tall enough that the 72px stroke leaves a genuinely hollow
# interior (height - 2*stroke-width well above MIN_NEGATIVE_SPACE); a
# shorter ring's stroke fills the interior solid and reads as a blob.
_CHAIN_LINK = """\
    <g transform="translate(467,557) rotate(-45) translate(-150,-110)">
      <rect x="0" y="0" width="300" height="220" rx="110" ry="110"/>
    </g>
    <g transform="translate(557,467) rotate(-45) translate(-150,-110)">
      <rect x="0" y="0" width="300" height="220" rx="110" ry="110"/>
    </g>"""


GLYPHS: Final[dict[str, Glyph]] = {
    glyph.name: glyph
    for glyph in (
        Glyph("cloud-down", "Cloud with a download arrow", _CLOUD_DOWN),
        Glyph("barbell", "Barbell with plates and collars", _BARBELL),
        Glyph("clock", "Clock face with hands", _CLOCK),
        Glyph("shield-cutlery", "Shield guarding a fork and knife", _SHIELD_CUTLERY),
        Glyph("checklist", "Two ticked-off list rows", _CHECKLIST),
        Glyph("chain-link", "Two interlocking chain links", _CHAIN_LINK),
    )
}


def get_glyph(name: str) -> Glyph:
    """Look up a glyph by name.

    Parameters:
    name (str): Glyph identifier, e.g. ``"barbell"``.

    Returns:
    Glyph: The matching glyph.

    Raises:
    KeyError: If no glyph with that name exists. The message lists the
        available names, since this is usually a CLI typo.
    """
    try:
        return GLYPHS[name]
    except KeyError:
        available = ", ".join(sorted(GLYPHS))
        msg = f"unknown glyph {name!r}; available: {available}"
        raise KeyError(msg) from None
