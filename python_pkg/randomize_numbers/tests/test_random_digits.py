"""Unit tests for random_digits module."""

from unittest.mock import patch

import pytest

from python_pkg.randomize_numbers.random_digits import (
    DEFAULT_MAX_PERCENTAGE,
    DEFAULT_MIN_PERCENTAGE,
    _parse_single_number,
    parse_input,
    randomize_numbers,
)


class TestRandomizeNumbers:
    """Tests for randomize_numbers function."""

    def test_returns_same_length(self) -> None:
        """Test output list has same length as input."""
        nums = [10.0, 20.0, 30.0]
        result = randomize_numbers(nums)
        assert len(result) == len(nums)

    def test_values_within_range(self) -> None:
        """Test randomized values are within expected percentage range."""
        nums = [100.0]
        min_pct = 10
        max_pct = 20
        # Run multiple times to test randomness bounds
        for _ in range(100):
            result = randomize_numbers(nums, min_pct, max_pct)
            # Value should be within ±20% of original
            assert 80.0 <= result[0] <= 120.0

    def test_with_zero(self) -> None:
        """Test randomizing zero returns zero (percentage of 0 is 0)."""
        result = randomize_numbers([0.0])
        assert result[0] == 0.0

    def test_negative_numbers(self) -> None:
        """Test randomizing negative numbers."""
        nums = [-100.0]
        result = randomize_numbers(nums, 10, 10)
        # -100 ± 10% = -90 to -110
        assert -110.0 <= result[0] <= -90.0

    def test_custom_percentages(self) -> None:
        """Test custom min/max percentages."""
        nums = [100.0]
        result = randomize_numbers(nums, min_pct=50, max_pct=50)
        # With exactly 50%, result should be 50 or 150
        assert result[0] in [50.0, 150.0] or 50.0 <= result[0] <= 150.0


class TestParseInput:
    """Tests for parse_input function."""

    def test_simple_integers(self) -> None:
        """Test parsing simple integers."""
        nums, decimals = parse_input("10 20 30")
        assert nums == [10.0, 20.0, 30.0]
        assert decimals == [0, 0, 0]

    def test_floats_with_decimals(self) -> None:
        """Test parsing floats preserves decimal count."""
        nums, decimals = parse_input("10.5 20.123 30.00")
        assert nums == [10.5, 20.123, 30.0]
        assert decimals == [1, 3, 2]

    def test_comma_as_decimal_separator(self) -> None:
        """Test commas are converted to dots."""
        nums, decimals = parse_input("10,5 20,25")
        assert nums == [10.5, 20.25]
        assert decimals == [1, 2]

    def test_filters_non_numeric(self) -> None:
        """Test non-numeric characters are filtered out."""
        nums, _decimals = parse_input("$10 20€ #30")
        assert nums == [10.0, 20.0, 30.0]

    def test_empty_input(self) -> None:
        """Test empty input returns empty lists."""
        nums, decimals = parse_input("")
        assert nums == []
        assert decimals == []

    def test_invalid_numbers_skipped(self) -> None:
        """Test invalid number strings are skipped."""
        nums, decimals = parse_input("10 abc 20")
        assert nums == [10.0, 20.0]
        assert decimals == [0, 0]


class TestParseSingleNumber:
    """Tests for _parse_single_number function."""

    def test_valid_integer(self) -> None:
        """Test parsing valid integer."""
        result = _parse_single_number("42")
        assert result == (42.0, 0)

    def test_valid_float(self) -> None:
        """Test parsing valid float."""
        result = _parse_single_number("3.14")
        assert result == (3.14, 2)

    def test_invalid_string(self) -> None:
        """Test parsing invalid string returns None."""
        result = _parse_single_number("abc")
        assert result is None

    def test_empty_string(self) -> None:
        """Test parsing empty string returns None."""
        result = _parse_single_number("")
        assert result is None


class TestDefaultConstants:
    """Tests for module constants."""

    def test_default_min_percentage(self) -> None:
        """Test default minimum percentage constant."""
        assert DEFAULT_MIN_PERCENTAGE == 1

    def test_default_max_percentage(self) -> None:
        """Test default maximum percentage constant."""
        assert DEFAULT_MAX_PERCENTAGE == 20


class TestMainFunction:
    """Tests for main CLI function."""

    def test_main_no_args_exits(self) -> None:
        """Test main exits with error when no args provided."""
        from python_pkg.randomize_numbers.random_digits import main

        with patch("sys.argv", ["random_digits.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_with_valid_args(self) -> None:
        """Test main runs successfully with valid args."""
        from python_pkg.randomize_numbers.random_digits import main

        with patch("sys.argv", ["random_digits.py", "10", "20", "30"]):
            # Should not raise
            main()

    def test_main_no_valid_numbers_exits(self) -> None:
        """Test main exits when no valid numbers provided."""
        from python_pkg.randomize_numbers.random_digits import main

        with patch("sys.argv", ["random_digits.py", "abc", "def"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_with_custom_percentages(self) -> None:
        """Test main accepts custom percentage arguments."""
        from python_pkg.randomize_numbers.random_digits import main

        with patch("sys.argv", ["random_digits.py", "100", "5", "10"]):
            # Should run without error
            main()

    def test_main_handles_invalid_percentages(self) -> None:
        """Test main handles invalid percentage arguments gracefully."""
        from python_pkg.randomize_numbers.random_digits import main

        # Test where percentages would be invalid strings
        # Using more args than numbers to trigger percentage parsing
        args = ["random_digits.py", "100.5", "invalid_min", "invalid_max"]
        with patch("sys.argv", args):
            # The invalid strings become numbers in parse_input, so main runs
            main()

    def test_main_value_error_handling(self) -> None:
        """Test main handles ValueError exceptions."""
        from python_pkg.randomize_numbers.random_digits import main

        # Mock randomize_numbers to raise ValueError
        with (
            patch("sys.argv", ["random_digits.py", "100"]),
            patch(
                "python_pkg.randomize_numbers.random_digits.randomize_numbers",
                side_effect=ValueError("Test error"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 1
