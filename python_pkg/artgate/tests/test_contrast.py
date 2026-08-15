"""Silhouette-contrast tests, with a calibration control pair.

The threshold is justified by controls rather than taste: a near-white subject
scores 5.0 against white and must fail; a mid-grey subject scores ~128 against
both and must pass. A gate whose threshold has no controls is a bug waiting to
reject good art.
"""

from __future__ import annotations

import numpy as np

from python_pkg.artgate.codes import Code
from python_pkg.artgate.contrast import (
    DEFAULT_MIN_DELTA,
    check_silhouette,
    silhouette_delta,
)


def _solid(value: int, alpha: int = 255, size: int = 8) -> np.ndarray:
    """Build a uniform RGBA square.

    Args:
        value: Grey level for all channels.
        alpha: Alpha for every pixel.
        size: Square edge length.

    Returns:
        An ``(size, size, 4)`` uint8 array.
    """
    arr = np.zeros((size, size, 4), dtype=np.uint8)
    arr[:, :, :3] = value
    arr[:, :, 3] = alpha
    return arr


class TestCalibrationControls:
    """Provably-failing and provably-passing inputs bracket the threshold."""

    def test_near_white_fails_against_light(self) -> None:
        """A near-white subject is invisible on white and must fail."""
        arr = _solid(250)
        assert silhouette_delta(arr, 255) < DEFAULT_MIN_DELTA
        assert check_silhouette(arr) == [Code.SILHOUETTE_LOW_CONTRAST]

    def test_near_black_fails_against_dark(self) -> None:
        """A near-black subject is invisible on black and must fail."""
        arr = _solid(4)
        assert silhouette_delta(arr, 0) < DEFAULT_MIN_DELTA
        assert check_silhouette(arr) == [Code.SILHOUETTE_LOW_CONTRAST]

    def test_mid_grey_passes_both(self) -> None:
        """A mid-grey subject reads on both backgrounds and must pass."""
        arr = _solid(128)
        assert check_silhouette(arr) == []

    def test_both_backgrounds_are_required(self) -> None:
        """Passing one background is not sufficient.

        Near-white separates hugely from black (250) yet still fails, which is
        exactly the case a single-background check would wave through.
        """
        arr = _solid(250)
        assert silhouette_delta(arr, 0) == 250.0
        assert check_silhouette(arr) == [Code.SILHOUETTE_LOW_CONTRAST]


class TestEdgeCases:
    """Degenerate inputs fail closed rather than dividing by zero."""

    def test_fully_transparent_is_empty_canvas(self) -> None:
        """An image that paints nothing reports EMPTY_CANVAS."""
        assert check_silhouette(_solid(128, alpha=0)) == [Code.EMPTY_CANVAS]

    def test_delta_is_zero_when_nothing_is_painted(self) -> None:
        """The alpha-weighted mean is defined for a blank image."""
        assert silhouette_delta(_solid(128, alpha=0), 0) == 0.0

    def test_alpha_weighting_ignores_transparent_margin(self) -> None:
        """A transparent margin does not drag the subject's luma."""
        arr = _solid(250, size=8)
        arr[4:, :, 3] = 0
        assert silhouette_delta(arr, 255) == 5.0

    def test_threshold_is_configurable(self) -> None:
        """A style may demand more separation than the default."""
        arr = _solid(128)
        assert check_silhouette(arr, min_delta=200.0) == [Code.SILHOUETTE_LOW_CONTRAST]
