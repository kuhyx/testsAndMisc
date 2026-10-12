"""Third batch of SVG path fragments, continued from :mod:`_glyph_art_more`.

Split off purely to keep every glyph module under the 250-line cap; which file
a glyph lives in carries no meaning. :mod:`glyphs` imports from all three.
"""

from __future__ import annotations

# A lightbulb -- tutor, "learn any subject": the idea arriving. Filled bulb
# over two stroked screw-base bars. Filled rather than outlined because the
# filled bulb still reads as a bulb at 48dp, while the outline's 56px neck
# opening closes up to a speck there. ``open-book`` (book_guard_app) was the
# other obvious "learning" glyph and is taken.
#
# Geometry, ink inside SAFE_BOX (y=256..816 = 560 tall, x=326..698 = 372 wide):
#   bulb   circle r=150 about (512,442), tapering on cubics to a 128-wide neck
#          at y=556, closed across the neck; fill + family stroke, so the ink
#          reaches 36px past the centreline (top y=256, neck y=592).
#   base   bar x=440..584 at y=668 (ink 632..704) and a shorter tip bar
#          x=480..544 at y=780 (ink 744..816). Gaps neck->bar and bar->tip
#          are both 40px, clear of MIN_NEGATIVE_SPACE=36.
_LIGHTBULB = """\
    <path fill="{{ACCENT}}" d="M 448 556 C 448 510 362 500 362 442 \
A 150 150 0 0 1 662 442 C 662 500 576 510 576 556 Z"/>
    <path d="M 440 668 L 584 668"/>
    <path d="M 480 780 L 544 780"/>"""
