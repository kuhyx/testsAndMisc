#!/usr/bin/env python3
"""Generate diagrams for PYTANIE 31.

Interaktywne wspomaganie decyzji w warunkach ryzyka.

Diagrams:
  1. Payoff matrix + all criteria results comparison (bar chart)
  2. Regret matrix construction step-by-step
  3. Hurwicz alpha interpolation between maximax and maximin
  4. Decision criteria mnemonic map
  5. Expected value criterion with probability-weighted bars
  6. Decision conditions spectrum

All: A4-compatible, B&W, 300 DPI, laser-printer-friendly.
"""

from __future__ import annotations

import logging

import matplotlib as mpl

mpl.use("Agg")

from python_pkg.praca_magisterska_video.generate_images._q31_common import (
    OUTPUT_DIR,
    _logger,
)
from python_pkg.praca_magisterska_video.generate_images._q31_criteria_comparison import (
    draw_criteria_comparison,
)
from python_pkg.praca_magisterska_video.generate_images._q31_ev_spectrum import (
    draw_conditions_spectrum,
    draw_expected_value,
)
from python_pkg.praca_magisterska_video.generate_images._q31_hurwicz_mnemonic import (
    draw_criteria_mnemonic,
    draw_hurwicz_interpolation,
)
from python_pkg.praca_magisterska_video.generate_images._q31_regret_matrix import (
    draw_regret_matrix,
)

__all__ = [
    "draw_conditions_spectrum",
    "draw_criteria_comparison",
    "draw_criteria_mnemonic",
    "draw_expected_value",
    "draw_hurwicz_interpolation",
    "draw_regret_matrix",
]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _logger.info("Generating PYTANIE 31 diagrams...")
    draw_criteria_comparison()
    draw_regret_matrix()
    draw_hurwicz_interpolation()
    draw_criteria_mnemonic()
    draw_expected_value()
    draw_conditions_spectrum()
    _logger.info("Done! All Q31 diagrams saved to: %s", OUTPUT_DIR)
