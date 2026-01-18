#!/usr/bin/env python3
"""Fetch Polish license plate codes from Wikipedia.

This script scrapes the Wikipedia page "Vehicle registration plates of Poland"
to extract the official license plate codes and their corresponding locations.

The data is extracted from the wikitable on the page and saved to license_plate_data.py.

Usage:
    python -m python_pkg.polish_license_plates.fetch_license_plates

Source:
    https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Poland

Note:
    This script requires internet access and the following packages:
    - requests
    - beautifulsoup4
    - lxml
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

try:
    from bs4 import BeautifulSoup
    import requests
except ImportError:
    sys.stderr.write(
        "Error: Required packages not installed.\n"
        "Install with: pip install requests beautifulsoup4 lxml\n"
    )
    sys.exit(1)


def fetch_wikipedia_license_plates() -> dict[str, str]:
    """Fetch Polish license plate codes from Wikipedia.

    Returns:
        Dictionary mapping license plate codes to their locations.

    Raises:
        RuntimeError: If the page cannot be fetched or parsed.
    """
    url = "https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Poland"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    }

    sys.stdout.write(f"Fetching data from {url}...\n")

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        msg = f"Failed to fetch Wikipedia page: {e}"
        raise RuntimeError(msg) from e

    soup = BeautifulSoup(response.text, "html.parser")

    # Find all wikitables
    tables = soup.find_all("table", {"class": "wikitable"})

    if not tables:
        msg = "No wikitable found on the page"
        raise RuntimeError(msg)

    sys.stdout.write(f"Found {len(tables)} tables on the page\n")

    license_plates: dict[str, str] = {}

    # Process each table
    for table_idx, table in enumerate(tables):
        rows = table.find_all("tr")

        sys.stdout.write(f"Processing table {table_idx + 1} with {len(rows)} rows...\n")

        for row in rows[1:]:  # Skip header row
            cells = row.find_all(["td", "th"])

            if len(cells) >= 2:  # noqa: PLR2004
                # Extract code and location
                code_text = cells[0].get_text(strip=True)
                location_text = cells[1].get_text(strip=True)

                # Clean up the code (remove spaces, keep only letters)
                code = re.sub(r"[^A-Z]", "", code_text.upper())

                # Skip if code is invalid
                if not code or len(code) > 4:  # noqa: PLR2004
                    continue

                # Clean up location text (remove citations, extra spaces)
                location = re.sub(r"\[[0-9]+\]", "", location_text)
                location = " ".join(location.split())

                if location:
                    license_plates[code] = location

    sys.stdout.write(f"Extracted {len(license_plates)} license plate codes\n")

    return license_plates


def generate_license_plate_data_file(
    license_plates: dict[str, str],
    output_path: Path,
) -> None:
    """Generate license_plate_data.py file with the extracted data.

    Args:
        license_plates: Dictionary mapping codes to locations.
        output_path: Path to the output file.
    """
    # Group by first letter (voivodeship)
    voivodeships: dict[str, list[tuple[str, str]]] = {}
    for code, location in sorted(license_plates.items()):
        first_letter = code[0]
        if first_letter not in voivodeships:
            voivodeships[first_letter] = []
        voivodeships[first_letter].append((code, location))

    # Voivodeship names
    voivodeship_names = {
        "B": "Podlaskie",
        "C": "Kujawsko-Pomorskie",
        "D": "Dolnośląskie",
        "E": "Łódzkie",
        "F": "Lubuskie",
        "G": "Pomorskie",
        "K": "Małopolskie",
        "L": "Lubelskie",
        "N": "Warmińsko-Mazurskie",
        "O": "Opolskie",
        "P": "Wielkopolskie",
        "R": "Podkarpackie",
        "S": "Śląskie",
        "T": "Świętokrzyskie",
        "W": "Mazowieckie",
        "Z": "Zachodniopomorskie",
    }

    # Generate file content
    content = '''"""Database of Polish car license plate registration codes.

This module contains a comprehensive mapping of Polish vehicle registration
plate codes to their corresponding locations (cities, powiats, voivodeships).

Polish license plates use a system where:
- First letter indicates the voivodeship (province)
- Following 1-2 letters indicate the specific city or powiat (county)

The database is organized by voivodeships in alphabetical order:
- B: Podlaskie
- C: Kujawsko-Pomorskie
- D: Dolnośląskie
- E: Łódzkie
- F: Lubuskie
- G: Pomorskie
- K: Małopolskie
- L: Lubelskie
- N: Warmińsko-Mazurskie
- O: Opolskie
- P: Wielkopolskie
- R: Podkarpackie
- S: Śląskie
- T: Świętokrzyskie
- W: Mazowieckie
- Z: Zachodniopomorskie

Data source:
    Wikipedia - Vehicle registration plates of Poland
    https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Poland

Auto-generated by:
    python -m python_pkg.polish_license_plates.fetch_license_plates

Examples:
    WA = Warszawa (Warsaw)
    KR = Kraków
    GD = Gdańsk
"""

from __future__ import annotations

LICENSE_PLATE_CODES: dict[str, str] = {
'''

    # Add entries grouped by voivodeship
    for letter in sorted(voivodeships.keys()):
        voivodeship_name = voivodeship_names.get(letter, f"Voivodeship {letter}")
        codes = voivodeships[letter]

        content += f"    # {letter} - {voivodeship_name} ({len(codes)} codes)\n"

        for code, location in codes:
            # Escape quotes in location
            location_escaped = location.replace('"', '\\"')
            content += f'    "{code}": "{location_escaped}",\n'

        content += "\n"

    # Remove last comma and newline, then close the dict
    content = content.rstrip(",\n") + "\n}\n"

    # Write to file
    output_path.write_text(content, encoding="utf-8")
    sys.stdout.write(f"Generated {output_path}\n")


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    try:
        # Fetch data from Wikipedia
        license_plates = fetch_wikipedia_license_plates()

        # Determine output path
        script_dir = Path(__file__).parent
        output_path = script_dir / "license_plate_data.py"

        # Generate the file
        generate_license_plate_data_file(license_plates, output_path)

        sys.stdout.write("\n")
        sys.stdout.write("=" * 70 + "\n")
        sys.stdout.write("LICENSE PLATE DATA UPDATE COMPLETE\n")
        sys.stdout.write("=" * 70 + "\n")
        sys.stdout.write(f"Total codes: {len(license_plates)}\n")
        sys.stdout.write(f"Output file: {output_path}\n")
        sys.stdout.write("\n")
        sys.stdout.write("Data source: Wikipedia\n")
        sys.stdout.write(
            "URL: https://en.wikipedia.org/wiki/"
            "Vehicle_registration_plates_of_Poland\n"
        )
        sys.stdout.write("\n")
        sys.stdout.write("Next steps:\n")
        sys.stdout.write("  1. Review the generated file\n")
        sys.stdout.write(
            "  2. Run tests: " "pytest python_pkg/polish_license_plates/tests/\n"
        )
        sys.stdout.write(
            "  3. Regenerate Anki package: "
            "python -m python_pkg.polish_license_plates.polish_license_plates_anki\n"
        )

    except RuntimeError as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
