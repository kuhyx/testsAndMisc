"""More SVG path fragments, continued from :mod:`_glyph_art`.

Split off purely to keep both modules under the 250-line cap; the division
between the two files carries no meaning beyond that. :mod:`glyphs` imports
from both, so no caller or test needs to know which file a glyph lives in.
"""

from __future__ import annotations

# Three rising bars with a plotted point above the tallest -- a day-by-day log
# that adds up to a trend, which is what a life tracker is. The bars are
# strokes rather than filled rects so the glyph keeps one stroke weight
# throughout; at a 168px pitch the 72px strokes leave 96px gaps, well above
# MIN_NEGATIVE_SPACE. The marker sits on its own row clear of the bar caps,
# and is hollow so it reads as a data point rather than a full stop.
_TRACK_BARS = """\
    <path d="M 320 700 L 320 556"/>
    <path d="M 488 700 L 488 460"/>
    <path d="M 656 700 L 656 364"/>
    <circle cx="656" cy="252" r="40" fill="none"/>"""

# A note whose stem drops past the head onto a flat baseline foot, so one
# vertical stroke reads as both a music stem and a letterform ascender sitting
# on a text line -- lyricanki turns songs into words. Filled, not stroked, for
# the nib/anvil reason: at 72px weight an outlined note-head's interior is
# under MIN_NEGATIVE_SPACE and fills in solid at 48dp.
#
# Geometry, all inside SAFE_BOX (x=232..792, y=232..792):
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


# A closed padlock: shackle down, body filled, keyhole punched out of it in the
# field colour. For the Device Owner enforcer -- the app that locks the device
# down -- where the literal reading is the right one.
#
# Geometry, computed rather than eyeballed (see the _NOTE_ASCENDER note above
# for why that distinction earned its own comment):
#   body     x=292..732, y=520..792   (440x272, rounded r=40)
#   shackle  semicircular arc, centreline r=132 about (512,520), stroke 72,
#            so its outer top is 520-132-36 = 352, inside the 232 safe edge,
#            and its legs land at x=380 and x=644, well inside the body.
#   keyhole  circle r=40 at (512,620) + tapered stem down to y=716.
#            60px of body above the circle and 76px below the stem, both
#            clear of MIN_NEGATIVE_SPACE=36, so it stays a hole at 48dp
#            instead of merging into the body edge.
#
# The shackle is stroked (inheriting the group's round caps) while the body is
# filled: a fully stroked padlock loses its keyhole at launcher size, and a
# fully filled one loses the shackle's opening.
_PADLOCK_CLOSED = """\
    <path d="M 380 520 L 380 448 A 132 132 0 0 1 644 448 L 644 520"/>
    <path fill="{{ACCENT}}" fill-rule="evenodd" stroke="none" d="\
M 332 520 L 692 520 A 40 40 0 0 1 732 560 L 732 752 A 40 40 0 0 1 692 792 \
L 332 792 A 40 40 0 0 1 292 752 L 292 560 A 40 40 0 0 1 332 520 Z \
M 512 580 A 40 40 0 0 0 492 655 L 480 716 L 544 716 L 532 655 \
A 40 40 0 0 0 512 580 Z"/>"""


# Punch card: a time card with a clipped top-left corner and a row of punched
# holes down one side, the way a real card is read by a column of sensors.
#
# An earlier version put two holes above two wide slots, which read as a face
# (eyes over teeth) at every size. Four holes in a vertical column with three
# short ruled lines beside them reads as a card instead.
#
# Geometry, all inside SAFE_BOX (232..792) and clear of MIN_NEGATIVE_SPACE=36:
#   card    x=292..732, y=232..792, top-left corner clipped 104px.
#   holes   r=34 at x=392, y=376/476/576/676. Centres 100 apart, so 32 of gap
#           between edges... too tight, hence r=30 and 100 spacing -> 40 gap.
#   lines   three 46-tall bars from x=488 to x=652, aligned to the hole rows.
_PUNCH_CARD = """\
    <path fill="{{ACCENT}}" fill-rule="evenodd" stroke="none" d="\
M 396 232 L 732 232 L 732 792 L 292 792 L 292 336 Z \
M 392 346 A 30 30 0 0 0 392 406 A 30 30 0 0 0 392 346 Z \
M 392 446 A 30 30 0 0 0 392 506 A 30 30 0 0 0 392 446 Z \
M 392 546 A 30 30 0 0 0 392 606 A 30 30 0 0 0 392 546 Z \
M 392 646 A 30 30 0 0 0 392 706 A 30 30 0 0 0 392 646 Z \
M 500 356 L 652 356 L 652 396 L 500 396 Z \
M 500 496 L 652 496 L 652 536 L 500 536 Z \
M 500 636 L 652 636 L 652 676 L 500 676 Z"/>"""

