"""Anki flashcard generator for Polish car license plates.

Generates Anki-compatible flashcard decks with bidirectional cards for Polish
vehicle registration plate codes and their corresponding locations.

Creates two types of cards:
1. Code → Location (e.g., WY → Warszawa Wola)
2. Location → Code (e.g., Warszawa Wola → WY)

Usage:
    # Generate Anki cards for all Polish license plates
    python -m python_pkg.polish_license_plates.polish_license_plates_anki

    # Specify custom output file
    python -m python_pkg.polish_license_plates.polish_license_plates_anki \
        --output plates.apkg

Output:
    Creates a self-contained .apkg file that can be directly imported into Anki.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import random
import sys
from typing import TYPE_CHECKING

import genanki

from python_pkg.polish_license_plates.license_plate_data import LICENSE_PLATE_CODES

if TYPE_CHECKING:
    from collections.abc import Sequence


def generate_anki_package(
    deck_name: str = "Polish License Plates",
) -> genanki.Package:
    """Generate Anki package (.apkg) for Polish license plates.

    Creates two cards for each license plate code:
    1. Code → Location
    2. Location → Code

    Args:
        deck_name: Name for the Anki deck.

    Returns:
        genanki.Package object ready to be written to file.
    """
    # Create unique model ID based on deck name
    model_id_hash = hashlib.md5(
        f"polish_license_plates_{deck_name}".encode(),
        usedforsecurity=False,
    )
    model_id = int(model_id_hash.hexdigest()[:8], 16)

    # Define the note model with centered styling and bidirectional templates
    card_css = """
.card {
    font-family: Arial, sans-serif;
    font-size: 28px;
    text-align: center;
    color: #333;
    background-color: #fff;
}
.card.night_mode {
    color: #eee;
    background-color: #2f2f2f;
}
.question {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 60vh;
    font-size: 48px;
    font-weight: bold;
    color: #2C3E50;
}
.card.night_mode .question {
    color: #ECF0F1;
}
.answer {
    font-size: 36px;
    font-weight: bold;
    margin-top: 20px;
    color: #27AE60;
}
.card.night_mode .answer {
    color: #2ECC71;
}
.plate-code {
    font-family: 'Courier New', monospace;
    background-color: #FFD700;
    color: #000;
    padding: 15px 30px;
    border: 3px solid #000;
    border-radius: 8px;
    display: inline-block;
    letter-spacing: 5px;
}
.card.night_mode .plate-code {
    background-color: #FFA500;
}
"""

    my_model = genanki.Model(
        model_id,
        "Polish License Plate Model",
        fields=[
            {"name": "Code"},
            {"name": "Location"},
        ],
        templates=[
            {
                "name": "Code → Location",
                "qfmt": '<div class="question">'
                '<span class="plate-code">{{Code}}</span>'
                "</div>",
                "afmt": '<div class="question">'
                '<span class="plate-code">{{Code}}</span>'
                "</div>"
                '<hr id="answer">'
                '<div class="answer">{{Location}}</div>',
            },
            {
                "name": "Location → Code",
                "qfmt": '<div class="question">{{Location}}</div>',
                "afmt": '<div class="question">{{Location}}</div>'
                '<hr id="answer">'
                '<div class="answer">'
                '<span class="plate-code">{{Code}}</span>'
                "</div>",
            },
        ],
        css=card_css,
    )

    # Create unique deck ID
    deck_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311

    # Create the deck
    my_deck = genanki.Deck(deck_id, deck_name)

    # Generate notes for each license plate code
    for code, location in sorted(LICENSE_PLATE_CODES.items()):
        note = genanki.Note(
            model=my_model,
            fields=[code, location],
            tags=["geography", "poland", "license-plates", "transportation"],
        )
        my_deck.add_note(note)

    # Create package
    return genanki.Package(my_deck)


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command line arguments.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Generate Anki flashcards for Polish license plates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: polish_license_plates.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Polish License Plates",
        help="Name for the Anki deck (default: 'Polish License Plates')",
    )

    args = parser.parse_args(argv)

    # Determine output path
    output_path = (
        Path(args.output) if args.output else Path("polish_license_plates.apkg")
    )

    try:
        num_codes = len(LICENSE_PLATE_CODES)
        num_cards = num_codes * 2  # Two cards per code (bidirectional)

        sys.stdout.write(
            f"Generating flashcards for {num_codes} Polish license plate codes...\n"
        )
        sys.stdout.write(
            "Each code will have 2 cards: Code → Location and Location → Code\n"
        )

        # Generate the package
        package = generate_anki_package(args.deck_name)

        # Write to file
        package.write_to_file(str(output_path))

        sys.stdout.write("\n")
        sys.stdout.write("=" * 70 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 70 + "\n")
        sys.stdout.write(f"License plate codes: {num_codes}\n")
        sys.stdout.write(f"Total flashcards: {num_cards} (bidirectional)\n")
        sys.stdout.write(f"Output file: {output_path.absolute()}\n")
        sys.stdout.write("\n")
        sys.stdout.write("Card types:\n")
        sys.stdout.write("  1. Code → Location (e.g., WY → Warszawa Wola)\n")
        sys.stdout.write("  2. Location → Code (e.g., Warszawa Wola → WY)\n")
        sys.stdout.write("\n")
        sys.stdout.write("To import into Anki:\n")
        sys.stdout.write("  1. Open Anki\n")
        sys.stdout.write("  2. File → Import\n")
        sys.stdout.write(f"  3. Select: {output_path.absolute()}\n")
        sys.stdout.write("  4. Click Import\n")
        sys.stdout.write("\n")
        sys.stdout.write("You can now learn Polish license plates both ways!\n")
    except (OSError, ValueError) as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
