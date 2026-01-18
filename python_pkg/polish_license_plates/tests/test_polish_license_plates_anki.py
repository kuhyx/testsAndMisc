"""Tests for the Polish license plates Anki generator."""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from python_pkg.polish_license_plates.license_plate_data import (
        LICENSE_PLATE_CODES,
    )
    from python_pkg.polish_license_plates.polish_license_plates_anki import (
        generate_anki_package,
        main,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from python_pkg.polish_license_plates.license_plate_data import (
        LICENSE_PLATE_CODES,
    )
    from python_pkg.polish_license_plates.polish_license_plates_anki import (
        generate_anki_package,
        main,
    )


class TestLicensePlateData:
    """Tests for license plate data."""

    def test_has_codes(self) -> None:
        """Test that we have license plate codes."""
        assert len(LICENSE_PLATE_CODES) > 0

    def test_all_codes_are_uppercase(self) -> None:
        """Test that all codes are uppercase strings."""
        for code in LICENSE_PLATE_CODES:
            assert isinstance(code, str)
            assert code.isupper()
            assert len(code) >= 2

    def test_all_locations_are_strings(self) -> None:
        """Test that all locations are non-empty strings."""
        for location in LICENSE_PLATE_CODES.values():
            assert isinstance(location, str)
            assert len(location) > 0

    def test_no_duplicate_codes(self) -> None:
        """Test that all codes are unique."""
        codes = list(LICENSE_PLATE_CODES.keys())
        assert len(codes) == len(set(codes))

    def test_warsaw_codes_present(self) -> None:
        """Test that Warsaw codes are in the database."""
        warsaw_codes = [
            "WA",
            "WB",
            "WC",
            "WD",
            "WE",
            "WF",
            "WG",
            "WH",
            "WI",
            "WJ",
            "WK",
            "WL",
            "WM",
            "WN",
            "WO",
            "WP",
            "WR",
            "WS",
            "WT",
            "WU",
            "WW",
            "WX",
            "WY",
            "WZ",
        ]
        for code in warsaw_codes:
            assert code in LICENSE_PLATE_CODES

    def test_major_cities_present(self) -> None:
        """Test that major Polish cities have codes."""
        major_cities = {
            "WA": "Warszawa",
            "KR": "Kraków",
            "GD": "Gdańsk",
            "PO": "Poznań",
            "WR": "Radom",
            "BI": "Białystok",
        }
        for code, city_part in major_cities.items():
            assert code in LICENSE_PLATE_CODES
            assert city_part.lower() in LICENSE_PLATE_CODES[code].lower()

    def test_voivodeship_prefixes_present(self) -> None:
        """Test that all 16 voivodeship prefixes are represented."""
        voivodeship_prefixes = {
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "K",
            "L",
            "N",
            "O",
            "P",
            "R",
            "S",
            "T",
            "W",
            "Z",
        }
        found_prefixes = {code[0] for code in LICENSE_PLATE_CODES}
        assert voivodeship_prefixes.issubset(found_prefixes)


class TestGenerateAnkiPackage:
    """Tests for generating Anki package."""

    def test_generates_package(self) -> None:
        """Test that output is a genanki Package."""
        package = generate_anki_package("Test Deck")
        assert package is not None
        assert len(package.decks) == 1

    def test_generates_notes_for_all_codes(self) -> None:
        """Test that package contains notes for all license plate codes."""
        package = generate_anki_package()
        deck = package.decks[0]
        # Each code generates one note with two card templates
        assert len(deck.notes) == len(LICENSE_PLATE_CODES)

    def test_custom_deck_name(self) -> None:
        """Test that custom deck name is used."""
        package = generate_anki_package("Custom Deck")
        deck = package.decks[0]
        assert deck.name == "Custom Deck"

    def test_notes_have_correct_fields(self) -> None:
        """Test that notes have Code and Location fields."""
        package = generate_anki_package()
        deck = package.decks[0]
        note = deck.notes[0]
        # Note should have 2 fields: Code and Location
        assert len(note.fields) == 2
        # Fields should be non-empty strings
        assert len(note.fields[0]) > 0
        assert len(note.fields[1]) > 0

    def test_notes_have_tags(self) -> None:
        """Test that notes have appropriate tags."""
        package = generate_anki_package()
        deck = package.decks[0]
        note = deck.notes[0]
        assert "geography" in note.tags
        assert "poland" in note.tags
        assert "license-plates" in note.tags

    def test_model_has_bidirectional_templates(self) -> None:
        """Test that the model has two card templates (bidirectional)."""
        package = generate_anki_package()
        deck = package.decks[0]
        model = deck.notes[0].model
        # Should have 2 templates: Code → Location and Location → Code
        assert len(model.templates) == 2


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output_file(self, tmp_path: Path) -> None:
        """Test that main creates the output file."""
        output_file = tmp_path / "test_output.apkg"

        result = main(
            [
                "--output",
                str(output_file),
            ]
        )

        assert result == 0
        assert output_file.exists()

    def test_custom_deck_name(self, tmp_path: Path) -> None:
        """Test that custom deck name is used."""
        output_file = tmp_path / "test_output.apkg"

        result = main(
            [
                "--output",
                str(output_file),
                "--deck-name",
                "Custom Deck",
            ]
        )

        assert result == 0
        assert output_file.exists()

    def test_default_output_path(self) -> None:
        """Test that default output path is used when not specified."""
        # Clean up any existing file
        default_path = Path("polish_license_plates.apkg")
        if default_path.exists():
            default_path.unlink()

        result = main([])

        assert result == 0
        assert default_path.exists()

        # Clean up
        default_path.unlink()

    def test_help_flag(self) -> None:
        """Test that --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
