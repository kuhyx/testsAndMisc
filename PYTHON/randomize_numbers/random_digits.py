import random
import sys
import re

def randomize_numbers(numbers, min_percentage=1, max_percentage=20):
    randomized_numbers = []
    for number in numbers:
        percentage = random.uniform(min_percentage, max_percentage) / 100
        change = number * percentage
        if random.choice([True, False]):
            new_number = number + change
        else:
            new_number = number - change
        randomized_numbers.append(new_number)
    return randomized_numbers

def parse_input(input_string):
    # Replace commas with dots and remove non-numeric characters except dots, commas, digits, and minus signs
    cleaned_input = re.sub(r'[^\d.,\s-]', '', input_string).replace(',', '.')
    # Split the cleaned input into individual numbers
    number_strings = re.split(r'\s+', cleaned_input)
    # Convert the number strings to floats
    numbers = []
    decimal_counts = []
    for num in number_strings:
        try:
            float_num = float(num)
            if '.' in num:
                digits_count = len(num.split('.')[-1])
            else:
                digits_count = 0
            numbers.append(float_num)
            decimal_counts.append(digits_count)
        except ValueError:
            continue
    return numbers, decimal_counts

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python random_digits.py <number1> <number2> ... [min_percentage max_percentage]")
        sys.exit(1)

    try:
        input_string = ' '.join(sys.argv[1:])
        numbers, decimal_counts = parse_input(input_string)
        min_percentage = 1
        max_percentage = 20

        if len(numbers) == 0:
            raise ValueError("No valid numbers provided.")

        if len(sys.argv) > len(numbers) + 1:
            try:
                min_percentage = float(sys.argv[len(numbers) + 1])
            except ValueError:
                pass
        if len(sys.argv) > len(numbers) + 2:
            try:
                max_percentage = float(sys.argv[len(numbers) + 2])
            except ValueError:
                pass

        randomized_numbers = randomize_numbers(numbers, min_percentage, max_percentage)
        formatted_numbers = []
        for i, num in enumerate(randomized_numbers):
            format_str = f'.{decimal_counts[i]}f'
            formatted_numbers.append(float(format(num, format_str)))

        print("Original numbers:", numbers)
        print("Randomized numbers:", formatted_numbers)
    except ValueError as e:
        print(f"Error: {e}")
        print("Please provide valid numbers and percentages.")
        sys.exit(1)

