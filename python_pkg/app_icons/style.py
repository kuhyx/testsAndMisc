"""The numbers that define the shared icon family.

Changing anything here changes *every* app's icon, which is the point: the
family is defined once and each app only contributes an accent colour and a
glyph. Regenerate all apps after editing this module.
"""

from __future__ import annotations

from typing import Final

# Master canvas. 1024 is what flutter_launcher_icons wants as a source image.
CANVAS: Final[int] = 1024
CENTRE: Final[float] = CANVAS / 2

# Charcoal field shared by all icons. Also used as adaptive_icon_background so
# the adaptive foreground and background layers stay seamless. Warm-tinted
# (unified-design-system `ink`) — a byte-reversed mirror of the previous
# cool-tinted #1B1D21, so relative lightness is unchanged.
BACKGROUND: Final[str] = "#211D1B"

# Authoring box for glyph fragments. The renderer rescales every glyph to
# INK_RADIUS anyway, so this only keeps hand-written coordinates comparable.
SAFE_BOX: Final[int] = 560

# Every glyph is scaled so its furthest inked pixel sits exactly this far from
# the centre, so all icons occupy the same circle (kuhy, 2026-10-23: glyphs had
# drifted from 250 to 394px, and focus_owner filled the whole mask). 340px is
# 24.4dp on the adaptive canvas (flutter_launcher_icons' default 16% inset maps
# 1024px onto 73.44dp), well inside Android's 33dp guaranteed-visible circle
# and the 40% (410px) maskable-web safe zone.
INK_RADIUS: Final[int] = 340

# The same circle in dp, for routes that emit Android vectors instead of PNGs
# (phone-focus-mode's focus_owner): flutter_launcher_icons insets the adaptive
# foreground 16% per side, so the 1024px canvas covers 108 * 0.68 = 73.44dp.
ADAPTIVE_CANVAS_DP: Final[float] = 108 * (1 - 2 * 0.16)
INK_RADIUS_DP: Final[float] = INK_RADIUS / CANVAS * ADAPTIVE_CANVAS_DP

# Single stroke weight for the whole family. Glyph negative space must stay at
# or above STROKE_WIDTH / 2, otherwise adjacent strokes merge into a blob when
# the icon is scaled down to launcher size.
STROKE_WIDTH: Final[int] = 72
MIN_NEGATIVE_SPACE: Final[float] = STROKE_WIDTH / 2

# Colour used for the Android 13 themed ("monochrome") layer, which the system
# recolours itself, so the glyph must be drawn in flat white.
MONOCHROME: Final[str] = "#FFFFFF"

# Placeholder replaced with an app's accent colour inside a glyph fragment.
ACCENT_MARKER: Final[str] = "{{ACCENT}}"

# Sizes installed into the hicolor icon theme for Linux desktop targets.
LINUX_ICON_SIZES: Final[tuple[int, ...]] = (16, 24, 32, 48, 64, 128, 256, 512)
