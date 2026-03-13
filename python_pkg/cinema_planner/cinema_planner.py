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
from dataclasses import dataclass, field
import importlib
from io import StringIO
import logging
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    import types

logger = logging.getLogger(__name__)

# Default genres to exclude (can be overridden with --all-genres)
DEFAULT_EXCLUDED_GENRES = {"horror"}

# Ads duration before movie starts (Cinema City shows ~15 min of ads)
ADS_DURATION = 15

# Constants for validation and parsing
_MIN_MANUAL_LINE_PARTS = 3
_MIN_TITLE_LENGTH = 3
_DEFAULT_MOVIE_DURATION = 120
_TITLE_LOOKAHEAD_LINES = 5
_SEPARATOR_WIDTH = 60


def _try_import(name: str) -> types.ModuleType | None:
    """Attempt to import a module, returning None if unavailable."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


_pdfplumber = _try_import("pdfplumber")
_fitz = _try_import("fitz")


@dataclass
class Movie:
    """A movie with screening times and metadata."""

    name: str
    start_times: list[int]
    duration: int
    genres: list[str] = field(default_factory=list)


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


def parse_time(time_str: str) -> int:
    """Parse time string like '18:20' to minutes from midnight."""
    time_str = time_str.strip().replace(".", ":")
    match = re.match(r"(\d{1,2}):(\d{2})", time_str)
    if not match:
        msg = f"Invalid time format: {time_str}"
        raise ValueError(msg)
    hours, minutes = int(match.group(1)), int(match.group(2))
    return hours * 60 + minutes


def parse_duration(duration_str: str) -> int:
    """Parse duration like '1h 46m', '1:46', '106m', '110 min', etc."""
    duration_str = duration_str.strip().lower()

    # Try "X min" format (from Cinema City)
    match = re.search(r"(\d+)\s*min", duration_str)
    if match:
        return int(match.group(1))

    hours = 0
    minutes = 0

    h_match = re.search(r"(\d+)\s*h", duration_str)
    m_match = re.search(r"(\d+)\s*m(?!in)", duration_str)

    if h_match or m_match:
        if h_match:
            hours = int(h_match.group(1))
        if m_match:
            minutes = int(m_match.group(1))
        return hours * 60 + minutes

    # Try "H:MM" format
    match = re.match(r"(\d+):(\d{2})", duration_str)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))

    # Try pure minutes
    match = re.match(r"(\d+)", duration_str)
    if match:
        return int(match.group(1))

    msg = f"Invalid duration format: {duration_str}"
    raise ValueError(msg)


def parse_manual_line(line: str) -> Movie | None:
    """Parse a manual format line like 'Movie A, 18:20 or 20:50, 1h 46m'."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = line.split(",")
    if len(parts) < _MIN_MANUAL_LINE_PARTS:
        msg = f"Invalid line format: {line}"
        raise ValueError(msg)

    movie = parts[0].strip()
    times_str = parts[1].strip()
    duration_str = ",".join(parts[2:]).strip()

    start_times = [
        parse_time(time_part)
        for time_part in re.split(r"\s+or\s+", times_str, flags=re.IGNORECASE)
    ]

    duration = parse_duration(duration_str)

    return Movie(movie, start_times, duration)


def _try_parse_time(time_str: str) -> int | None:
    """Try to parse a time string, returning None on failure."""
    try:
        return parse_time(time_str)
    except ValueError:
        return None


def _try_parse_manual_line(
    line: str,
    error_stream: TextIO | None = None,
) -> Movie | None:
    """Try to parse a manual line, writing errors to error_stream."""
    try:
        return parse_manual_line(line)
    except ValueError as e:
        if error_stream is not None:
            error_stream.write(f"Warning: {e}\n")
        return None


def _try_parse_interactive_line(line: str) -> Movie | None:
    """Try to parse a line in interactive mode, logging errors."""
    try:
        result = parse_manual_line(line)
    except ValueError:
        logger.exception("  Error parsing input")
        return None
    if result:
        logger.info("  Added: %s", result.name)
    return result


def extract_date_from_html(content: str) -> str | None:
    """Extract schedule date from Cinema City HTML."""
    # Look for date in YYYY-MM-DD format
    match = re.search(r"(202\d-\d{2}-\d{2})", content)
    if match:
        return match.group(1)
    return None


