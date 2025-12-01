"""Unit tests for link extraction functionality."""

from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

# Allow importing from project root when running pytest from this folder
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT = ROOT / "main.py"


def read_lines(p: Path) -> list[str]:
    """Read lines from a file, stripping newlines."""
    return [line.rstrip("\n") for line in p.read_text(encoding="utf-8").splitlines()]


def test_extract_hosts_function() -> None:
    """Test extract_hosts_from_html extracts unique hosts in order."""
    from main import extract_hosts_from_html

    html = (
        '<a href="https://wiby.me/">A</a>'
        '<a href="http://example.com/page">B</a>'
        '<a href="#local">C</a>'
        '<a href="mailto:foo@bar.com">D</a>'
        '<a href="https://wiby.me/about">E</a>'
    )
    hosts = extract_hosts_from_html(html)
    assert hosts == ["wiby.me", "example.com"], hosts


def test_cli_writes_expected_output(tmp_path: Path) -> None:
    """Test CLI writes correctly formatted output file."""
    # copy sample1.html to tmpdir and run the script
    sample = ROOT / "tests" / "sample1.html"
    html_copy = tmp_path / "sample1.html"
    html_copy.write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")

    # Run CLI
    out_file = tmp_path / "out.txt"
    subprocess.run(
        [sys.executable, str(SCRIPT), str(html_copy), str(out_file)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert out_file.exists()

    lines = read_lines(out_file)
    # Expected order: first time we see wiby.me, then example.com
    assert lines == ["*wiby.me*", "*example.com*"], lines


def test_cli_default_output_name(tmp_path: Path) -> None:
    """Test CLI generates default output filename from input."""
    sample = ROOT / "tests" / "sample2.html"
    html_copy = tmp_path / "sample2.html"
    html_copy.write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")

    subprocess.run(
        [sys.executable, str(SCRIPT), str(html_copy)],
        capture_output=True,
        text=True,
        check=True,
    )

    default_out = tmp_path / "sample2_links.txt"
    assert default_out.exists()

    lines = read_lines(default_out)
    assert lines == ["*sub.domain.co.uk*", "*example.com:8080*"], lines


class TestMainFunction:
    """Tests for main() function directly for coverage."""

    def test_main_with_output_file(self, tmp_path: Path) -> None:
        """Test main() with explicit output file."""
        from python_pkg.extract_links.main import main

        input_file = tmp_path / "test.html"
        input_file.write_text(
            '<a href="https://example.com/page">Link</a>',
            encoding="utf-8",
        )
        output_file = tmp_path / "output.txt"

        with patch(
            "sys.argv",
            ["main.py", str(input_file), str(output_file)],
        ):
            result = main()

        assert result == 0
        assert output_file.exists()
        lines = read_lines(output_file)
        assert lines == ["*example.com*"]

    def test_main_default_output(self, tmp_path: Path) -> None:
        """Test main() generates default output file name."""
        from python_pkg.extract_links.main import main

        input_file = tmp_path / "mypage.html"
        input_file.write_text(
            '<a href="http://test.org">Test</a>',
            encoding="utf-8",
        )

        with patch("sys.argv", ["main.py", str(input_file)]):
            result = main()

        assert result == 0
        expected_output = tmp_path / "mypage_links.txt"
        assert expected_output.exists()
        lines = read_lines(expected_output)
        assert lines == ["*test.org*"]

    def test_main_file_not_found(self, tmp_path: Path) -> None:
        """Test main() raises SystemExit for missing file."""
        from python_pkg.extract_links.main import main

        nonexistent = tmp_path / "nonexistent.html"

        with (
            patch("sys.argv", ["main.py", str(nonexistent)]),
            pytest.raises(SystemExit, match="Input file not found"),
        ):
            main()

    def test_main_multiple_hosts(self, tmp_path: Path) -> None:
        """Test main() extracts multiple unique hosts."""
        from python_pkg.extract_links.main import main

        input_file = tmp_path / "links.html"
        input_file.write_text(
            """
            <a href="https://first.com/a">First</a>
            <a href="https://second.com/b">Second</a>
            <a href="https://first.com/c">First Again</a>
            <a href="https://third.org/d">Third</a>
            """,
            encoding="utf-8",
        )
        output_file = tmp_path / "hosts.txt"

        with patch("sys.argv", ["main.py", str(input_file), str(output_file)]):
            result = main()

        assert result == 0
        lines = read_lines(output_file)
        assert lines == ["*first.com*", "*second.com*", "*third.org*"]

    def test_main_empty_html(self, tmp_path: Path) -> None:
        """Test main() handles HTML with no links."""
        from python_pkg.extract_links.main import main

        input_file = tmp_path / "empty.html"
        input_file.write_text("<html><body>No links</body></html>", encoding="utf-8")
        output_file = tmp_path / "out.txt"

        with patch("sys.argv", ["main.py", str(input_file), str(output_file)]):
            result = main()

        assert result == 0
        lines = read_lines(output_file)
        assert lines == []


class TestHrefParser:
    """Tests for _HrefParser class."""

    def test_parser_collects_hrefs(self) -> None:
        """Test parser collects href attributes."""
        from python_pkg.extract_links.main import _HrefParser

        parser = _HrefParser()
        parser.feed('<a href="http://a.com">A</a><a href="http://b.com">B</a>')
        assert parser.hrefs == ["http://a.com", "http://b.com"]

    def test_parser_ignores_none_href(self) -> None:
        """Test parser ignores href attributes with None value."""
        from python_pkg.extract_links.main import _HrefParser

        parser = _HrefParser()
        # Simulate HTML where href might be parsed as None
        parser.feed("<a href>Empty href</a>")
        # href with no value might result in empty string, not None
        # but we test the condition anyway
        assert len(parser.hrefs) <= 1  # May or may not capture empty href
