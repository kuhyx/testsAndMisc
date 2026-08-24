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

from python_pkg.app_icons._glyph_art import (
    _ANVIL,
    _BARBELL,
    _CHAIN_LINK,
    _CHECKLIST,
    _CLOCK,
    _CLOUD_DOWN,
    _DECISION_TREE,
    _QUILL_NIB,
    _RECEIPT_SPLIT,
    _SHIELD_CUTLERY,
    _STORAGE_BOX,
)
from python_pkg.app_icons._glyph_art_more import (
    _NOTE_ASCENDER,
    _PADLOCK_CLOSED,
    _TRACK_BARS,
)


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

GLYPHS: Final[dict[str, Glyph]] = {
    glyph.name: glyph
    for glyph in (
        Glyph("cloud-down", "Cloud with a download arrow", _CLOUD_DOWN),
        Glyph("barbell", "Barbell with plates and collars", _BARBELL),
        Glyph("clock", "Clock face with hands", _CLOCK),
        Glyph("shield-cutlery", "Shield guarding a fork and knife", _SHIELD_CUTLERY),
        Glyph("checklist", "Two ticked-off list rows", _CHECKLIST),
        Glyph("chain-link", "Two interlocking chain links", _CHAIN_LINK),
        Glyph("storage-box", "Isometric storage carton", _STORAGE_BOX),
        Glyph("receipt-split", "Torn receipt with a perforated split", _RECEIPT_SPLIT),
        Glyph("quill-nib", "Dip-pen nib with vent hole and slit", _QUILL_NIB),
        Glyph("anvil", "Blacksmith's anvil with horn and flared foot", _ANVIL),
        Glyph(
            "note-ascender",
            "Eighth note whose stem doubles as a letterform ascender on a baseline",
            _NOTE_ASCENDER,
        ),
        Glyph("track-bars", "Rising log bars with a plotted trend point", _TRACK_BARS),
        Glyph(
            "decision-tree",
            "Node branching into two levels of child nodes",
            _DECISION_TREE,
        ),
        Glyph(
            "padlock-closed",
            "Closed padlock with a punched-out keyhole",
            _PADLOCK_CLOSED,
        ),
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
