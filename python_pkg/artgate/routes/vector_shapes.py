"""Route (d): the remaining seven vector subjects.

Split from ``vector.py`` to stay under the 250-line file cap. Together the two
modules cover all twelve bake-off subjects, which is what makes this cell's
number comparable to route (a)'s -- a cell measured on five easy subjects
would not be.

Each shape carries a distinguishing feature for the same reason the procedural
route does: geometric correctness alone reads as a placeholder.
"""

from __future__ import annotations

from typing import Final

from python_pkg.artgate.routes.vector import PALETTE, STROKE, register

EXTRA_SHAPES: Final[dict[str, str]] = {
    "scroll": (
        f'<rect x="12" y="14" width="40" height="36" '
        f'fill="{PALETTE["light"]}" {STROKE}/>'
        f'<rect x="8" y="10" width="48" height="8" rx="4" '
        f'fill="{PALETTE["mid"]}" {STROKE}/>'
        f'<rect x="8" y="46" width="48" height="8" rx="4" '
        f'fill="{PALETTE["mid"]}" {STROKE}/>'
        f'<g stroke="{PALETTE["shadow"]}" stroke-width="2">'
        f'<line x1="19" y1="26" x2="45" y2="26"/>'
        f'<line x1="19" y1="32" x2="45" y2="32"/>'
        f'<line x1="19" y1="38" x2="38" y2="38"/></g>'
    ),
    "book": (
        f'<rect x="12" y="8" width="40" height="48" rx="2" '
        f'fill="{PALETTE["red"]}" {STROKE}/>'
        f'<rect x="12" y="8" width="9" height="48" '
        f'fill="{PALETTE["shadow"]}"/>'
        f'<rect x="26" y="16" width="20" height="3" '
        f'fill="{PALETTE["light"]}"/>'
        f'<rect x="46" y="26" width="8" height="12" rx="2" '
        f'fill="{PALETTE["gold"]}" {STROKE}/>'
    ),
    "bone": (
        f'<rect x="24" y="16" width="16" height="32" '
        f'fill="{PALETTE["light"]}" {STROKE}/>'
        f'<circle cx="22" cy="16" r="9" fill="{PALETTE["light"]}" {STROKE}/>'
        f'<circle cx="42" cy="16" r="9" fill="{PALETTE["light"]}" {STROKE}/>'
        f'<circle cx="22" cy="48" r="9" fill="{PALETTE["light"]}" {STROKE}/>'
        f'<circle cx="42" cy="48" r="9" fill="{PALETTE["light"]}" {STROKE}/>'
    ),
    "bomb": (
        f'<circle cx="30" cy="40" r="19" fill="{PALETTE["shadow"]}" '
        f"{STROKE}/>"
        f'<circle cx="23" cy="33" r="5" fill="{PALETTE["mid"]}"/>'
        f'<rect x="34" y="14" width="7" height="10" '
        f'fill="{PALETTE["mid"]}" {STROKE}/>'
        f'<path d="M38 14 Q46 8 50 12" fill="none" '
        f'stroke="{PALETTE["mid"]}" stroke-width="3"/>'
        f'<circle cx="52" cy="10" r="4" fill="{PALETTE["gold"]}"/>'
        f'<circle cx="53" cy="8" r="2" fill="{PALETTE["red"]}"/>'
    ),
    "sword": (
        f'<polygon points="32,4 38,18 38,44 26,44 26,18" '
        f'fill="{PALETTE["light"]}" {STROKE}/>'
        f'<line x1="32" y1="12" x2="32" y2="42" '
        f'stroke="{PALETTE["mid"]}" stroke-width="3"/>'
        f'<rect x="16" y="44" width="32" height="6" rx="2" '
        f'fill="{PALETTE["gold"]}" {STROKE}/>'
        f'<rect x="28" y="48" width="8" height="8" '
        f'fill="{PALETTE["shadow"]}" {STROKE}/>'
        f'<circle cx="32" cy="56" r="4" fill="{PALETTE["gold"]}" {STROKE}/>'
    ),
    "ring": (
        f'<circle cx="32" cy="40" r="17" fill="none" '
        f'stroke="{PALETTE["gold"]}" stroke-width="7"/>'
        f'<circle cx="32" cy="40" r="17" fill="none" '
        f'stroke="{PALETTE["outline"]}" stroke-width="1"/>'
        f'<rect x="25" y="10" width="14" height="8" '
        f'fill="{PALETTE["gold"]}" {STROKE}/>'
        f'<polygon points="32,2 41,11 32,20 23,11" '
        f'fill="{PALETTE["cyan"]}" {STROKE}/>'
    ),
    "meat": (
        f'<path d="M18 34 Q18 16 34 16 Q52 16 52 36 Q52 56 34 56 '
        f'Q18 56 18 34 Z" fill="{PALETTE["red"]}" {STROKE}/>'
        f'<path d="M24 32 Q24 22 33 22" fill="none" '
        f'stroke="{PALETTE["gold"]}" stroke-width="4"/>'
        f'<rect x="28" y="8" width="8" height="12" '
        f'fill="{PALETTE["light"]}" {STROKE}/>'
        f'<circle cx="28" cy="9" r="5" fill="{PALETTE["light"]}" {STROKE}/>'
        f'<circle cx="37" cy="9" r="5" fill="{PALETTE["light"]}" {STROKE}/>'
    ),
}

# Registering at import time keeps the dependency one-directional: vector.py
# never imports this module, so there is no cycle and no lazy import.
register(EXTRA_SHAPES)
