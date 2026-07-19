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
# the adaptive foreground and background layers stay seamless.
BACKGROUND: Final[str] = "#1B1D21"

# Android masks an adaptive icon down to roughly the inner 66% of the canvas.
# Keeping every glyph inside this box means no launcher mask (circle, squircle,
# teardrop, ...) can clip it.
SAFE_BOX: Final[int] = 560

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
