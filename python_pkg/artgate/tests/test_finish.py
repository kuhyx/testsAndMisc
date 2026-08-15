"""Finishing-stage tests.

The finisher is the bridge every continuous-tone route depends on, so its
contract is asserted directly: whatever goes in, what comes out satisfies the
alpha, colour and canvas gates.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter
import pytest

from python_pkg.artgate.finish import (
    ALPHA_CUTOFF,
    binarize_alpha,
    downscale,
    finish,
    quantize,
)
from python_pkg.artgate.pixels import (
    check_alpha_binary,
    check_color_count,
    opaque_rgb,
)


@pytest.fixture(name="smooth")
def fixture_smooth() -> np.ndarray:
    """Return a blurred, many-coloured, soft-alpha source image.

    Returns:
        A ``(256, 256, 4)`` uint8 array standing in for generator output.
    """
    rng = np.random.default_rng(5)
    arr = rng.integers(0, 255, (256, 256, 4), dtype=np.uint8)
    img = Image.fromarray(arr, "RGBA").filter(ImageFilter.GaussianBlur(6))
    return np.asarray(img, dtype=np.uint8)


class TestContract:
    """Finished output satisfies the gates its route could not satisfy."""

    def test_finished_output_passes_gates(self, smooth: np.ndarray) -> None:
        """The end-to-end pipeline yields gate-passing pixel art."""
        out = finish(smooth, target=32, max_colors=16)
        assert out.shape == (32, 32, 4)
        assert check_alpha_binary(out) == []
        assert check_color_count(out, 16) == []

    def test_raw_input_would_have_failed(self, smooth: np.ndarray) -> None:
        """The source genuinely fails, so the test is not vacuous."""
        assert check_alpha_binary(smooth) != []


class TestBinarizeAlpha:
    """Alpha thresholding also canonicalises transparent pixels."""

    def test_threshold_splits_at_cutoff(self) -> None:
        """Values at the cutoff round up, below it round down."""
        arr = np.zeros((1, 2, 4), dtype=np.uint8)
        arr[0, 0] = (9, 9, 9, ALPHA_CUTOFF)
        arr[0, 1] = (9, 9, 9, ALPHA_CUTOFF - 1)
        out = binarize_alpha(arr)
        assert out[0, 0, 3] == 255
        assert out[0, 1, 3] == 0

    def test_transparent_rgb_is_zeroed(self) -> None:
        """Leftover RGB under transparency would inflate colour counts."""
        arr = np.zeros((1, 1, 4), dtype=np.uint8)
        arr[0, 0] = (200, 100, 50, 0)
        assert tuple(binarize_alpha(arr)[0, 0]) == (0, 0, 0, 0)

    def test_source_is_not_mutated(self) -> None:
        """The finisher never edits its caller's array in place."""
        arr = np.full((2, 2, 4), 200, dtype=np.uint8)
        binarize_alpha(arr)
        assert arr[0, 0, 3] == 200


class TestStages:
    """Individual stages behave as documented."""

    def test_downscale_hits_target(self, smooth: np.ndarray) -> None:
        """Box downscaling produces the requested square."""
        assert downscale(smooth, 16).shape == (16, 16, 4)

    def test_quantize_caps_opaque_colours(self) -> None:
        """Quantisation respects the cap over opaque pixels."""
        rng = np.random.default_rng(2)
        arr = rng.integers(0, 255, (16, 16, 4), dtype=np.uint8)
        arr[:, :, 3] = 255
        out = quantize(arr, 8)
        assert np.unique(opaque_rgb(out), axis=0).shape[0] <= 8

    def test_quantize_keeps_transparency_clean(self) -> None:
        """Transparent pixels stay canonical through quantisation."""
        arr = np.zeros((4, 4, 4), dtype=np.uint8)
        arr[0, :, :3] = (10, 20, 30)
        arr[0, :, 3] = 255
        out = quantize(arr, 4)
        assert not out[1:, :, :].any()
