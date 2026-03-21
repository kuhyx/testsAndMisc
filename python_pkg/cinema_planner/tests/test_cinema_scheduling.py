"""Tests for _cinema_scheduling module."""

from __future__ import annotations

from io import StringIO

from python_pkg.cinema_planner._cinema_parsing import Movie
from python_pkg.cinema_planner._cinema_scheduling import (
    Screening,
    _format_all_movies,
    _format_schedules,
    _format_single_schedule,
    find_best_schedule,
)


class TestScreening:
    """Tests for Screening dataclass."""

    def test_start_str(self) -> None:
        s = Screening("Movie", 600, 720)
        assert s.start_str() == "10:00"

    def test_end_str(self) -> None:
        s = Screening("Movie", 600, 720)
        assert s.end_str() == "12:00"

    def test_start_str_zero_padded(self) -> None:
        s = Screening("Movie", 65, 180)
        assert s.start_str() == "01:05"

    def test_overlaps_true(self) -> None:
        s1 = Screening("A", 600, 720)
        s2 = Screening("B", 700, 820)
        assert s1.overlaps(s2)

    def test_overlaps_false(self) -> None:
        s1 = Screening("A", 600, 720)
        s2 = Screening("B", 900, 1020)
        assert not s1.overlaps(s2)

    def test_overlaps_with_buffer(self) -> None:
        s1 = Screening("A", 600, 720)
        s2 = Screening("B", 735, 855)
        assert not s1.overlaps(s2, buffer=0)
        # buffer=31 => 720+31=751 > 735+15=750 => overlap
        assert s1.overlaps(s2, buffer=31)

    def test_overlaps_ads_grace(self) -> None:
        # ADS_DURATION is 15. end + buffer <= start + ADS
        # 720 + 0 <= 720 + 15 => True => no overlap
        s1 = Screening("A", 600, 720)
        s2 = Screening("B", 720, 840)
        assert not s1.overlaps(s2)

    def test_overlaps_symmetric(self) -> None:
        s1 = Screening("A", 600, 720)
        s2 = Screening("B", 700, 820)
        assert s1.overlaps(s2)
        assert s2.overlaps(s1)

    def test_no_overlap_reversed_order(self) -> None:
        s1 = Screening("A", 900, 1020)
        s2 = Screening("B", 600, 720)
        assert not s1.overlaps(s2)


class TestFindBestSchedule:
    """Tests for find_best_schedule."""

    def test_single_movie(self) -> None:
        movies = [Movie("A", [600], 120)]
        result = find_best_schedule(movies, 0)
        assert len(result) == 1
        assert len(result[0]) == 1
        assert result[0][0].movie == "A"

    def test_two_non_overlapping(self) -> None:
        movies = [
            Movie("A", [600], 120),
            Movie("B", [900], 120),
        ]
        result = find_best_schedule(movies, 0)
        assert len(result) >= 1
        assert len(result[0]) == 2

    def test_two_overlapping(self) -> None:
        movies = [
            Movie("A", [600], 120),
            Movie("B", [610], 120),
        ]
        result = find_best_schedule(movies, 0)
        # Best schedule has 1 movie (they overlap)
        assert len(result[0]) == 1

    def test_multiple_screenings(self) -> None:
        movies = [
            Movie("A", [600, 900], 120),
            Movie("B", [750], 120),
        ]
        result = find_best_schedule(movies, 0)
        # Should find schedule with both movies A@600 + B@750
        best = result[0]
        assert len(best) == 2

    def test_buffer_time(self) -> None:
        movies = [
            Movie("A", [600], 120),
            Movie("B", [735], 120),  # 15 min gap (exactly ADS_DURATION)
        ]
        # With buffer=0, no overlap
        result_no_buffer = find_best_schedule(movies, 0)
        assert len(result_no_buffer[0]) == 2

        # With large buffer, they do overlap
        result_buffer = find_best_schedule(movies, 31)
        assert len(result_buffer[0]) == 1

    def test_empty_movies(self) -> None:
        result = find_best_schedule([], 0)
        # Empty schedule with 0 movies => best_count stays 0
        assert result == []

    def test_multiple_best_schedules(self) -> None:
        movies = [
            Movie("A", [600], 60),
            Movie("B", [600], 60),
        ]
        result = find_best_schedule(movies, 0)
        assert len(result) == 2  # A or B, both are equally good

    def test_sorted_by_start_time(self) -> None:
        movies = [
            Movie("B", [900], 120),
            Movie("A", [600], 120),
        ]
        result = find_best_schedule(movies, 0)
        assert result[0][0].movie == "A"
        assert result[0][1].movie == "B"

    def test_pruning(self) -> None:
        # Create scenario where pruning is triggered
        movies = [
            Movie("A", [600], 60),
            Movie("B", [700], 60),
            Movie("C", [800], 60),
            Movie("D", [610], 60),  # Overlaps with A
        ]
        result = find_best_schedule(movies, 0)
        # Best has 3 movies (A, B, C)
        assert len(result[0]) == 3