# A filled five-pointed star sitting above an open bowl: a dish, and a verdict
# on it. Distinct from _SHIELD_CUTLERY (diet-guard) by silhouette rather than
# colour -- the accent is shared family-wide and must not carry meaning.
#
# The star is FILLED, not stroked, for the nib/anvil reason: at 72px weight an
# outlined star's five interior notches close up well above
# MIN_NEGATIVE_SPACE and render as a pentagon blob at 48dp.
#
# Geometry, all inside SAFE_BOX (x=232..792, y=232..792):
#   star  R=140 r=56 about (512,380): spans y=240..493, x=379..645
#   rim   y=566, x=268..756 -- stroke top 530, so 37px clear of the star's
#         lowest point at 493, just above MIN_NEGATIVE_SPACE=36
#   bowl  walls at x=348 and x=676 dropping to y=752: stroke bottom 788,
#         4px inside the safe box
#
# The bowl is deep and narrow relative to its rim on purpose. A first pass
# used shallow walls at x=330..694 stopping at y=736, and the result read as
# a smiling mouth with the star for a nose -- two curves and a shape above
# them is a face unless the vessel is unmistakably deeper than it is wide at
# the base. Total ink runs y=240..788 = 548, under the 560 safe box.
#
# The star's lowest points are the two lower
# outer tips at y=493 -- NOT the inner vertex at y=436, which is what a first
# pass measured before checking; the rim was placed off that and overlapped
# the tips. Compute every extreme, do not eyeball one.
_BOWL_STAR = """\
    <path d="M 512 240 L 545 335 L 645 337 L 565 397 L 594 493 L 512 436 \
L 430 493 L 459 397 L 379 337 L 479 335 Z" fill="{{ACCENT}}" stroke="none"/>
    <path d="M 268 566 L 756 566"/>
    <path d="M 348 566 C 348 700 420 752 512 752 C 604 752 676 700 676 566"/>"""


# A handset under a broadcast arc: the bot's control panel, reached from
# somewhere else. The arc is what makes it "remote" rather than "settings",
# and it is detached from the body on purpose -- an arc that *meets* the body
# is a padlock shackle, and padlock-closed is already in this family.
#
# Filled body with punched-out buttons, not a stroked outline, for the reason
# the nib and the anvil are filled: a 200-wide stroked body leaves a 56px
# interior at STROKE_WIDTH=72, which fills in solid at 48dp.
#
# Geometry, all inside SAFE_BOX (232..792) and clear of MIN_NEGATIVE_SPACE=36:
#   body    x=412..612, y=440..792, corner radius 56
#   buttons r=40 at (512,540) and (512,680). Edge gap between them 60; to the
#           body's top edge 60, to its bottom edge 72, to each side wall 60
#   arc     r=132 about the body's top centre (512,440), drawn between its
#           135 and 45 degree points (419,347)-(605,347)
#
# The arc's *lowest* ink is its endpoints at y=347 plus half the stroke = 383,
# which is 57 clear of the body at 440 -- not the arc's centre, which is
# inside the body. Total ink y=272..792 and x=383..641, both within the box.
_REMOTE_WAVE = """\
    <path d="M 419 347 A 132 132 0 0 1 605 347"/>
    <path fill="{{ACCENT}}" fill-rule="evenodd" stroke="none" d="\
M 468 440 L 556 440 A 56 56 0 0 1 612 496 L 612 736 A 56 56 0 0 1 556 792 \
L 468 792 A 56 56 0 0 1 412 736 L 412 496 A 56 56 0 0 1 468 440 Z \
M 512 500 A 40 40 0 0 0 512 580 A 40 40 0 0 0 512 500 Z \
M 512 640 A 40 40 0 0 0 512 720 A 40 40 0 0 0 512 640 Z"/>"""


# House with a tick inside: the home, cleared. A stroked house outline rather
# than a broom or sparkle -- a broom reads as a paintbrush at 48dp, and the
# family already leans on "check" for done-ness (see checklist).
#
# Geometry, all inside SAFE_BOX (232..792) and clear of MIN_NEGATIVE_SPACE=36:
#   house   apex (512,280), eaves y=480 at x=272/752, walls down to y=752.
#           Apex ink with the round join reaches ~y=244, inside the box.
#   tick    (400,560)-(480,640)-(630,500). Bottom ink 676 vs floor ink 716
#           -> 40 gap; right ink 666 vs wall ink 716 -> 50; left ink 364 vs
#           wall ink 308 -> 56; top ink 464 vs the roof line at x=630
#           (y=363, ink to 399) -> 65.
_HOUSE_TICK = """\
    <path d="M 272 752 L 272 480 L 512 280 L 752 480 L 752 752 Z"/>
    <path d="M 400 560 L 480 640 L 630 500"/>"""


# Umbrella: a filled canopy with a scalloped hem over a stroked J-handle -- the
# app answers exactly one question, "take it or not". Filled rather than
# stroked because a stroked dome with ribs reads as a jellyfish at 48dp.
#
# Geometry, inside SAFE_BOX (232..792) and clear of MIN_NEGATIVE_SPACE=36:
#   canopy  dome r=240 about (512,512): x 272..752, top y=272; hem is three
#           r=80 scallops bulging up to y=432.
#   handle  shaft x=512 from the hem (y=440) to y=700, then a hook r=56 about
#           (456,700): ink reaches y=792 and x=364; the hook's inner opening
#           is 112-72 = 40 wide.
_UMBRELLA = """\
    <path fill="{{ACCENT}}" stroke="none" d="\
M 272 512 A 240 240 0 0 1 752 512 A 80 80 0 0 0 592 512 \
A 80 80 0 0 0 432 512 A 80 80 0 0 0 272 512 Z"/>
    <path d="M 512 440 L 512 700 A 56 56 0 0 1 400 700"/>"""
