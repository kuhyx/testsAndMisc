"""The SVG path fragments each glyph is drawn from.

Split out of :mod:`python_pkg.app_icons.glyphs` to keep it under the 250-line
cap. Pure data: :mod:`glyphs` keeps the Glyph dataclass, the registry and the
lookup, so no caller or test needs to know these moved.
"""

from __future__ import annotations

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

# A branching decision tree: one node splitting into two. Reads as "decompose
# a problem into parts", the move every one of the 25 thinking tools makes in
# some form -- an issue tree most literally, but also a fishbone's ribs and a
# 2x2's quadrants.
#
# Nodes are hollow circles rather than filled dots: at 48dp a filled dot and
# the 72px stroke merge into a blob, while the ring keeps visible negative
# space (r=78 leaves 156-72=84px of interior).
#
# Two levels of branching were tried first (7 nodes) and rejected: the
# generator's safe-box check flagged it as overflowing by ~170px, and at icon
# size the doubled connectors closed up into a solid mass. One clean split
# survives the launcher mask and still reads as a tree rather than a Y-fork,
# because the square shoulders and vertical drops keep the hierarchy legible.
_DECISION_TREE = """\
    <circle cx="512" cy="300" r="78"/>
    <path d="M 512 378 L 512 452"/>
    <path d="M 346 452 L 678 452"/>
    <path d="M 346 452 L 346 528"/>
    <path d="M 678 452 L 678 528"/>
    <circle cx="346" cy="606" r="78"/>
    <circle cx="678" cy="606" r="78"/>"""

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


# An isometric storage carton: hexagonal silhouette plus the three edges that
# meet at the near-top corner (one down the front, two up the top face).
#
# A front-on rectangle with a lid seam was tried first and rejected — a seam
# plus a divider reads as a browser window or a table header, not a box. The
# isometric form has no such collision anywhere else in the family, and it is
# the shape people already recognise as "a package of stuff".
#
# Geometry: a regular hexagon, centre (512,512), circumradius 240, pointy top
# and bottom. Opposite faces sit 208px apart, leaving 136px of hollow once the
# 72px stroke is drawn — comfortably past MIN_NEGATIVE_SPACE, so no face fills
# in at 48dp. Rendered ink is 488x552, inside SAFE_BOX on both axes.
_STORAGE_BOX = """\
    <path d="M 512 272 L 720 392 L 720 632 L 512 752 L 304 632 L 304 392 Z"/>
    <path d="M 512 512 L 512 752"/>
    <path d="M 512 512 L 304 392"/>
    <path d="M 512 512 L 720 392"/>"""


# A till receipt with a torn bottom edge and a perforation down the middle:
# one bill, two shares.
#
# Filled rather than stroked, which is what makes the tear possible at all. A
# stroked receipt cannot have a fine ragged edge: at the family's 72px stroke,
# a zigzag needs ~200px pitch to keep adjacent up-strokes MIN_NEGATIVE_SPACE
# apart, and two teeth that coarse read as a ribbon or a pair of bookmarks,
# not as a torn receipt. A filled silhouette is not bound by that rule, so the
# teeth can be small enough to read as a real tear — the "prefer a filled
# silhouette when a stroked outline reads ambiguously" case.
#
# The split is a perforation, not a divider. A full-height divider cuts the
# silhouette into two separate shapes and the receipt read is lost (the same
# bookmarks failure); a dotted tear line says "split here" while leaving one
# intact receipt. Drawn with fill-rule="evenodd" so the dots are true holes,
# not charcoal-painted ones — icon_foreground and icon_monochrome are rendered
# on transparency, where a painted hole would show as a blob and, on the
# monochrome layer, in the wrong colour entirely.
#
# Geometry: body x 312..712, y 282..752, six teeth 46px deep off a root at
# y=706. Four holes of r=30 on the centreline at y=350/446/542/638. Every gap
# is at the family budget: 36px of accent between holes (96px pitch, 60px
# diameter), 38px above the first and below the last. Ink is 400x470, inside
# SAFE_BOX on both axes.
_RECEIPT_SPLIT = """\
    <path fill="{{ACCENT}}" fill-rule="evenodd" stroke="none" d="\
M 312 282 L 712 282 L 712 706 L 678 752 L 645 706 L 612 752 L 578 706 \
L 545 752 L 512 706 L 478 752 L 445 706 L 412 752 L 378 706 L 345 752 \
L 312 706 Z \
M 482 350 A 30 30 0 1 0 542 350 A 30 30 0 1 0 482 350 Z \
M 482 446 A 30 30 0 1 0 542 446 A 30 30 0 1 0 482 446 Z \
M 482 542 A 30 30 0 1 0 542 542 A 30 30 0 1 0 482 542 Z \
M 482 638 A 30 30 0 1 0 542 638 A 30 30 0 1 0 482 638 Z"/>"""