class TestFormatSingleSchedule:
    """Tests for _format_single_schedule."""

    def test_single_screening(self) -> None:
        output = StringIO()
        schedule = [Screening("Movie A", 600, 720)]
        _format_single_schedule(schedule, output)
        text = output.getvalue()
        assert "Movie A" in text
        assert "10:00" in text
        assert "12:00" in text

    def test_multiple_screenings_with_gap(self) -> None:
        output = StringIO()
        schedule = [
            Screening("A", 600, 720),
            Screening("B", 780, 900),
        ]
        _format_single_schedule(schedule, output)
        text = output.getvalue()
        assert "60 min break" in text

    def test_no_gap(self) -> None:
        output = StringIO()
        schedule = [
            Screening("A", 600, 720),
            Screening("B", 720, 840),
        ]
        _format_single_schedule(schedule, output)
        text = output.getvalue()
        assert "break" not in text

    def test_duration_display(self) -> None:
        output = StringIO()
        schedule = [Screening("Movie A", 600, 706)]
        _format_single_schedule(schedule, output)
        text = output.getvalue()
        assert "1h 46m" in text

    def test_actual_start_display(self) -> None:
        output = StringIO()
        schedule = [Screening("Movie A", 600, 720)]
        _format_single_schedule(schedule, output)
        text = output.getvalue()
        # actual start = 600 + 15 = 615 => 10:15
        assert "10:15" in text


class TestFormatSchedules:
    """Tests for _format_schedules."""

    def test_empty_schedules(self) -> None:
        output = StringIO()
        _format_schedules([], ["A"], output=output)
        assert "No movies can be scheduled!" in output.getvalue()

    def test_empty_first_schedule(self) -> None:
        output = StringIO()
        _format_schedules([[]], ["A"], output=output)
        assert "No movies can be scheduled!" in output.getvalue()

    def test_single_schedule(self) -> None:
        output = StringIO()
        schedule = [[Screening("Movie A", 600, 720)]]
        _format_schedules(schedule, ["Movie A"], output=output)
        text = output.getvalue()
        assert "OPTIMAL CINEMA SCHEDULES" in text
        assert "1 movies" in text

    def test_with_date(self) -> None:
        output = StringIO()
        schedule = [[Screening("Movie A", 600, 720)]]
        _format_schedules(schedule, ["Movie A"], "2025-01-25", output=output)
        text = output.getvalue()
        assert "2025-01-25" in text

    def test_no_date(self) -> None:
        output = StringIO()
        schedule = [[Screening("Movie A", 600, 720)]]
        _format_schedules(schedule, ["Movie A"], output=output)
        text = output.getvalue()
        assert "OPTIMAL CINEMA SCHEDULES\n" in text

    def test_multiple_schedules(self) -> None:
        output = StringIO()
        schedules = [
            [Screening("A", 600, 720)],
            [Screening("B", 600, 720)],
        ]
        _format_schedules(schedules, ["A", "B"], output=output)
        text = output.getvalue()
        assert "OPTION 1" in text
        assert "OPTION 2" in text

    def test_max_display_truncation(self) -> None:
        output = StringIO()
        schedules = [
            [Screening("A", 600, 720)],
            [Screening("B", 600, 720)],
            [Screening("C", 600, 720)],
        ]
        _format_schedules(schedules, ["A", "B", "C"], max_display=2, output=output)
        text = output.getvalue()
        assert "1 more combinations" in text
        assert "use -n to show more" in text

    def test_skipped_movies(self) -> None:
        output = StringIO()
        schedules = [[Screening("A", 600, 720)]]
        _format_schedules(schedules, ["A", "B", "C"], output=output)
        text = output.getvalue()
        assert "Skipped movies (2)" in text
        assert "- B" in text
        assert "- C" in text

    def test_no_skipped_with_multiple_schedules(self) -> None:
        output = StringIO()
        schedules = [
            [Screening("A", 600, 720)],
            [Screening("B", 600, 720)],
        ]
        _format_schedules(schedules, ["A", "B", "C"], output=output)
        text = output.getvalue()
        # Skipped only printed when num_schedules == 1
        assert "Skipped" not in text

    def test_default_output_stdout(self) -> None:
        schedule = [[Screening("Movie A", 600, 720)]]
        import sys
        from unittest.mock import patch

        with patch.object(sys, "stdout", new_callable=StringIO) as mock_stdout:
            _format_schedules(schedule, ["Movie A"])
            text = mock_stdout.getvalue()
            assert "OPTIMAL CINEMA SCHEDULES" in text


class TestFormatAllMovies:
    """Tests for _format_all_movies."""

    def test_basic(self) -> None:
        output = StringIO()
        movies = [Movie("Movie A", [600, 840], 120)]
        _format_all_movies(movies, output=output)
        text = output.getvalue()
        assert "Movie A" in text
        assert "120 min" in text

    def test_with_date(self) -> None:
        output = StringIO()
        movies = [Movie("Movie A", [600], 90)]
        _format_all_movies(movies, "2025-01-25", output=output)
        text = output.getvalue()
        assert "2025-01-25" in text

    def test_no_date(self) -> None:
        output = StringIO()
        movies = [Movie("Movie A", [600], 90)]
        _format_all_movies(movies, output=output)
        text = output.getvalue()
        assert "Parsed 1 movies:" in text

    def test_with_genres(self) -> None:
        output = StringIO()
        movies = [Movie("Movie A", [600], 90, ["Action", "Drama"])]
        _format_all_movies(movies, output=output)
        text = output.getvalue()
        assert "[Action, Drama]" in text

    def test_without_genres(self) -> None:
        output = StringIO()
        movies = [Movie("Movie A", [600], 90)]
        _format_all_movies(movies, output=output)
        text = output.getvalue()
        assert "[" not in text.split("Movie A")[1].split("\n")[0]

    def test_default_output_stdout(self) -> None:
        movies = [Movie("Movie A", [600], 90)]
        import sys
        from unittest.mock import patch

        with patch.object(sys, "stdout", new_callable=StringIO) as mock_stdout:
            _format_all_movies(movies)
            text = mock_stdout.getvalue()
            assert "Movie A" in text
