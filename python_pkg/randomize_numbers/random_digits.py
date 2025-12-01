"""Randomize numbers by applying a random percentage variation."""

import contextlib
import logging
import re
import secrets
import sys

_logger = logging.getLogger(__name__)

# Use cryptographically secure random number generator
_rng = secrets.SystemRandom()

DEFAULT_MIN_PERCENTAGE = 1
DEFAULT_MAX_PERCENTAGE = 20


def randomize_numbers(
    nums: list[float],
    min_pct: float = DEFAULT_MIN_PERCENTAGE,
    max_pct: float = DEFAULT_MAX_PERCENTAGE,
) -> list[float]:
    """Apply random percentage variation to a list of numbers."""
    result = []
    for number in nums:
        percentage = _rng.uniform(min_pct, max_pct) / 100
        if _rng.choice([True, False]):
            new_number = number + (number * percentage)
        else:
            new_number = number - (number * percentage)
        result.append(new_number)
    return result


def parse_input(text: str) -> tuple[list[float], list[int]]:
    """Parse a string of numbers and return floats with decimal counts."""
    # Replace commas with dots and remove non-numeric characters
    # except dots, commas, and digits
    cleaned_input = re.sub(r"[^\d.,\s]", "", text).replace(",", ".")
    # Split the cleaned input into individual numbers
    number_strings = cleaned_input.split()
    # Convert the number strings to floats
    nums: list[float] = []
    decimals: list[int] = []
    for num_str in number_strings:
        parsed = _parse_single_number(num_str)
        if parsed is not None:
            float_num, digits_count = parsed
            nums.append(float_num)
            decimals.append(digits_count)
    return nums, decimals


def _parse_single_number(num_str: str) -> tuple[float, int] | None:
    """Parse a single number string into float and decimal count.

    Args:
        num_str: The number string to parse.

    Returns:
        Tuple of (float value, decimal count) or None if invalid.
    """
    try:
        float_num = float(num_str)
        digits_count = len(num_str.split(".")[-1]) if "." in num_str else 0
    except ValueError:
        return None
    return float_num, digits_count


MIN_ARGS = 2


def main() -> None:
    """Run the number randomizer from command line arguments."""
    if len(sys.argv) < MIN_ARGS:
        _logger.info(
            "Usage: python random_digits.py <number1> <number2> ... "
            "[min_percentage max_percentage]"
        )
        sys.exit(1)

    args_string = " ".join(sys.argv[1:])
    numbers, decimal_counts = parse_input(args_string)

    if not numbers:
        _logger.error("No valid numbers provided.")
        sys.exit(1)

    min_pct = DEFAULT_MIN_PERCENTAGE
    max_pct = DEFAULT_MAX_PERCENTAGE

    try:
        if len(sys.argv) > len(numbers) + 1:
            with contextlib.suppress(ValueError):
                min_pct = float(sys.argv[len(numbers) + 1])
        if len(sys.argv) > len(numbers) + 2:
            with contextlib.suppress(ValueError):
                max_pct = float(sys.argv[len(numbers) + 2])

        randomized = randomize_numbers(numbers, min_pct, max_pct)
        formatted_numbers = []
        for i, num in enumerate(randomized):
            format_str = f".{decimal_counts[i]}f"
            formatted_numbers.append(float(format(num, format_str)))

        _logger.info("Original numbers: %s", numbers)
        _logger.info("Randomized numbers: %s", formatted_numbers)
    except ValueError:
        _logger.exception("Error processing numbers")
        _logger.exception("Please provide valid numbers and percentages.")
        sys.exit(1)


if __name__ == "__main__":
    main()
