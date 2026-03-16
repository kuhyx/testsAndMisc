#!/usr/bin/env python3
"""Generate all diagrams for PYTANIE 23: Segmentacja obrazu.

A4-compatible, monochrome-friendly (grays + one accent), 300 DPI.
Re-exports all diagram generators from submodules.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys

# Ensure sibling modules are importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _q23_architectures import generate_fcn, generate_unet
from _q23_common import OUTPUT_DIR
from _q23_diy_unet import generate_diy_unet
from _q23_mean_shift_ncuts import generate_mean_shift, generate_normalized_cuts
from _q23_mnemonics import generate_mnemonics
from _q23_nn_basics import generate_dot_product, generate_relu
from _q23_otsu_watershed import generate_otsu_bimodal, generate_watershed
from _q23_receptive_transformer import generate_receptive_field, generate_transformer
from _q23_region_diy import generate_diy_thresholding, generate_region_growing

__all__ = [
    "generate_diy_thresholding",
    "generate_diy_unet",
    "generate_dot_product",
    "generate_fcn",
    "generate_mean_shift",
    "generate_mnemonics",
    "generate_normalized_cuts",
    "generate_otsu_bimodal",
    "generate_receptive_field",
    "generate_region_growing",
    "generate_relu",
    "generate_transformer",
    "generate_unet",
    "generate_watershed",
]

_logger = logging.getLogger(__name__)

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    _logger.info("Generating PYTANIE 23 diagrams...")
    generate_otsu_bimodal()
    generate_watershed()
    generate_mean_shift()
    generate_normalized_cuts()
    generate_relu()
    generate_dot_product()
    generate_fcn()
    generate_unet()
    generate_receptive_field()
    generate_transformer()
    generate_region_growing()
    generate_diy_thresholding()
    generate_diy_unet()
    generate_mnemonics()
    _logger.info("All diagrams saved to: %s", OUTPUT_DIR)
