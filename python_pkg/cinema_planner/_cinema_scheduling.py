"""Scheduling algorithm and display formatting for cinema plans."""

from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from python_pkg.cinema_planner._cinema_parsing import Movie

# Ads duration before movie starts (Cinema City shows ~15 min of ads)
ADS_DURATION = 15

_SEPARATOR_WIDTH = 60


@dataclass
class Screening:
    """A specific screening of a movie at a particular time."""

    movie: str
    start: int  # minutes from midnight
    end: int  # minutes from midnight

    def overlaps(self, other: Screening, buffer: int = 0) -> bool:
        """Check if this screening overlaps with another, considering buffer."""
        # Account for ADS_DURATION grace period
        return not (
            self.end + buffer <= other.start + ADS_DURATION
            or other.end + buffer <= self.start + ADS_DURATION
        )

    def start_str(self) -> str:
        """Format start time as HH:MM."""
        return f"{self.start // 60:02d}:{self.start % 60:02d}"

    def end_str(self) -> str:
        """Format end time as HH:MM."""
        return f"{self.end // 60:02d}:{self.end % 60:02d}"


def find_best_schedule(
    movies: list[Movie],
    buffer: int,
) -> list[list[Screening]]:
    """Find ALL schedules that maximize number of movies watched."""
    movie_screenings: list[list[Screening]] = [
        [
            Screening(movie.name, start, start + movie.duration)
            for start in movie.start_times
        ]
        for movie in movies
    ]

    best_count = 0
    all_best_schedules: list[list[Screening]] = []

    def _backtrack(
        movie_idx: int,
        current_schedule: list[Screening],
    ) -> None:
        nonlocal best_count, all_best_schedules

        if movie_idx == len(movie_screenings):
            if len(current_schedule) > best_count:
                best_count = len(current_schedule)
                all_best_schedules = [current_schedule.copy()]
            elif len(current_schedule) == best_count and best_count > 0:
                all_best_schedules.append(current_schedule.copy())
            return

        # Pruning: can't beat the best
        remaining = len(movie_screenings) - movie_idx
        if len(current_schedule) + remaining < best_count:
            return

        # Try each screening of current movie
        for screening in movie_screenings[movie_idx]:
            conflicts = any(screening.overlaps(s, buffer) for s in current_schedule)
            if not conflicts:
                current_schedule.append(screening)
                _backtrack(movie_idx + 1, current_schedule)
                current_schedule.pop()

        # Also try skipping this movie
        _backtrack(movie_idx + 1, current_schedule)

    _backtrack(0, [])

    # Sort each schedule by start time and return
    return [sorted(schedule, key=lambda s: s.start) for schedule in all_best_schedules]


def _format_single_schedule(
    schedule: list[Screening],
    output: TextIO,
) -> None:
    """Format a single schedule to the output stream."""
    for i, screening in enumerate(schedule, 1):
        duration = screening.end - screening.start
        hours, mins = divmod(duration, 60)
        actual_start = screening.start + ADS_DURATION
        actual_start_str = f"{actual_start // 60:02d}:{actual_start % 60:02d}"
        output.write(
            f"  {i}. {screening.start_str()} - "
            f"{screening.end_str()}  {screening.movie}\n"
        )
        output.write(
            f"     Duration: {hours}h {mins}m " f"(movie starts ~{actual_start_str})\n"
        )
        if i < len(schedule):
            gap = schedule[i].start - screening.end
            if gap > 0:
                output.write(f"     [{gap} min break]\n")
        output.write("\n")


def _format_schedules(
    schedules: list[list[Screening]],
    all_movies: list[str],
    date: str | None = None,
    max_display: int = 5,
    *,
    output: TextIO | None = None,
) -> None:
    """Format optimal schedules to the output stream."""
    if output is None:
        output = sys.stdout

    sep = "=" * _SEPARATOR_WIDTH
    thin_sep = "\u2500" * _SEPARATOR_WIDTH

    if not schedules or not schedules[0]:
        output.write("No movies can be scheduled!\n")
        return

    num_movies = len(schedules[0])
    num_schedules = len(schedules)

    output.write(f"\n{sep}\n")
    if date:
        output.write(f"  OPTIMAL CINEMA SCHEDULES - {date}\n")
    else:
        output.write("  OPTIMAL CINEMA SCHEDULES\n")
    output.write(
        f"  {num_movies} movies, " f"{num_schedules} possible combination(s)\n"
    )
    output.write(f"{sep}\n\n")

    display_count = min(num_schedules, max_display)
    for idx, schedule in enumerate(schedules[:display_count], 1):
        if num_schedules > 1:
            output.write(f"{thin_sep}\n")
            output.write(f"  OPTION {idx}:\n")
            output.write(f"{thin_sep}\n\n")
        _format_single_schedule(schedule, output)

    if num_schedules > display_count:
        output.write(f"{thin_sep}\n")
        output.write(
            f"  ... and {num_schedules - display_count} " "more combinations\n"
        )
        output.write("  (use -n to show more, e.g., -n 10)\n")
        output.write("\n")

    # Show skipped movies (from first schedule as reference)
    scheduled_movies = {s.movie for s in schedules[0]}
    skipped = [m for m in all_movies if m not in scheduled_movies]
    if skipped and num_schedules == 1:
        output.write(f"{thin_sep}\n")
        output.write(f"  Skipped movies ({len(skipped)}):\n")
        for movie in skipped:
            output.write(f"    - {movie}\n")
        output.write("\n")


def _format_all_movies(
    movies: list[Movie],
    date: str | None = None,
    *,
    output: TextIO | None = None,
) -> None:
    """Format all parsed movies to the output stream."""
    if output is None:
        output = sys.stdout

    thin_sep = "\u2500" * _SEPARATOR_WIDTH

    output.write(f"\n{thin_sep}\n")
    if date:
        output.write(f"  Parsed {len(movies)} movies for {date}:\n")
    else:
        output.write(f"  Parsed {len(movies)} movies:\n")
    output.write(f"{thin_sep}\n")
    for movie in movies:
        times_str = ", ".join(
            f"{t // 60:02d}:{t % 60:02d}" for t in sorted(movie.start_times)
        )
        genre_str = f" [{', '.join(movie.genres)}]" if movie.genres else ""
        output.write(f"  {movie.name} ({movie.duration} min){genre_str}\n")
        output.write(f"    Times: {times_str}\n")
    output.write("\n")
