"""Tests for _q23_region_diy (part 2): generate_diy_thresholding coverage."""

from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

pytestmark = pytest.mark.usefixtures("_no_savefig")


def test_draw_otsu_variance_and_pseudocode() -> None:
    """_draw_otsu_variance_and_pseudocode computes and plots Otsu curve."""
    from _q23_region_diy import _draw_otsu_variance_and_pseudocode

    fig, (ax_var, ax_code) = plt.subplots(1, 2)
    size = 64
    img = np.ones((size, size)) * 200
    yy, xx = np.mgrid[:size, :size]
    mask = ((xx - 32) ** 2 + (yy - 32) ** 2) < 15**2
    img[mask] = 60
    img += np.random.default_rng(42).normal(0, 10, img.shape)
    img = np.clip(img, 0, 255)

    best_t = _draw_otsu_variance_and_pseudocode(ax_var, ax_code, img)
    assert isinstance(best_t, int)
    assert 0 < best_t < 255
    plt.close(fig)


def test_draw_otsu_variance_uniform_image() -> None:
    """Handle bimodal image so Otsu finds a valid threshold."""
    from _q23_region_diy import _draw_otsu_variance_and_pseudocode

    fig, (ax_var, ax_code) = plt.subplots(1, 2)
    img = np.ones((32, 32)) * 50.0
    img[16:, :] = 200.0

    best_t = _draw_otsu_variance_and_pseudocode(ax_var, ax_code, img)
    assert isinstance(best_t, int)
    plt.close(fig)


def test_generate_diy_thresholding() -> None:
    """generate_diy_thresholding runs all 6 panels without error."""
    from _q23_region_diy import generate_diy_thresholding

    generate_diy_thresholding()
