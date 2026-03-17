#!/usr/bin/env python3
"""Generate diagrams for PYTANIE 1: Automata and language classes.

  1. FA recognition example — DFA for strings ending in "ab"
  2. PDA recognition example — PDA for aⁿbⁿ
  3. LBA recognition example — LBA for aⁿbⁿcⁿ
  4. TM recognition example — TM for 0ⁿ1ⁿ.

All: A4-compatible, B&W, 300 DPI, laser-printer-friendly.
"""

from __future__ import annotations

import logging

from python_pkg.praca_magisterska_video.generate_images._automata_common import (
    OUTPUT_DIR,
)
from python_pkg.praca_magisterska_video.generate_images._automata_fa import (
    draw_fa_recognition,
)
from python_pkg.praca_magisterska_video.generate_images._automata_lba import (
    draw_lba_recognition,
)
from python_pkg.praca_magisterska_video.generate_images._automata_pda import (
    draw_pda_recognition,
)
from python_pkg.praca_magisterska_video.generate_images._automata_tm import (
    draw_tm_recognition,
)

logger = logging.getLogger(__name__)

__all__ = [
    "draw_fa_recognition",
    "draw_lba_recognition",
    "draw_pda_recognition",
    "draw_tm_recognition",
]

# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    logger.info("Generating automata diagrams for PYTANIE 1...")
    draw_fa_recognition()
    draw_pda_recognition()
    draw_lba_recognition()
    draw_tm_recognition()
    logger.info("All diagrams saved to %s/", OUTPUT_DIR)
