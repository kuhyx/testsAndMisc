"""Fourth batch of SVG path fragments, continued from :mod:`_glyph_art_extra`.

Split off purely to keep every glyph module under the 250-line cap; which file
a glyph lives in carries no meaning. :mod:`glyphs` imports from all of them.
"""

from __future__ import annotations

# A board card with a tick and a play arrow -- todo_implementer, the board that
# runs Claude sessions on todo notes: the card is a task, the play arrow starts
# its run, the tick is the task landing. ``checklist`` (todo) already owns the
# tick-rows idea, so the card outline is what tells the two apart.
#
# Geometry (authoring space; the fit shrinks it, tests measure the final gaps):
#   card   stroked rounded rect x=208..816, y=272..752, corner r=72.
#   tick   stroked (345,525)->(410,590)->(515,465), left of centre.
#   play   filled triangle x=615..712, y=430..610, no stroke.
#   Centrelines: card->tick 137px (two half strokes), tick->play 100px and
#   play->card 104px (one half stroke each), so every gap stays clear of
#   MIN_NEGATIVE_SPACE=36 after the ~0.82 fit.
_CARD_CHECK_PLAY = """\
    <path d="M 280 272 L 744 272 A 72 72 0 0 1 816 344 L 816 680 \
A 72 72 0 0 1 744 752 L 280 752 A 72 72 0 0 1 208 680 L 208 344 \
A 72 72 0 0 1 280 272 Z"/>
    <path d="M 345 525 L 410 590 L 515 465"/>
    <path fill="{{ACCENT}}" stroke="none" d="M 615 430 L 712 520 L 615 610 Z"/>"""