def parse_cinema_city_html(
    filepath: str,
) -> tuple[list[Movie], str | None]:
    """Parse Cinema City HTML schedule.

    Returns:
        Tuple of (movies, date).
    """
    with Path(filepath).open(encoding="utf-8") as f:
        content = f.read()

    movies: list[Movie] = []
    schedule_date = extract_date_from_html(content)

    # Split content by movie sections
    sections = re.split(r'class="row movie-row', content)

    for section in sections[1:]:  # Skip first (before any movie)
        # Get movie name
        name_match = re.search(r'qb-movie-name">([^<]+)<', section)
        if not name_match:
            continue
        movie_name = name_match.group(1).strip()

        # Get genres
        genre_match = re.search(
            r'class="mr-sm"[^>]*>([^<]+)<\s*span', section
        )
        genres: list[str] = []
        if genre_match:
            genre_text = genre_match.group(1).strip()
            genres = [
                g.strip() for g in genre_text.split(",") if g.strip()
            ]

        # Get duration
        duration_match = re.search(r"(\d+)\s*min", section)
        if not duration_match:
            continue
        duration = int(duration_match.group(1))

        # Get screening times - look for time buttons
        times = re.findall(
            r'btn btn-primary btn-lg">\s*(\d{2}:\d{2})\s*<', section
        )
        if not times:
            # Try alternate pattern
            times = re.findall(
                r">\s*(\d{2}:\d{2})\s*\(HTTPS://", section
            )

        if times:
            start_times = list(dict.fromkeys(
                parse_time(t) for t in times
            ))
            movies.append(
                Movie(movie_name, start_times, duration, genres),
            )

    # Deduplicate movies (same movie might appear multiple times)
    seen: set[str] = set()
    unique_movies: list[Movie] = []
    for movie in movies:
        if movie.name not in seen:
            seen.add(movie.name)
            unique_movies.append(movie)

    return unique_movies, schedule_date


def parse_cinema_city_pdf(filepath: str) -> list[Movie]:
    """Parse Cinema City PDF schedule by extracting text."""
    if _pdfplumber is not None:
        with _pdfplumber.open(filepath) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        return parse_cinema_city_text(full_text)

    return _parse_cinema_city_pdf_basic(filepath)


