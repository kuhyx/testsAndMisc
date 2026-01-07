"""Tests for the Warsaw districts Anki generator."""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from python_pkg.warsaw_districts.warsaw_districts_anki import (
        WARSAW_DISTRICTS,
        create_district_map,
        generate_anki_deck,
        main,
        save_district_image,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from python_pkg.warsaw_districts.warsaw_districts_anki import (
        WARSAW_DISTRICTS,
        create_district_map,
        generate_anki_deck,
        main,
        save_district_image,
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
        """Test that known Warsaw districts are in the list."""
        district_names = {d.name for d in WARSAW_DISTRICTS}
        # Check a few well-known districts
        assert "Śródmieście" in district_names
        assert "Mokotów" in district_names
        assert "Praga-Północ" in district_names
        assert "Żoliborz" in district_names


class TestCreateDistrictMap:
    """Tests for creating district maps."""

    def test_creates_figure(self) -> None:
        """Test that create_district_map returns a Figure."""
        district = WARSAW_DISTRICTS[0]
        fig = create_district_map(district)
        assert fig is not None
        # Clean up
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_creates_figure_for_all_districts(self) -> None:
        """Test that we can create maps for all districts."""
        import matplotlib.pyplot as plt

        for district in WARSAW_DISTRICTS:
            fig = create_district_map(district)
            assert fig is not None
            plt.close(fig)


class TestSaveDistrictImage:
    """Tests for saving district images."""

    def test_saves_image_file(self, tmp_path: Path) -> None:
        """Test that save_district_image creates a file."""
        district = WARSAW_DISTRICTS[0]
        image_path = save_district_image(district, tmp_path)

        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.parent == tmp_path

    def test_saves_all_district_images(self, tmp_path: Path) -> None:
        """Test that we can save images for all districts."""
        for district in WARSAW_DISTRICTS:
            image_path = save_district_image(district, tmp_path)
            assert image_path.exists()


class TestGenerateAnkiDeck:
    """Tests for generating Anki deck content."""

    def test_generates_valid_header(self, tmp_path: Path) -> None:
        """Test that output contains valid Anki headers."""
        result = generate_anki_deck(tmp_path, "Test Deck")

        assert "#separator:semicolon" in result
        assert "#deck:Test Deck" in result
        assert "#html:true" in result

    def test_generates_flashcard_for_all_districts(self, tmp_path: Path) -> None:
        """Test that output contains cards for all 18 districts."""
        result = generate_anki_deck(tmp_path)

        # Check that all district names appear in the output
        for district in WARSAW_DISTRICTS:
            assert district.name in result

    def test_generates_images_for_all_districts(self, tmp_path: Path) -> None:
        """Test that images are generated for all districts."""
        generate_anki_deck(tmp_path)

        # Check that all image files were created
        image_files = list(tmp_path.glob("*.png"))
        assert len(image_files) == 18

    def test_output_format(self, tmp_path: Path) -> None:
        """Test that output has correct semicolon-separated format."""
        result = generate_anki_deck(tmp_path)

        lines = result.split("\n")
        # Skip header lines and empty lines
        data_lines = [line for line in lines if line and not line.startswith("#")]

        # Each data line should have exactly 2 fields (front;back)
        for line in data_lines:
            fields = line.split(";")
            assert len(fields) == 2
            # Front should contain <img src=
            assert "<img src=" in fields[0]
            # Back should be a district name
            assert fields[1] in {d.name for d in WARSAW_DISTRICTS}


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output_file(self, tmp_path: Path) -> None:
        """Test that main creates the output file."""
        output_file = tmp_path / "test_output.txt"
        image_dir = tmp_path / "images"

        result = main(
            [
                "--output",
                str(output_file),
                "--image-dir",
                str(image_dir),
            ]
        )

        assert result == 0
        assert output_file.exists()
        assert image_dir.exists()

    def test_creates_images(self, tmp_path: Path) -> None:
        """Test that main creates image files."""
        output_file = tmp_path / "test_output.txt"
        image_dir = tmp_path / "images"

        main(
            [
                "--output",
                str(output_file),
                "--image-dir",
                str(image_dir),
            ]
        )

        image_files = list(image_dir.glob("*.png"))
        assert len(image_files) == 18

    def test_custom_deck_name(self, tmp_path: Path) -> None:
        """Test that custom deck name is used."""
        output_file = tmp_path / "test_output.txt"
        image_dir = tmp_path / "images"

        main(
            [
                "--output",
                str(output_file),
                "--image-dir",
                str(image_dir),
                "--deck-name",
                "Custom Deck",
            ]
        )

        content = output_file.read_text()
        assert "#deck:Custom Deck" in content

    def test_help_flag(self) -> None:
        """Test that --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
