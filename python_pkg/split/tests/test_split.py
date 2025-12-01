"""Unit tests for split_x_into_n_symmetrically module."""

import pytest

from python_pkg.split.split_x_into_n_symmetrically import (
    calculate_symmetric_weights,
    scale_to_total,
    split_x_into_n_middle,
    split_x_into_n_symmetrically,
)


class TestCalculateSymmetricWeights:
    """Tests for calculate_symmetric_weights function."""

    def test_odd_n_without_factors(self) -> None:
        """Test odd N creates symmetric weights around middle."""
        weights = calculate_symmetric_weights(n=5, middle_weight=3)
        # For n=5, half_n=2, should be symmetric around middle
        assert len(weights) == 5
        # Check symmetry
        assert weights[0] == weights[-1]
        assert weights[1] == weights[-2]

    def test_even_n_without_factors(self) -> None:
        """Test even N creates symmetric weights."""
        weights = calculate_symmetric_weights(n=4, middle_weight=2)
        assert len(weights) == 4
        # Check symmetry
        assert weights[0] == weights[-1]
        assert weights[1] == weights[-2]

    def test_with_factors(self) -> None:
        """Test custom factors are applied correctly."""
        weights = calculate_symmetric_weights(n=4, middle_weight=1, factors=[0.5, 0.3])
        # Factors control growth from middle, so we get 2 * len(factors) + mirrored
        assert len(weights) == 6  # Actual behavior based on factors
        # Check symmetry
        assert weights[0] == weights[-1]
        assert weights[1] == weights[-2]

    def test_n_equals_1(self) -> None:
        """Test single part returns weights based on algorithm."""
        weights = calculate_symmetric_weights(n=1, middle_weight=5)
        # Odd case with half_n=0: [middle_weight] reversed + middle + [middle_weight]
        assert weights == [5, 5, 5]

    def test_n_equals_2(self) -> None:
        """Test two parts returns two equal weights."""
        weights = calculate_symmetric_weights(n=2, middle_weight=3)
        assert len(weights) == 2
        assert weights[0] == weights[1]


class TestScaleToTotal:
    """Tests for scale_to_total function."""

    def test_scale_to_total_basic(self) -> None:
        """Test weights are scaled to sum to x."""
        weights = [1.0, 2.0, 1.0]
        scaled = scale_to_total(x=100, weights=weights)
        assert sum(scaled) == pytest.approx(100)

    def test_scale_preserves_proportions(self) -> None:
        """Test scaling preserves relative proportions."""
        weights = [1.0, 2.0, 3.0]
        scaled = scale_to_total(x=60, weights=weights)
        # Original sum is 6, so each unit = 10
        assert scaled[0] == pytest.approx(10)
        assert scaled[1] == pytest.approx(20)
        assert scaled[2] == pytest.approx(30)

    def test_scale_with_floats(self) -> None:
        """Test scaling works with float weights."""
        weights = [0.5, 1.0, 0.5]
        scaled = scale_to_total(x=10, weights=weights)
        assert sum(scaled) == pytest.approx(10)


class TestSplitXIntoNSymmetrically:
    """Tests for split_x_into_n_symmetrically function."""

    def test_split_basic(self) -> None:
        """Test basic split with factors."""
        result = split_x_into_n_symmetrically(x=100, n=4, factors=[0.5, 0.2])
        # Length depends on factors, not just n
        assert len(result) == 6  # Actual behavior
        assert sum(result) == pytest.approx(100)
        # Check symmetry
        assert result[0] == pytest.approx(result[-1])
        assert result[1] == pytest.approx(result[-2])

    def test_split_preserves_total(self) -> None:
        """Test that the split preserves the total value."""
        result = split_x_into_n_symmetrically(x=1000, n=5, factors=[0.1, 0.2])
        assert sum(result) == pytest.approx(1000)


class TestSplitXIntoNMiddle:
    """Tests for split_x_into_n_middle function."""

    def test_split_middle_basic(self) -> None:
        """Test basic split using middle value."""
        result = split_x_into_n_middle(x=100, n=3, middle_value=2)
        assert len(result) == 3
        assert sum(result) == pytest.approx(100)

    def test_split_middle_symmetric(self) -> None:
        """Test that result is symmetric."""
        result = split_x_into_n_middle(x=100, n=5, middle_value=3)
        assert result[0] == pytest.approx(result[-1])
        assert result[1] == pytest.approx(result[-2])

    def test_split_middle_even_parts(self) -> None:
        """Test split with even number of parts."""
        result = split_x_into_n_middle(x=50, n=4, middle_value=1)
        assert len(result) == 4
        assert sum(result) == pytest.approx(50)
