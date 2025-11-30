import contextlib
import logging
import random
import re
import sys

logging.basicConfig(level=logging.INFO)


def randomize_numbers(numbers, min_percentage=1, max_percentage=20):
    randomized_numbers = []
    for number in numbers:
        percentage = random.uniform(min_percentage, max_percentage) / 100
        if random.choice([True, False]):
            new_number = number + (number * percentage)
        else:
            new_number = number - (number * percentage)
        randomized_numbers.append(new_number)
    return randomized_numbers


def parse_input(input_string):
    # Replace commas with dots and remove non-numeric characters
    # except dots, commas, and digits
    cleaned_input = re.sub(r"[^\d.,\s]", "", input_string).replace(",", ".")
    # Split the cleaned input into individual numbers
    number_strings = cleaned_input.split()
    # Convert the number strings to floats
    numbers = []
    decimal_counts = []
    for num in number_strings:
        try:
            float_num = float(num)
            digits_count = len(num.split(".")[-1]) if "." in num else 0
            numbers.append(float_num)
            decimal_counts.append(digits_count)
        except ValueError:
            continue
    return numbers, decimal_counts


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.info(
            "Usage: python random_digits.py <number1> <number2> ... "
            "[min_percentage max_percentage]"
        )
        sys.exit(1)

    try:
        input_string = " ".join(sys.argv[1:])
        numbers, decimal_counts = parse_input(input_string)
        min_percentage = 1
        max_percentage = 20

        if len(numbers) == 0:
            msg = "No valid numbers provided."
            raise ValueError(msg)

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

        logging.info(f"Original numbers: {numbers}")
        logging.info(f"Randomized numbers: {formatted_numbers}")
    except ValueError as e:
        logging.exception(f"Error: {e}")
        logging.exception("Please provide valid numbers and percentages.")
        sys.exit(1)
