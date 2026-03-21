#!/usr/bin/env python3
"""Cinema Day Planner - Maximize movies watched in a day.

Supports:
- Cinema City HTML/PDF schedules (auto-parsed)
- Manual input format

Usage:
    ./cinema_planner.py schedule.html          # Parse Cinema City HTML
    ./cinema_planner.py schedule.pdf           # Parse Cinema City PDF
    ./cinema_planner.py -i                     # Interactive manual input
    ./cinema_planner.py movies.txt             # Manual format file
"""

from __future__ import annotations

import argparse
from contextlib import suppress
from io import StringIO
import logging
from pathlib import Path
import sys

from python_pkg.cinema_planner._cinema_parsing import (
    Movie,
    _try_parse_interactive_line,
    _try_parse_manual_line,
    parse_cinema_city_html,
    parse_cinema_city_pdf,
)
from python_pkg.cinema_planner._cinema_scheduling import (
    Screening,
    _format_all_movies,
    _format_schedules,
    find_best_schedule,
)

logger = logging.getLogger(__name__)

# Default genres to exclude (can be overridden with --all-genres)
DEFAULT_EXCLUDED_GENRES = {"horror"}


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the cinema planner."""
    parser = argparse.ArgumentParser(
        description=("Plan your cinema day to watch as many movies as possible."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supports Cinema City HTML/PDF schedules (auto-detected).

Manual input format (one movie per line):
    Movie Title, start_time1 [or start_time2 ...], duration

Example:
    Inception, 10:30 or 14:00 or 18:30, 2h 28m
    The Matrix, 12:00 or 16:45, 2h 16m
        """,
    )
    parser.add_argument("input_file", nargs="?", help="Input file (HTML/PDF/TXT)")
    parser.add_argument(
        "-b",
        "--buffer",
        type=int,
        default=0,
        help="Buffer time between movies in minutes (default: 0)",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactive mode - enter movies one by one",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all parsed movies without scheduling",
    )
    parser.add_argument(
        "-s",
        "--select",
        type=str,
        help="Comma-separated movie names to include (partial match)",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        type=str,
        help="Comma-separated movie names to exclude (partial match)",
    )
    parser.add_argument(
        "-g",
        "--exclude-genre",
        type=str,
        help="Comma-separated genres to exclude (e.g., 'Horror')",
    )
    parser.add_argument(
        "--all-genres",
        action="store_true",
        help="Include all genres (disable default Horror exclusion)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Save schedule to file (default: cinema_plan_DATE.txt)",
    )
    parser.add_argument(
        "-n",
        "--max-schedules",
        type=int,
        default=5,
        help="Max schedule options to display (default: 5)",
    )
    parser.add_argument(
        "-m",
        "--must-watch",
        type=str,
        help="Only show schedules containing this movie (partial match)",
    )
    return parser


def _load_movies_interactive() -> list[Movie]:
    """Load movies through interactive terminal input."""
    logger.info("Enter movies (empty line to finish):")
    logger.info("Format: Title, start1 [or start2 ...], duration")
    logger.info("Example: Inception, 10:30 or 14:00, 2h 28m")
    logger.info("")
    movies: list[Movie] = []
    with suppress(EOFError):
        while True:
            line = input("> ")
            if not line.strip():
                break
            result = _try_parse_interactive_line(line)
            if result:
                movies.append(result)
    return movies


def _load_movies_from_file(
    filepath: Path,
) -> tuple[list[Movie], str | None]:
    """Load movies from a file (HTML, PDF, or manual format)."""
    suffix = filepath.suffix.lower()
    logger.info("Parsing: %s", filepath)

    if suffix in {".html", ".htm"}:
        return parse_cinema_city_html(str(filepath))

    if suffix == ".pdf":
        return parse_cinema_city_pdf(str(filepath)), None

    movies: list[Movie] = []
    with filepath.open() as f:
        for line in f:
            result = _try_parse_manual_line(line, sys.stderr)
            if result:
                movies.append(result)
    return movies, None


def _load_movies_from_stdin() -> list[Movie]:
    """Load movies from standard input."""
    logger.info("Enter movies (Ctrl+D when done):")
    movies: list[Movie] = []
    for line in sys.stdin:
        result = _try_parse_manual_line(line, sys.stderr)
        if result:
            movies.append(result)
    return movies


