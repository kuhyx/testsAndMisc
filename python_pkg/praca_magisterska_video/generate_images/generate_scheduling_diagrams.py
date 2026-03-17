#!/usr/bin/env python3
"""Generate diagrams for PYTANIE 17: Szeregowanie zadań (Scheduling).

Diagrams:
  1. Graham notation α|β|γ visual mnemonic map
  2. Johnson's algorithm Gantt chart (F2||Cmax example)
  3. SPT vs LPT comparison Gantt (1||ΣCⱼ)
  4. Flow shop vs Job shop visual comparison
  5. Scheduling complexity landscape
  6. EDD example (1 || Lmax)

All: A4-compatible, B&W, 300 DPI, laser-printer-friendly.
"""

from __future__ import annotations

import logging

import matplotlib as mpl

mpl.use("Agg")

# Re-export common utilities for backward compatibility
from python_pkg.praca_magisterska_video.generate_images._sched_common import (
    BG,
    DPI,
    FONTWEIGHT_THRESHOLD,
    FS,
    FS_TITLE,
    GRAY1,
    GRAY2,
    GRAY3,
    GRAY4,
    GRAY5,
    LN,
    MIN_COLUMN_INDEX,
    OUTPUT_DIR,
    draw_arrow,
    draw_box,
)

__all__ = [
    "BG",
    "DPI",
    "FONTWEIGHT_THRESHOLD",
    "FS",
    "FS_TITLE",
    "GRAY1",
    "GRAY2",
    "GRAY3",
    "GRAY4",
    "GRAY5",
    "LN",
    "MIN_COLUMN_INDEX",
    "OUTPUT_DIR",
    "draw_arrow",
    "draw_box",
]
from python_pkg.praca_magisterska_video.generate_images._sched_complexity_edd import (
    draw_complexity_map,
    draw_edd_example,
)
from python_pkg.praca_magisterska_video.generate_images._sched_graham import (
    draw_graham_notation,
)
from python_pkg.praca_magisterska_video.generate_images._sched_johnson import (
    draw_johnson_gantt,
)
from python_pkg.praca_magisterska_video.generate_images._sched_spt_flow_job import (
    draw_flow_vs_job,
    draw_spt_comparison,
)

_logger = logging.getLogger(__name__)

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    _logger.info("Generating scheduling diagrams for PYTANIE 17...")
    draw_graham_notation()
    draw_johnson_gantt()
    draw_spt_comparison()
    draw_flow_vs_job()
    draw_complexity_map()
    draw_edd_example()
    _logger.info("Done! All diagrams saved to: %s", OUTPUT_DIR)
