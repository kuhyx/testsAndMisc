"""Tests for cinema_planner main module."""

from __future__ import annotations

import argparse
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from python_pkg.cinema_planner._cinema_parsing import Movie
from python_pkg.cinema_planner._cinema_scheduling import Screening
from python_pkg.cinema_planner.cinema_planner import (
    _apply_must_watch_filter,
    _build_parser,
    _filter_movies,
    _load_movies_from_file,
    _load_movies_from_stdin,
    _load_movies_interactive,
    _output_schedules,
    main,
)


class TestBuildParser:
    """Tests for _build_parser."""

    def test_parser_created(self) -> None:
        parser = _build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_defaults(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.buffer == 0
        assert args.interactive is False
        assert args.list is False
        assert args.max_schedules == 5
        assert args.input_file is None
        assert args.select is None
        assert args.exclude is None
        assert args.exclude_genre is None
        assert args.all_genres is False
        assert args.output is None
        assert args.must_watch is None

    def test_parser_with_file(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["test.html"])
        assert args.input_file == "test.html"

    def test_parser_interactive(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["-i"])
        assert args.interactive is True

    def test_parser_all_options(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            [
                "test.html",
                "-b",
                "10",
                "-l",
                "-s",
                "Movie",
                "-x",
                "Bad",
                "-g",
                "Horror",
                "--all-genres",
                "-o",
                "out.txt",
                "-n",
                "3",
                "-m",
                "Must",
            ]
        )
        assert args.buffer == 10
        assert args.list is True
        assert args.select == "Movie"
        assert args.exclude == "Bad"
        assert args.exclude_genre == "Horror"
        assert args.all_genres is True
        assert args.output == "out.txt"
        assert args.max_schedules == 3
        assert args.must_watch == "Must"


class TestLoadMoviesInteractive:
    """Tests for _load_movies_interactive."""

    @patch("builtins.input", side_effect=["Movie A, 10:00, 90min", ""])
    def test_single_movie(self, mock: MagicMock) -> None:
        result = _load_movies_interactive()
        assert len(result) == 1
        assert result[0].name == "Movie A"

    @patch(
        "builtins.input",
        side_effect=[
            "Movie A, 10:00, 90min",
            "Movie B, 14:00, 120min",
            "",
        ],
    )
    def test_multiple_movies(self, mock: MagicMock) -> None:
        result = _load_movies_interactive()
        assert len(result) == 2

    @patch("builtins.input", side_effect=EOFError)
    def test_eof(self, mock: MagicMock) -> None:
        result = _load_movies_interactive()
        assert result == []

    @patch("builtins.input", side_effect=["bad line", ""])
    def test_invalid_input(self, mock: MagicMock) -> None:
        result = _load_movies_interactive()
        assert result == []

    @patch(
        "builtins.input",
        side_effect=["bad line", "Movie A, 10:00, 90min", ""],
    )
    def test_mixed_valid_invalid(self, mock: MagicMock) -> None:
        result = _load_movies_interactive()
        assert len(result) == 1


class TestLoadMoviesFromFile:
    """Tests for _load_movies_from_file."""

    @patch(
        "python_pkg.cinema_planner.cinema_planner.parse_cinema_city_html",
    )
    def test_html_file(self, mock_parse: MagicMock) -> None:
        mock_parse.return_value = ([Movie("A", [600], 120)], "2025-01-25")
        movies, date = _load_movies_from_file(Path("test.html"))
        assert len(movies) == 1
        assert date == "2025-01-25"

    @patch(
        "python_pkg.cinema_planner.cinema_planner.parse_cinema_city_html",
    )
    def test_htm_file(self, mock_parse: MagicMock) -> None:
        mock_parse.return_value = ([Movie("A", [600], 120)], None)
        _, _ = _load_movies_from_file(Path("test.htm"))
        mock_parse.assert_called_once()

    @patch(
        "python_pkg.cinema_planner.cinema_planner.parse_cinema_city_pdf",
    )
    def test_pdf_file(self, mock_parse: MagicMock) -> None:
        mock_parse.return_value = [Movie("A", [600], 120)]
        movies, date = _load_movies_from_file(Path("test.pdf"))
        assert len(movies) == 1
        assert date is None

    def test_text_file(self) -> None:
        content = "Movie A, 10:00, 90min\n# comment\nMovie B, 14:00, 120min\n"
        with (
            patch.object(Path, "open", mock_open(read_data=content)),
            patch.object(Path, "suffix", new=".txt"),
        ):
            movies, date = _load_movies_from_file(Path("test.txt"))
        assert len(movies) == 2
        assert date is None

    def test_text_file_with_bad_line(self) -> None:
        content = "Movie A, 10:00, 90min\nbad line\n"
        with (
            patch.object(Path, "open", mock_open(read_data=content)),
            patch.object(Path, "suffix", new=".txt"),
        ):
            movies, _ = _load_movies_from_file(Path("test.txt"))
        assert len(movies) == 1


class TestLoadMoviesFromStdin:
    """Tests for _load_movies_from_stdin."""

    def test_basic(self) -> None:
        with patch("sys.stdin", StringIO("Movie A, 10:00, 90min\n")):
            result = _load_movies_from_stdin()
        assert len(result) == 1

    def test_invalid_line(self) -> None:
        with patch("sys.stdin", StringIO("bad line\n")):
            result = _load_movies_from_stdin()
        assert result == []


class TestFilterMovies:
    """Tests for _filter_movies."""

    def _make_args(self, **kwargs: str | bool | None) -> argparse.Namespace:
        defaults = {
            "select": None,
            "exclude": None,
            "exclude_genre": None,
            "all_genres": False,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_no_filters(self) -> None:
        movies = [Movie("A", [600], 120)]
        result, _ = _filter_movies(movies, self._make_args())
        # Default horror exclusion but no genre matches
        assert len(result) == 1

    def test_select_filter(self) -> None:
        movies = [
            Movie("Inception", [600], 120),
            Movie("Matrix", [600], 120),
        ]
        result, _ = _filter_movies(
            movies,
            self._make_args(select="inception"),
        )
        assert len(result) == 1
        assert result[0].name == "Inception"

    def test_exclude_filter(self) -> None:
        movies = [
            Movie("Inception", [600], 120),
            Movie("Matrix", [600], 120),
        ]
        result, _ = _filter_movies(
            movies,
            self._make_args(exclude="matrix"),
        )
        assert len(result) == 1
        assert result[0].name == "Inception"

    def test_genre_exclusion_default(self) -> None:
        movies = [
            Movie("Horror Movie", [600], 120, ["Horror"]),
            Movie("Comedy Movie", [600], 120, ["Comedy"]),
        ]
        result, excluded = _filter_movies(movies, self._make_args())
        assert len(result) == 1
        assert result[0].name == "Comedy Movie"
        assert "horror" in excluded

    def test_all_genres_flag(self) -> None:
        movies = [
            Movie("Horror Movie", [600], 120, ["Horror"]),
            Movie("Comedy Movie", [600], 120, ["Comedy"]),
        ]
        result, excluded = _filter_movies(
            movies,
            self._make_args(all_genres=True),
        )
        assert len(result) == 2
        assert len(excluded) == 0

    def test_custom_genre_exclusion(self) -> None:
        movies = [
            Movie("Action Movie", [600], 120, ["Action"]),
            Movie("Drama Movie", [600], 120, ["Drama"]),
        ]
        result, _ = _filter_movies(
            movies,
            self._make_args(all_genres=True, exclude_genre="action"),
        )
        assert len(result) == 1
        assert result[0].name == "Drama Movie"

    def test_no_genre_filtered(self) -> None:
        movies = [Movie("Movie", [600], 120, ["Comedy"])]
        result, _ = _filter_movies(movies, self._make_args())
        assert len(result) == 1


class TestApplyMustWatchFilter:
    """Tests for _apply_must_watch_filter."""

    def test_found(self) -> None:
        schedules = [
            [Screening("Movie A", 600, 720)],
            [Screening("Movie B", 600, 720)],
        ]
        result = _apply_must_watch_filter(schedules, "Movie A")
        assert len(result) == 1
        assert result[0][0].movie == "Movie A"

    def test_not_found(self) -> None:
        schedules = [
            [Screening("Movie A", 600, 720)],
            [Screening("Movie B", 600, 720)],
        ]
        result = _apply_must_watch_filter(schedules, "Movie C")
        assert len(result) == 2  # Returns original

    def test_partial_match(self) -> None:
        schedules = [[Screening("The Matrix Reloaded", 600, 720)]]
        result = _apply_must_watch_filter(schedules, "matrix")
        assert len(result) == 1


class TestOutputSchedules:
    """Tests for _output_schedules."""

    def _make_args(self, **kwargs: str | int | None) -> argparse.Namespace:
        defaults = {
            "buffer": 0,
            "max_schedules": 5,
            "output": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    @patch("sys.stdout", new_callable=StringIO)
    def test_basic_output(self, mock_stdout: MagicMock) -> None:
        schedules = [[Screening("A", 600, 720)]]
        _output_schedules(
            schedules,
            ["A"],
            None,
            self._make_args(),
            set(),
        )
        assert "OPTIMAL" in mock_stdout.getvalue()

    @patch("sys.stdout", new_callable=StringIO)
    @patch("builtins.open", mock_open())
    def test_output_to_file(self, mock_stdout: MagicMock) -> None:
        schedules = [[Screening("A", 600, 720)]]
        _output_schedules(
            schedules,
            ["A"],
            None,
            self._make_args(output="out.txt"),
            set(),
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("builtins.open", mock_open())
    def test_output_with_date(self, mock_stdout: MagicMock) -> None:
        schedules = [[Screening("A", 600, 720)]]
        _output_schedules(
            schedules,
            ["A"],
            "2025-01-25",
            self._make_args(),
            set(),
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("builtins.open", mock_open())
    def test_output_with_excluded_genres(self, mock_stdout: MagicMock) -> None:
        schedules = [[Screening("A", 600, 720)]]
        _output_schedules(
            schedules,
            ["A"],
            "2025-01-25",
            self._make_args(),
            {"horror"},
        )


class TestMain:
    """Tests for main function."""

    @patch("sys.argv", ["cinema_planner", "-i"])
    @patch(
        "python_pkg.cinema_planner.cinema_planner._load_movies_interactive",
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_interactive_mode(
        self,
        mock_stdout: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_load.return_value = [Movie("A", [600], 120)]
        main()

    @patch("sys.argv", ["cinema_planner", "test.html"])
    @patch(
        "python_pkg.cinema_planner.cinema_planner._load_movies_from_file",
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_file_mode(
        self,
        mock_stdout: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_load.return_value = ([Movie("A", [600], 120)], "2025-01-25")
        with patch("builtins.open", mock_open()):
            main()

    @patch("sys.argv", ["cinema_planner"])
    @patch(
        "python_pkg.cinema_planner.cinema_planner._load_movies_from_stdin",
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_stdin_mode(
        self,
        mock_stdout: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_load.return_value = [Movie("A", [600], 120)]
        main()

    @patch("sys.argv", ["cinema_planner", "-i"])
    @patch(
        "python_pkg.cinema_planner.cinema_planner._load_movies_interactive",
    )
    def test_no_movies_exits(self, mock_load: MagicMock) -> None:
        mock_load.return_value = []
        with pytest.raises(SystemExit):
            main()

    @patch("sys.argv", ["cinema_planner", "-i", "-l"])
    @patch(
        "python_pkg.cinema_planner.cinema_planner._load_movies_interactive",
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_list_mode(
        self,
        mock_stdout: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_load.return_value = [Movie("A", [600], 120)]
        main()
        assert "Parsed" in mock_stdout.getvalue()

    @patch("sys.argv", ["cinema_planner", "-i", "-m", "Movie A"])
    @patch(
        "python_pkg.cinema_planner.cinema_planner._load_movies_interactive",
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_must_watch(
        self,
        mock_stdout: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_load.return_value = [
            Movie("Movie A", [600], 120),
            Movie("Movie B", [900], 120),
        ]
        main()

    @patch(
        "sys.argv",
        ["cinema_planner", "-i", "-s", "Movie", "-x", "Bad", "-g", "Horror"],
    )
    @patch(
        "python_pkg.cinema_planner.cinema_planner._load_movies_interactive",
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_filters(
        self,
        mock_stdout: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_load.return_value = [
            Movie("Movie Good", [600], 120),
            Movie("Bad Movie", [600], 120),
            Movie("Other", [600], 120),
        ]
        main()