# A dip-pen nib: the character sheet is a thing you write on, and the game is
# set in the Romantic era, so the nib carries both the app and the period.
#
# Filled rather than stroked. A stroked almond outline plus a stroked vent hole
# leaves only ~20px of charcoal between the two strokes at the family's 72px
# weight — under MIN_NEGATIVE_SPACE, so the nib fills in solid at 48dp. Filled,
# the vent and the slit become true holes and the budget is spent on gaps
# instead of on stroke.
#
# A d20 was the obvious alternative and was rejected: this system rolls k6, and
# a 20-sided outline is a mess of short strokes at launcher size. A front-on
# die with pips collides with `storage-box` (both read as "boxy thing with
# marks"). Nothing else in the family is a tall pointed shape.
#
# The top edge is flat, not pointed. A symmetric almond — pointed at both ends
# — with a round hole in the upper half is a map pin, which is exactly what the
# first draft rendered as. The flat shoulder is where a real nib clips into the
# holder, and it is what stops the map-pin read.
#
# Geometry: shoulder (420,312)-(604,312), waist bowing out to ~x=400/624 around
# y=456, converging to the tip at (512,812) — ink 224x500, inside SAFE_BOX on
# both axes. Vent circle r=40 at (512,470) clears the outline by ~61px; the
# slit stops at y=700, leaving ~41px to the outline near the tip and 70px to
# the vent above. Every gap is over the 36px budget. fill-rule="evenodd" keeps
# both holes true holes — icon_foreground and icon_monochrome render on
# transparency, where a painted hole would show as a blob and in the wrong
# colour.
_QUILL_NIB = """\
    <path fill="{{ACCENT}}" fill-rule="evenodd" stroke="none" d="\
M 420 312 L 604 312 Q 626 470 596 570 L 512 812 L 428 570 \
Q 398 470 420 312 Z \
M 472 470 A 40 40 0 1 0 552 470 A 40 40 0 1 0 472 470 Z \
M 512 700 L 492 580 L 532 580 Z"/>"""


# A blacksmith's anvil: OctoForge is a GitHub client, and the forge is the
# name. Filled rather than stroked, for the same reason as the nib — a stroked
# anvil outline is a long thin horn plus a narrow waist, and at the family's
# 72px weight the waist closes up solid at 48dp.
#
# The obvious alternatives were rejected: an octopus (the Octocat) is both
# GitHub trade dress and a tangle of thin curves that blurs at launcher size,
# and a hammer alone collides with nothing in the family but reads as a generic
# tool rather than a forge. The anvil silhouette is unmistakable and shares no
# shape language with the other nine glyphs.
#
# Geometry: the body is a face slab (x=336..768, y=316..420), a waist
# (x=444..596, y=420..592) and a flared foot (x=304..716, y=592..708) — total
# ink 512x392 including the horn, inside SAFE_BOX once the renderer scales it.
#
# The horn is what makes this an anvil rather than an I-beam, so it is a
# separate wedge projecting left off the face, not a rounded corner on it: it
# leaves the slab at full 104px depth (x=336) and tapers to a 40px blunt tip
# at x=256, dropping the underside from y=420 to y=392 on the way. A sharp
# point would disappear at 48dp; 40px is above MIN_NEGATIVE_SPACE so it
# survives. The first two drafts folded the taper into the slab's left end and
# both read as a bump.
_ANVIL = """\
    <path fill="{{ACCENT}}" stroke="none" d="\
M 768 316 L 768 420 L 596 420 \
Q 592 512 592 592 L 716 592 L 716 708 L 304 708 L 304 592 L 428 592 \
Q 428 512 424 420 L 336 420 \
L 256 392 Q 248 376 256 360 L 336 316 Z"/>"""

# A note whose stem drops past the head onto a flat baseline foot, so one
# vertical stroke reads as both a music stem and a letterform ascender sitting
# on a text line -- lyricanki turns songs into words. Filled, not stroked, for
# the nib/anvil reason: at 72px weight an outlined note-head's interior is
# under MIN_NEGATIVE_SPACE and fills in solid at 48dp.
#
# Geometry, all inside SAFE_BOX (ink 560x504):
#   stem  x=520..592, y=272..584  (72 wide, the family stroke weight)
#   head  ellipse (501,580) rx=118 ry=90 rot -20deg: y=486..674, x=386..616,
#         overlapping the stem's end, so the stem stops at y=584
#   flags two stacked wedges off the stem top, reaching x=756 and x=736
#   foot  x=232..792, y=724..776  (52 tall, reads as the baseline)
#
# The head's lowest point is y=674: a rotated ellipse reaches
# sqrt((rx*sin t)^2 + (ry*cos t)^2) below its centre, NOT ry. That leaves 50px
# above the foot, clear of MIN_NEGATIVE_SPACE=36. A first draft used ry=104 at
# cy=672 and recorded "40px clearance" without doing that sum -- the head
# overlapped the foot by 40px and rendered as a mailbox. Recompute, never eyeball.
#
# Rejected: a bare note says nothing about words; a speech bubble around one
# has nested outlines that vanish at 48dp.
_NOTE_ASCENDER = """\
    <path fill="{{ACCENT}}" fill-rule="evenodd" stroke="none" d="\
M 520 272 L 592 272 L 592 584 L 520 584 Z \
M 592 272 Q 706 332 756 416 Q 760 316 592 220 Z \
M 592 352 Q 694 408 736 480 Q 740 392 592 302 Z \
M 232 724 L 792 724 L 792 776 L 232 776 Z"/>
    <ellipse fill="{{ACCENT}}" stroke="none" \
cx="501" cy="580" rx="118" ry="90" transform="rotate(-20 501 580)"/>"""
