"""Tests for _cinema_parsing module."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

from python_pkg.cinema_planner._cinema_parsing import (
    _exit_no_pdf_support,
    _parse_cinema_city_pdf_basic,
    _try_parse_interactive_line,
    _try_parse_manual_line,
    _try_parse_time,
    extract_date_from_html,
    parse_cinema_city_html,
    parse_cinema_city_pdf,
    parse_cinema_city_text,
    parse_duration,
    parse_manual_line,
    parse_time,
)


class TestParseTime:
    """Tests for parse_time."""

    def test_standard_time(self) -> None:
        assert parse_time("18:20") == 18 * 60 + 20

    def test_time_with_spaces(self) -> None:
        assert parse_time("  09:05  ") == 9 * 60 + 5

    def test_time_with_dot(self) -> None:
        assert parse_time("14.30") == 14 * 60 + 30

    def test_single_digit_hour(self) -> None:
        assert parse_time("9:05") == 9 * 60 + 5

    def test_midnight(self) -> None:
        assert parse_time("0:00") == 0

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time("abc")

    def test_invalid_no_colon(self) -> None:
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time("1820")


class TestParseDuration:
    """Tests for parse_duration."""

    def test_minutes_with_min(self) -> None:
        assert parse_duration("110 min") == 110

    def test_minutes_with_min_no_space(self) -> None:
        assert parse_duration("90min") == 90

    def test_hours_and_minutes(self) -> None:
        assert parse_duration("1h 46m") == 106

    def test_hours_only(self) -> None:
        assert parse_duration("2h") == 120

    def test_minutes_only_m(self) -> None:
        assert parse_duration("46m") == 46

    def test_colon_format(self) -> None:
        assert parse_duration("1:46") == 106

    def test_pure_number(self) -> None:
        assert parse_duration("110") == 110

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("abc")


class TestParseManualLine:
    """Tests for parse_manual_line."""

    def test_basic_line(self) -> None:
        result = parse_manual_line("Inception, 10:30 or 14:00, 2h 28m")
        assert result is not None
        assert result.name == "Inception"
        assert result.start_times == [10 * 60 + 30, 14 * 60]
        assert result.duration == 148

    def test_empty_line(self) -> None:
        assert parse_manual_line("") is None

    def test_comment_line(self) -> None:
        assert parse_manual_line("# comment") is None

    def test_whitespace_line(self) -> None:
        assert parse_manual_line("   ") is None

    def test_too_few_parts(self) -> None:
        with pytest.raises(ValueError, match="Invalid line format"):
            parse_manual_line("Movie, 10:30")

    def test_single_time(self) -> None:
        result = parse_manual_line("Movie A, 18:20, 1h 46m")
        assert result is not None
        assert result.start_times == [18 * 60 + 20]

    def test_multiple_times(self) -> None:
        result = parse_manual_line("Movie B, 10:00 or 14:00 or 18:00, 120")
        assert result is not None
        assert len(result.start_times) == 3

    def test_duration_with_comma(self) -> None:
        # If duration part contains comma, the rest after parts[1] is duration
        result = parse_manual_line("Movie C, 10:00, 1h, 30m")
        assert result is not None


class TestTryParseTime:
    """Tests for _try_parse_time."""

    def test_valid(self) -> None:
        assert _try_parse_time("10:30") == 10 * 60 + 30

    def test_invalid(self) -> None:
        assert _try_parse_time("abc") is None


class TestTryParseManualLine:
    """Tests for _try_parse_manual_line."""

    def test_valid_line(self) -> None:
        result = _try_parse_manual_line("Movie, 10:00, 90min")
        assert result is not None
        assert result.name == "Movie"

    def test_invalid_line_with_error_stream(self) -> None:
        stream = MagicMock()
        result = _try_parse_manual_line("bad line", stream)
        assert result is None
        stream.write.assert_called_once()

    def test_invalid_line_no_error_stream(self) -> None:
        result = _try_parse_manual_line("bad line")
        assert result is None

    def test_empty_line(self) -> None:
        result = _try_parse_manual_line("")
        assert result is None


class TestTryParseInteractiveLine:
    """Tests for _try_parse_interactive_line."""

    def test_valid_line(self) -> None:
        result = _try_parse_interactive_line("Movie, 10:00, 90min")
        assert result is not None
        assert result.name == "Movie"

    def test_invalid_line(self) -> None:
        result = _try_parse_interactive_line("bad line")
        assert result is None

    def test_empty_line(self) -> None:
        result = _try_parse_interactive_line("")
        assert result is None


class TestExtractDateFromHtml:
    """Tests for extract_date_from_html."""

    def test_found_date(self) -> None:
        assert extract_date_from_html("schedule 2025-01-25 data") == "2025-01-25"

    def test_no_date(self) -> None:
        assert extract_date_from_html("no date here") is None

    def test_non_202x_date(self) -> None:
        assert extract_date_from_html("1999-01-01") is None


class TestParseCinemaCityHtml:
    """Tests for parse_cinema_city_html."""

    def _make_html_section(
        self,
        name: str,
        duration: int,
        times: list[str],
        *,
        genre: str = "",
    ) -> str:
        genre_html = ""
        if genre:
            genre_html = f'<span class="mr-sm">{genre}<span>x</span></span>'
        times_html = "".join(
            f'<button class="btn btn-primary btn-lg">{t}</button>' for t in times
        )
        return (
            f'class="row movie-row">'
            f'<span class="qb-movie-name">{name}</span>'
            f"{genre_html}"
            f"<span>{duration} min</span>"
            f"{times_html}"
        )

    def _patch_open(self, html: str) -> Any:
        return patch.object(Path, "open", mock_open(read_data=html))

    def test_parse_single_movie(self) -> None:
        html = "header" + self._make_html_section("Movie A", 120, ["10:00", "14:00"])
        with self._patch_open(html):
            movies, date = parse_cinema_city_html("test.html")
        assert len(movies) == 1
        assert movies[0].name == "Movie A"
        assert movies[0].duration == 120
        assert len(movies[0].start_times) == 2

    def test_parse_with_date(self) -> None:
        html = "2025-01-25 stuff" + self._make_html_section("Movie A", 90, ["18:00"])
        with self._patch_open(html):
            movies, date = parse_cinema_city_html("test.html")
        assert date == "2025-01-25"

    def test_parse_with_genres(self) -> None:
        html = "header" + self._make_html_section(
            "Horror Film", 100, ["20:00"], genre="Horror, Thriller"
        )
        with self._patch_open(html):
            movies, date = parse_cinema_city_html("test.html")
        assert len(movies) == 1
        assert "Horror" in movies[0].genres
        assert "Thriller" in movies[0].genres

    def test_no_name_match(self) -> None:
        html = 'header class="row movie-row"> no name here'
        with self._patch_open(html):
            movies, date = parse_cinema_city_html("test.html")
        assert len(movies) == 0

    def test_no_duration_match(self) -> None:
        html = (
            'header class="row movie-row">'
            '<span class="qb-movie-name">Movie</span>'
            "no duration here"
            '<button class="btn btn-primary btn-lg">10:00</button>'
        )
        with self._patch_open(html):
            movies, date = parse_cinema_city_html("test.html")
        assert len(movies) == 0

    def test_no_times_match(self) -> None:
        html = (
            'header class="row movie-row">'
            '<span class="qb-movie-name">Movie</span>'
            "<span>100 min</span>"
        )
        with self._patch_open(html):
            movies, date = parse_cinema_city_html("test.html")
        assert len(movies) == 0

    def test_alternate_time_pattern(self) -> None:
        html = (
            'header class="row movie-row">'
            '<span class="qb-movie-name">Movie</span>'
            "<span>100 min</span>"
            "> 10:00 (HTTPS://something"
        )
        with self._patch_open(html):
            movies, date = parse_cinema_city_html("test.html")
        assert len(movies) == 1

    def test_deduplicate_movies(self) -> None:
        section = self._make_html_section("Movie A", 120, ["10:00"])
        html = "header" + section + section
        with self._patch_open(html):
            movies, _ = parse_cinema_city_html("test.html")
        assert len(movies) == 1

    def test_no_genre_match(self) -> None:
        html = (
            'header class="row movie-row">'
            '<span class="qb-movie-name">Movie</span>'
            "<span>100 min</span>"
            '<button class="btn btn-primary btn-lg">10:00</button>'
        )
        with self._patch_open(html):
            movies, _ = parse_cinema_city_html("test.html")
        assert len(movies) == 1
        assert movies[0].genres == []


class TestParseCinemaCityPdf:
    """Tests for parse_cinema_city_pdf."""

    @patch("python_pkg.cinema_planner._cinema_parsing._pdfplumber")
    def test_with_pdfplumber(self, mock_pdfplumber: MagicMock) -> None:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "MOVIE TITLE\n110 min\n10:00\n"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__ = MagicMock(
            return_value=mock_pdf,
        )
        mock_pdfplumber.open.return_value.__exit__ = MagicMock(return_value=False)
        result = parse_cinema_city_pdf("test.pdf")
        assert isinstance(result, list)

    @patch(
        "python_pkg.cinema_planner._cinema_parsing._pdfplumber",
        None,
    )
    @patch(
        "python_pkg.cinema_planner._cinema_parsing._parse_cinema_city_pdf_basic",
    )
    def test_fallback_to_basic(self, mock_basic: MagicMock) -> None:
        mock_basic.return_value = []
        result = parse_cinema_city_pdf("test.pdf")
        mock_basic.assert_called_once_with("test.pdf")
        assert result == []

    @patch("python_pkg.cinema_planner._cinema_parsing._pdfplumber")
    def test_pdfplumber_page_no_text(
        self,
        mock_pdfplumber: MagicMock,
    ) -> None:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__ = MagicMock(
            return_value=mock_pdf,
        )
        mock_pdfplumber.open.return_value.__exit__ = MagicMock(return_value=False)
        result = parse_cinema_city_pdf("test.pdf")
        assert result == []


class TestParseCinemaCityPdfBasic:
    """Tests for _parse_cinema_city_pdf_basic."""

    @patch("python_pkg.cinema_planner._cinema_parsing._fitz")
    def test_with_fitz(self, mock_fitz: MagicMock) -> None:
        mock_page = MagicMock()
        mock_page.get_text.return_value = "MOVIE TITLE\n110 min\n10:00\n"
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_fitz.open.return_value = mock_doc
        result = _parse_cinema_city_pdf_basic("test.pdf")
        mock_doc.close.assert_called_once()
        assert isinstance(result, list)

    @patch("python_pkg.cinema_planner._cinema_parsing._fitz", None)
    @patch("python_pkg.cinema_planner._cinema_parsing.shutil")
    def test_pdftotext_success(self, mock_shutil: MagicMock) -> None:
        mock_shutil.which.return_value = "/usr/bin/pdftotext"
        mock_result = MagicMock()
        mock_result.stdout = "MOVIE TITLE\n110 min\n10:00\n"
        with patch(
            "python_pkg.cinema_planner._cinema_parsing.subprocess.run",
            return_value=mock_result,
        ):
            result = _parse_cinema_city_pdf_basic("test.pdf")
        assert isinstance(result, list)

    @patch("python_pkg.cinema_planner._cinema_parsing._fitz", None)
    @patch("python_pkg.cinema_planner._cinema_parsing.shutil")
    def test_no_pdftotext(self, mock_shutil: MagicMock) -> None:
        mock_shutil.which.return_value = None
        with pytest.raises(SystemExit):
            _parse_cinema_city_pdf_basic("test.pdf")

    @patch("python_pkg.cinema_planner._cinema_parsing._fitz", None)
    @patch("python_pkg.cinema_planner._cinema_parsing.shutil")
    def test_pdftotext_process_error(self, mock_shutil: MagicMock) -> None:
        mock_shutil.which.return_value = "/usr/bin/pdftotext"
        with (
            patch(
                "python_pkg.cinema_planner._cinema_parsing.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "pdftotext"),
            ),
            pytest.raises(SystemExit),
        ):
            _parse_cinema_city_pdf_basic("test.pdf")


class TestExitNoPdfSupport:
    """Tests for _exit_no_pdf_support."""

    def test_exits(self) -> None:
        with pytest.raises(SystemExit):
            _exit_no_pdf_support()


class TestParseCinemaCityText:
    """Tests for parse_cinema_city_text."""

    def test_single_movie(self) -> None:
        text = "MOVIE TITLE\n110 min\n10:00\n14:00\n"
        result = parse_cinema_city_text(text)
        assert len(result) == 1
        assert result[0].name == "Movie Title"
        assert result[0].duration == 110
        assert len(result[0].start_times) == 2

    def test_multiple_movies(self) -> None:
        text = "FIRST MOVIE\n90 min\n10:00\nSECOND MOVIE\n120 min\n14:00\n18:00\n"
        result = parse_cinema_city_text(text)
        assert len(result) == 2

    def test_movie_without_duration(self) -> None:
        text = "MOVIE TITLE\n10:00\n14:00\n"
        result = parse_cinema_city_text(text)
        assert len(result) == 1
        assert result[0].duration == 120  # default

    def test_no_times(self) -> None:
        text = "MOVIE TITLE\n110 min\nno times here\n"
        result = parse_cinema_city_text(text)
        assert len(result) == 0

    def test_empty_text(self) -> None:
        result = parse_cinema_city_text("")
        assert result == []

    def test_title_too_short(self) -> None:
        text = "AB\n110 min\n10:00\n"
        result = parse_cinema_city_text(text)
        assert len(result) == 0

    def test_lowercase_line_ignored_as_title(self) -> None:
        text = "some lowercase text\n110 min\n10:00\n"
        result = parse_cinema_city_text(text)
        assert len(result) == 0

    def test_duration_in_lookahead(self) -> None:
        text = "MOVIE TITLE\nsome other line\n95 min\n10:00\n"
        result = parse_cinema_city_text(text)
        assert len(result) == 1
        assert result[0].duration == 95

    def test_deduplicates_times(self) -> None:
        text = "MOVIE TITLE\n110 min\n10:00\n10:00\n"
        result = parse_cinema_city_text(text)
        assert len(result) == 1
        assert len(result[0].start_times) == 1

    def test_movie_saved_when_new_title_found(self) -> None:
        text = "FIRST MOVIE\n90 min\n10:00\nSECOND MOVIE\n120 min\n14:00\n"
        result = parse_cinema_city_text(text)
        assert len(result) == 2
        assert result[0].name == "First Movie"
        assert result[1].name == "Second Movie"

    def test_time_on_same_line_as_other_text(self) -> None:
        text = "MOVIE TITLE\n110 min\nSome text 10:00 more text\n"
        result = parse_cinema_city_text(text)
        assert len(result) == 1

    def test_try_parse_time_returns_none(self) -> None:
        # Time pattern \b(\d{1,2}:\d{2})\b matches but parse_time fails
        # This can happen when parse_time validates more strictly
        text = "MOVIE TITLE\n110 min\n10:00\n"
        with patch(
            "python_pkg.cinema_planner._cinema_parsing._try_parse_time",
            side_effect=lambda t: None,
        ):
            result = parse_cinema_city_text(text)
        assert len(result) == 0

    def test_movie_no_times_not_saved(self) -> None:
        # Movie with title but no valid times on subsequent lines
        text = "MOVIE ONE\n110 min\nno times\nMOVIE TWO\n90 min\n10:00\n"
        result = parse_cinema_city_text(text)
        assert len(result) == 1
        assert result[0].name == "Movie Two"
