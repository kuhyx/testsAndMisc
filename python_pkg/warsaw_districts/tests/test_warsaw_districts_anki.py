"""Tests for the Warsaw districts Anki generator."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pytest

try:
    from python_pkg.warsaw_districts.warsaw_districts_anki import (
        WARSAW_DISTRICTS,
        create_district_map,
        generate_anki_package,
        generate_district_image_bytes,
        main,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from python_pkg.warsaw_districts.warsaw_districts_anki import (
        WARSAW_DISTRICTS,
        create_district_map,
        generate_anki_package,
        generate_district_image_bytes,
        main,
    )


class TestDistricts:
    """Tests for Warsaw districts data."""

    def test_has_18_districts(self) -> None:
        """Test that we have exactly 18 Warsaw districts."""
        assert len(WARSAW_DISTRICTS) == 18

    def test_all_districts_have_names(self) -> None:
        """Test that all districts have non-empty names."""
        for district in WARSAW_DISTRICTS:
            assert district.name
            assert isinstance(district.name, str)
            assert len(district.name) > 0

    def test_all_districts_have_valid_coordinates(self) -> None:
        """Test that all districts have coordinates in valid range."""
        for district in WARSAW_DISTRICTS:
            assert 0 <= district.x <= 1
            assert 0 <= district.y <= 1

    def test_districts_are_unique(self) -> None:
        """Test that all district names are unique."""
        names = [d.name for d in WARSAW_DISTRICTS]
        assert len(names) == len(set(names))

    def test_known_districts_present(self) -> None:
        """Test that all known Warsaw districts are in the list."""
        district_names = {d.name for d in WARSAW_DISTRICTS}
        # Check all 18 districts
        expected_districts = {
            "Bemowo",
            "Białołęka",
            "Bielany",
            "Mokotów",
            "Ochota",
            "Praga-Południe",
            "Praga-Północ",
            "Rembertów",
            "Śródmieście",
            "Targówek",
            "Ursus",
            "Ursynów",
            "Wawer",
            "Wesoła",
            "Wilanów",
            "Włochy",
            "Wola",
            "Żoliborz",
        }
        assert district_names == expected_districts


class TestCreateDistrictMap:
    """Tests for creating district maps."""

    def test_creates_figure(self) -> None:
        """Test that create_district_map returns a Figure."""
        district = WARSAW_DISTRICTS[0]
        fig = create_district_map(district)
        assert fig is not None
        # Clean up
        plt.close(fig)

    def test_creates_figure_for_all_districts(self) -> None:
        """Test that we can create maps for all districts."""
        for district in WARSAW_DISTRICTS:
            fig = create_district_map(district)
            assert fig is not None
            plt.close(fig)


class TestGenerateDistrictImageBytes:
    """Tests for generating district image bytes."""

    def test_generates_bytes(self) -> None:
        """Test that generate_district_image_bytes returns bytes."""
        district = WARSAW_DISTRICTS[0]
        image_bytes = generate_district_image_bytes(district)
        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 0

    def test_generates_for_all_districts(self) -> None:
        """Test that we can generate images for all districts."""
        for district in WARSAW_DISTRICTS:
            image_bytes = generate_district_image_bytes(district)
            assert isinstance(image_bytes, bytes)
            assert len(image_bytes) > 0


class TestGenerateAnkiPackage:
    """Tests for generating Anki package."""

    def test_generates_package(self) -> None:
        """Test that output is a genanki Package."""
        package = generate_anki_package("Test Deck")
        assert package is not None
        assert len(package.decks) == 1

    def test_generates_notes_for_all_districts(self) -> None:
        """Test that package contains cards for all 18 districts."""
        package = generate_anki_package()
        deck = package.decks[0]
        assert len(deck.notes) == len(WARSAW_DISTRICTS)

    def test_custom_deck_name(self) -> None:
        """Test that custom deck name is used."""
        package = generate_anki_package("Custom Deck")
        deck = package.decks[0]
        assert deck.name == "Custom Deck"


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

    def test_help_flag(self) -> None:
        """Test that --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
