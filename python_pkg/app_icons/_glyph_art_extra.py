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

# Headphones -- tunedeck, a music player: the listening itself. A stroked
# headband over two filled ear cups. The music note (``note-ascender``) is
# lyricanki's, and a cassette's reels need more negative space than a 560px
# box leaves at the family stroke weight, so the ear cups carry the meaning.
#
# Geometry, ink inside SAFE_BOX (x=256..768 = 512 wide, y=308..736 = 428 tall):
#   band  semicircle r=216 about (512,560), so its ink tops out at y=308 and
#         its ends land at x=296 / x=728, buried inside the cups.
#   cups  filled rounded rects x=256..368 and x=656..768, y=520..736; the
#         288px gap between them is far clear of MIN_NEGATIVE_SPACE=36.
_HEADPHONES = """\
    <path d="M 296 560 A 216 216 0 0 1 728 560"/>
    <rect x="256" y="520" width="112" height="216" rx="40" \
fill="{{ACCENT}}" stroke="none"/>
    <rect x="656" y="520" width="112" height="216" rx="40" \
fill="{{ACCENT}}" stroke="none"/>"""

# A speech bubble with two text lines -- sufler, a prompter that reads the
# partner's lines aloud: the prompt being spoken. Ported verbatim from
# ~/src/sufler/assets/icon/icon_foreground.svg (commit 5d38160), drawn before
# the glyph was registered here; only its translate(0,-4) is dropped, since the
# renderer recentres every fragment anyway.
#
# Geometry, ink inside SAFE_BOX (x=260..764 = 504 wide, y=248..784 = 536 tall):
#   bubble rounded rect x=296..728, y=284..636, corner r=64, with a tail from
#          (480,636) down to a point at (360,748) and back up at x=384.
#   lines  x=408..616 at y=398 and a shorter x=408..520 at y=522. Gaps
#          bubble->line1, line1->line2 and line2->bubble are 42 / 52 / 42px,
#          clear of MIN_NEGATIVE_SPACE=36; the fit scales this glyph up
#          (authored ink radius 326 < 340), which only widens them.
_PROMPT_BUBBLE = """\
    <path d="M 360 284 L 664 284 A 64 64 0 0 1 728 348 L 728 572 \
A 64 64 0 0 1 664 636 L 480 636 L 360 748 L 384 636 L 360 636 \
A 64 64 0 0 1 296 572 L 296 348 A 64 64 0 0 1 360 284 Z"/>
    <path d="M 408 398 L 616 398"/>
    <path d="M 408 522 L 520 522"/>"""

# A camera -- macro-cam, which estimates a meal's macros from a photo: the
# photo being taken. Stroked body with a viewfinder hump over a stroked lens.
# The food itself is already taken (``shield-cutlery``, ``bowl-star``), so the
# camera carries the meaning.
#
# Geometry, ink x=220..804 (584 wide), y=236..788 (552 tall):
#   body  rounded rect x=256..768, y=336..752, corner r=64, with a hump
#         rising to y=272 between x=416..528. The corner arcs set the ink
#         radius (~360), so the fit shrinks the glyph to ~0.94.
#   lens  circle r=88 about (512,544). Centreline gaps lens->body are 120px
#         above and below, so after the ~0.94 fit the ink gap is ~41px, and
#         the lens hole is ~94px across: both clear of MIN_NEGATIVE_SPACE=36
#         at the FINAL scale (tests/test_registry.py measures it).
_CAMERA = """\
    <path d="M 320 336 L 384 336 L 416 272 L 528 272 L 560 336 L 704 336 \
A 64 64 0 0 1 768 400 L 768 688 A 64 64 0 0 1 704 752 L 320 752 \
A 64 64 0 0 1 256 688 L 256 400 A 64 64 0 0 1 320 336 Z"/>
    <circle cx="512" cy="544" r="88"/>"""
