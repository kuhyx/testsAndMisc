"""Glyphs of apps that shipped a family icon before they were registered here.

kartka, leetcode-guard and todoImplementer each drew their icon by hand in the
family style and committed it with no registry entry, so the generator could
not regenerate them. Each fragment below is ported verbatim from that app's
``assets/icon/icon_foreground.svg``, with only the hand-applied transform and
stroke width dropped (the renderer refits every fragment) and the literal
accent replaced by the marker, so regenerating changes nothing visible.
"""

from __future__ import annotations

# A document with a folded corner over a split lower panel -- kartka, a
# character sheet: the sheet itself. From ~/src/kartka/assets/icon.
#
# Geometry: page x=320..704, y=256..768 with the corner cut at (576,256) ->
# (704,384); the fold is a filled triangle. The lower panel starts at y=544
# and splits at x=464, so the smallest cell is 144x224 on the centreline,
# far clear of MIN_NEGATIVE_SPACE=36.
_DOCUMENT_SPLIT = """\
    <path d="M 320 256 L 576 256 L 704 384 L 704 768 L 320 768 Z"/>
    <path fill="{{ACCENT}}" d="M 576 256 L 576 384 L 704 384 Z"/>
    <path d="M 320 544 L 704 544"/>
    <path d="M 464 544 L 464 768"/>"""

# ``</>`` code brackets -- leetcode-guard, which gates on solving a LeetCode
# problem: the code being written. From ~/src/leetcode-guard/app/assets/icon.
#
# Geometry: chevrons from x=208 / x=816 to their tips at x=352 / x=672, height
# y=344..680, with the slash x=472..552 between them; 120px between a chevron
# and the slash at mid-height.
_CODE_BRACKETS = """\
    <path d="M 352 344 L 208 512 L 352 680"/>
    <path d="M 672 344 L 816 512 L 672 680"/>
    <path d="M 552 344 L 472 680"/>"""

# A screen holding a tick and a play triangle -- todoImplementer, which drives
# backlog items through to done: the item run and ticked off. From
# ~/src/todoImplementer/app/assets/icon.
#
# Geometry: rounded screen x=208..816, y=272..752, corner r=72; tick
# (345,525)->(410,590)->(515,465); filled play triangle x=615..712,
# y=430..610. The tick and the triangle sit 100px apart.
_SCREEN_TICK_PLAY = """\
    <path d="M 280 272 L 744 272 A 72 72 0 0 1 816 344 L 816 680 \
A 72 72 0 0 1 744 752 L 280 752 A 72 72 0 0 1 208 680 L 208 344 \
A 72 72 0 0 1 280 272 Z"/>
    <path d="M 345 525 L 410 590 L 515 465"/>
    <path fill="{{ACCENT}}" stroke="none" d="M 615 430 L 712 520 L 615 610 Z"/>"""
