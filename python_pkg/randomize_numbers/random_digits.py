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
    numbers: list[float],
    min_percentage: float = DEFAULT_MIN_PERCENTAGE,
    max_percentage: float = DEFAULT_MAX_PERCENTAGE,
) -> list[float]:
    """Apply random percentage variation to a list of numbers."""
    randomized_numbers = []
    for number in numbers:
        percentage = _rng.uniform(min_percentage, max_percentage) / 100
        if _rng.choice([True, False]):
            new_number = number + (number * percentage)
        else:
            new_number = number - (number * percentage)
        randomized_numbers.append(new_number)
    return randomized_numbers


def parse_input(input_string: str) -> tuple[list[float], list[int]]:
    """Parse a string of numbers and return floats with decimal counts."""
    # Replace commas with dots and remove non-numeric characters
    # except dots, commas, and digits
    cleaned_input = re.sub(r"[^\d.,\s]", "", input_string).replace(",", ".")
    # Split the cleaned input into individual numbers
    number_strings = cleaned_input.split()
    # Convert the number strings to floats
    numbers: list[float] = []
    decimal_counts: list[int] = []
    for num in number_strings:
        parsed = _parse_single_number(num)
        if parsed is not None:
            float_num, digits_count = parsed
            numbers.append(float_num)
            decimal_counts.append(digits_count)
    return numbers, decimal_counts


def _parse_single_number(num: str) -> tuple[float, int] | None:
    """Parse a single number string into float and decimal count.

    Args:
        num: The number string to parse.

    Returns:
        Tuple of (float value, decimal count) or None if invalid.
    """
    try:
        float_num = float(num)
        digits_count = len(num.split(".")[-1]) if "." in num else 0
    except ValueError:
        return None
    else:
        return float_num, digits_count


MIN_ARGS = 2

if __name__ == "__main__":
    if len(sys.argv) < MIN_ARGS:
        _logger.info(
            "Usage: python random_digits.py <number1> <number2> ... "
            "[min_percentage max_percentage]"
        )
        sys.exit(1)

    input_string = " ".join(sys.argv[1:])
    numbers, decimal_counts = parse_input(input_string)

    if len(numbers) == 0:
        _logger.error("No valid numbers provided.")
        sys.exit(1)

    min_percentage = DEFAULT_MIN_PERCENTAGE
    max_percentage = DEFAULT_MAX_PERCENTAGE

    try:
        if len(sys.argv) > len(numbers) + 1:
            with contextlib.suppress(ValueError):
                min_percentage = float(sys.argv[len(numbers) + 1])
        if len(sys.argv) > len(numbers) + 2:
            with contextlib.suppress(ValueError):
                max_percentage = float(sys.argv[len(numbers) + 2])

        randomized_numbers = randomize_numbers(numbers, min_percentage, max_percentage)
        formatted_numbers = []
        for i, num in enumerate(randomized_numbers):
            format_str = f".{decimal_counts[i]}f"
            formatted_numbers.append(float(format(num, format_str)))

        _logger.info("Original numbers: %s", numbers)
        _logger.info("Randomized numbers: %s", formatted_numbers)
    except ValueError:
        _logger.exception("Error processing numbers")
        _logger.exception("Please provide valid numbers and percentages.")
        sys.exit(1)