def _filter_movies(
    movies: list[Movie],
    args: argparse.Namespace,
) -> tuple[list[Movie], set[str]]:
    """Apply name and genre filters to movies."""
    if args.select:
        select_terms = [t.strip().lower() for t in args.select.split(",")]
        movies = [m for m in movies if any(t in m.name.lower() for t in select_terms)]
        logger.info(
            "Selected %d movies matching: %s",
            len(movies),
            args.select,
        )

    if args.exclude:
        exclude_terms = [t.strip().lower() for t in args.exclude.split(",")]
        movies = [
            m for m in movies if not any(t in m.name.lower() for t in exclude_terms)
        ]
        logger.info("After name exclusion: %d movies", len(movies))

    excluded_genres: set[str] = set()
    if not args.all_genres:
        excluded_genres.update(DEFAULT_EXCLUDED_GENRES)
    if args.exclude_genre:
        excluded_genres.update(g.strip().lower() for g in args.exclude_genre.split(","))

    if excluded_genres:
        before_count = len(movies)
        movies = [
            m for m in movies if not any(g.lower() in excluded_genres for g in m.genres)
        ]
        filtered_count = before_count - len(movies)
        if filtered_count > 0:
            logger.info(
                "Excluded %d movies by genre: %s",
                filtered_count,
                ", ".join(sorted(excluded_genres)),
            )

    return movies, excluded_genres


def _apply_must_watch_filter(
    schedules: list[list[Screening]],
    must_watch: str,
) -> list[list[Screening]]:
    """Filter schedules to only those containing must-watch movie."""
    must_watch_lower = must_watch.lower()
    filtered = [
        s
        for s in schedules
        if any(must_watch_lower in screening.movie.lower() for screening in s)
    ]
    if filtered:
        logger.info(
            "Filtered to %d schedules containing '%s'",
            len(filtered),
            must_watch,
        )
        return filtered

    logger.warning("No optimal schedules contain '%s'", must_watch)
    logger.warning("Showing all schedules instead.")
    return schedules


def _output_schedules(
    schedules: list[list[Screening]],
    all_movie_names: list[str],
    schedule_date: str | None,
    args: argparse.Namespace,
    excluded_genres: set[str],
) -> None:
    """Handle schedule output, optionally saving to file."""
    output_buffer = StringIO()
    _format_schedules(
        schedules,
        all_movie_names,
        schedule_date,
        args.max_schedules,
        output=output_buffer,
    )
    schedule_output = output_buffer.getvalue()
    sys.stdout.write(schedule_output)

    if args.output or schedule_date:
        output_file = (
            Path(args.output)
            if args.output
            else Path(f"cinema_plan_{schedule_date}.txt")
        )
        with output_file.open("w") as f:
            f.write(f"Generated: {schedule_date or 'unknown date'}\n")
            f.write(f"Movies considered: {len(all_movie_names)}\n")
            f.write(f"Buffer time: {args.buffer} minutes\n")
            if excluded_genres:
                f.write(f"Excluded genres: {', '.join(sorted(excluded_genres))}\n")
            f.write(schedule_output)
        logger.info("Schedule saved to: %s", output_file)


def main() -> None:
    """Run the cinema day planner CLI."""
    logging.basicConfig(format="%(message)s", level=logging.INFO)

    parser = _build_parser()
    args = parser.parse_args()

    movies: list[Movie] = []
    schedule_date: str | None = None

    if args.interactive:
        movies = _load_movies_interactive()
    elif args.input_file:
        movies, schedule_date = _load_movies_from_file(
            Path(args.input_file),
        )
    else:
        movies = _load_movies_from_stdin()

    if not movies:
        logger.error("No movies found!")
        sys.exit(1)

    movies, excluded_genres = _filter_movies(movies, args)

    if args.list:
        _format_all_movies(movies, schedule_date)
        return

    logger.info("\nOptimizing schedule for %d movies...", len(movies))
    logger.info("Buffer time between movies: %d minutes", args.buffer)

    schedules = find_best_schedule(movies, args.buffer)
    all_movie_names = [m.name for m in movies]

    if args.must_watch:
        schedules = _apply_must_watch_filter(schedules, args.must_watch)

    _output_schedules(
        schedules,
        all_movie_names,
        schedule_date,
        args,
        excluded_genres,
    )


if __name__ == "__main__":
    main()