def _parse_cinema_city_pdf_basic(filepath: str) -> list[Movie]:
    """Basic PDF parsing using PyMuPDF or falling back to subprocess."""
    if _fitz is not None:
        doc = _fitz.open(filepath)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
        return parse_cinema_city_text(full_text)

    pdftotext_path = shutil.which("pdftotext")
    if pdftotext_path is None:
        _exit_no_pdf_support()

    try:
        result = subprocess.run(
            [pdftotext_path, "-layout", filepath, "-"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        _exit_no_pdf_support()

    return parse_cinema_city_text(result.stdout)


def _exit_no_pdf_support() -> None:
    """Log PDF support error and exit."""
    logger.error(
        "Install pdfplumber, PyMuPDF, or poppler-utils for PDF support"
    )
    logger.error("  pip install pdfplumber")
    logger.error("  pip install pymupdf")
    logger.error("  pacman -S poppler")
    sys.exit(1)


def parse_cinema_city_text(text: str) -> list[Movie]:
    """Parse Cinema City schedule from extracted text."""
    movies: list[Movie] = []
    lines = text.split("\n")

    current_movie: str | None = None
    current_duration: int | None = None
    current_times: list[int] = []

    # Patterns for movie titles (all caps, usually)
    movie_title_pattern = re.compile(
        r"^([A-ZĄĆĘŁŃÓŚŹŻ][A-ZĄĆĘŁŃÓŚŹŻ0-9\s:,\.\-\!\?\(\)]+)$"
    )
    duration_pattern = re.compile(r"(\d+)\s*min")
    time_pattern = re.compile(r"\b(\d{1,2}:\d{2})\b")

    for i, raw_line in enumerate(lines):
        line = raw_line.strip()

        if (
            movie_title_pattern.match(line)
            and len(line) > _MIN_TITLE_LENGTH
        ):
            if current_movie and current_times:
                movies.append(Movie(
                    current_movie,
                    list(dict.fromkeys(current_times)),
                    current_duration or _DEFAULT_MOVIE_DURATION,
                ))

            current_movie = line.title()
            current_times = []
            current_duration = None

            # Look ahead for duration
            end = min(i + _TITLE_LOOKAHEAD_LINES, len(lines))
            for j in range(i + 1, end):
                dur_match = duration_pattern.search(lines[j])
                if dur_match:
                    current_duration = int(dur_match.group(1))
                    break

        if current_movie:
            times_in_line = time_pattern.findall(line)
            for t in times_in_line:
                parsed = _try_parse_time(t)
                if parsed is not None:
                    current_times.append(parsed)

    # Save last movie
    if current_movie and current_times:
        movies.append(Movie(
            current_movie,
            list(dict.fromkeys(current_times)),
            current_duration or _DEFAULT_MOVIE_DURATION,
        ))

    return movies


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
            elif (
                len(current_schedule) == best_count
                and best_count > 0
            ):
                all_best_schedules.append(current_schedule.copy())
            return

        # Pruning: can't beat the best
        remaining = len(movie_screenings) - movie_idx
        if len(current_schedule) + remaining < best_count:
            return

        # Try each screening of current movie
        for screening in movie_screenings[movie_idx]:
            conflicts = any(
                screening.overlaps(s, buffer)
                for s in current_schedule
            )
            if not conflicts:
                current_schedule.append(screening)
                _backtrack(movie_idx + 1, current_schedule)
                current_schedule.pop()

        # Also try skipping this movie
        _backtrack(movie_idx + 1, current_schedule)

    _backtrack(0, [])

    # Sort each schedule by start time and return
    return [
        sorted(schedule, key=lambda s: s.start)
        for schedule in all_best_schedules
    ]


def _format_single_schedule(
    schedule: list[Screening],
    output: TextIO,
) -> None:
    """Format a single schedule to the output stream."""
    for i, screening in enumerate(schedule, 1):
        duration = screening.end - screening.start
        hours, mins = divmod(duration, 60)
        actual_start = screening.start + ADS_DURATION
        actual_start_str = (
            f"{actual_start // 60:02d}:{actual_start % 60:02d}"
        )
        output.write(
            f"  {i}. {screening.start_str()} - "
            f"{screening.end_str()}  {screening.movie}\n"
        )
        output.write(
            f"     Duration: {hours}h {mins}m "
            f"(movie starts ~{actual_start_str})\n"
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
        f"  {num_movies} movies, "
        f"{num_schedules} possible combination(s)\n"
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
            f"  ... and {num_schedules - display_count} "
            "more combinations\n"
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
            f"{t // 60:02d}:{t % 60:02d}"
            for t in sorted(movie.start_times)
        )
        genre_str = (
            f" [{', '.join(movie.genres)}]" if movie.genres else ""
        )
        output.write(
            f"  {movie.name} ({movie.duration} min){genre_str}\n"
        )
        output.write(f"    Times: {times_str}\n")
    output.write("\n")


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the cinema planner."""
    parser = argparse.ArgumentParser(
        description=(
            "Plan your cinema day to watch "
            "as many movies as possible."
        ),
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
    parser.add_argument(
        "input_file", nargs="?", help="Input file (HTML/PDF/TXT)"
    )
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
        select_terms = [
            t.strip().lower() for t in args.select.split(",")
        ]
        movies = [
            m
            for m in movies
            if any(t in m.name.lower() for t in select_terms)
        ]
        logger.info(
            "Selected %d movies matching: %s",
            len(movies),
            args.select,
        )

    if args.exclude:
        exclude_terms = [
            t.strip().lower() for t in args.exclude.split(",")
        ]
        movies = [
            m
            for m in movies
            if not any(t in m.name.lower() for t in exclude_terms)
        ]
        logger.info("After name exclusion: %d movies", len(movies))

    excluded_genres: set[str] = set()
    if not args.all_genres:
        excluded_genres.update(DEFAULT_EXCLUDED_GENRES)
    if args.exclude_genre:
        excluded_genres.update(
            g.strip().lower() for g in args.exclude_genre.split(",")
        )

    if excluded_genres:
        before_count = len(movies)
        movies = [
            m
            for m in movies
            if not any(
                g.lower() in excluded_genres for g in m.genres
            )
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
        if any(
            must_watch_lower in screening.movie.lower()
            for screening in s
        )
    ]
    if filtered:
        logger.info(
            "Filtered to %d schedules containing '%s'",
            len(filtered),
            must_watch,
        )
        return filtered

    logger.warning(
        "No optimal schedules contain '%s'", must_watch
    )
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
            f.write(
                f"Generated: {schedule_date or 'unknown date'}\n"
            )
            f.write(f"Movies considered: {len(all_movie_names)}\n")
            f.write(f"Buffer time: {args.buffer} minutes\n")
            if excluded_genres:
                f.write(
                    "Excluded genres: "
                    f"{', '.join(sorted(excluded_genres))}\n"
                )
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

    logger.info(
        "\nOptimizing schedule for %d movies...", len(movies)
    )
    logger.info(
        "Buffer time between movies: %d minutes", args.buffer
    )

    schedules = find_best_schedule(movies, args.buffer)
    all_movie_names = [m.name for m in movies]

    if args.must_watch:
        schedules = _apply_must_watch_filter(
            schedules, args.must_watch
        )

    _output_schedules(
        schedules,
        all_movie_names,
        schedule_date,
        args,
        excluded_genres,
    )


if __name__ == "__main__":
    main()
