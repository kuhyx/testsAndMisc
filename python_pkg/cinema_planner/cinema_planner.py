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

import argparse
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
import re
import sys

# Default genres to exclude (can be overridden with --all-genres)
DEFAULT_EXCLUDED_GENRES = {"horror"}

# Ads duration before movie starts (Cinema City shows ~15 min of ads)
ADS_DURATION = 15


@dataclass
class Movie:
    name: str
    start_times: list[int]
    duration: int
    genres: list[str] = field(default_factory=list)


@dataclass
class Screening:
    movie: str
    start: int  # minutes from midnight
    end: int  # minutes from midnight

    def overlaps(self, other: "Screening", buffer: int = 0) -> bool:
        # Account for ADS_DURATION grace period - you can arrive late and still catch the movie
        # self ends, other starts: self.end vs other.start + ADS_DURATION (actual content start)
        # other ends, self starts: other.end vs self.start + ADS_DURATION
        return not (
            self.end + buffer <= other.start + ADS_DURATION
            or other.end + buffer <= self.start + ADS_DURATION
        )

    def start_str(self) -> str:
        return f"{self.start // 60:02d}:{self.start % 60:02d}"

    def end_str(self) -> str:
        return f"{self.end // 60:02d}:{self.end % 60:02d}"


def parse_time(time_str: str) -> int:
    """Parse time string like '18:20' to minutes from midnight."""
    time_str = time_str.strip().replace(".", ":")
    match = re.match(r"(\d{1,2}):(\d{2})", time_str)
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")
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

    raise ValueError(f"Invalid duration format: {duration_str}")


def parse_manual_line(line: str) -> Movie | None:
    """Parse a manual format line like 'Movie A, 18:20 or 20:50, 1h 46m'."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = line.split(",")
    if len(parts) < 3:
        raise ValueError(f"Invalid line format: {line}")

    movie = parts[0].strip()
    times_str = parts[1].strip()
    duration_str = ",".join(parts[2:]).strip()

    start_times = []
    for time_part in re.split(r"\s+or\s+", times_str, flags=re.IGNORECASE):
        start_times.append(parse_time(time_part))

    duration = parse_duration(duration_str)

    return Movie(movie, start_times, duration)


def extract_date_from_html(content: str) -> str | None:
    """Extract schedule date from Cinema City HTML."""
    # Look for date in YYYY-MM-DD format
    match = re.search(r"(202\d-\d{2}-\d{2})", content)
    if match:
        return match.group(1)
    return None


def parse_cinema_city_html(filepath: str) -> tuple[list[Movie], str | None]:
    """Parse Cinema City HTML schedule. Returns (movies, date)."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    movies = []
    schedule_date = extract_date_from_html(content)

    # Split content by movie sections
    sections = re.split(r'class="row movie-row', content)

    for section in sections[1:]:  # Skip first (before any movie)
        # Get movie name
        name_match = re.search(r'qb-movie-name">([^<]+)<', section)
        if not name_match:
            continue
        movie_name = name_match.group(1).strip()

        # Get genres - they appear before the duration, separated by commas
        # Pattern: class="mr-sm">Genre1, Genre2 <span
        genre_match = re.search(r'class="mr-sm"[^>]*>([^<]+)<\s*span', section)
        genres = []
        if genre_match:
            genre_text = genre_match.group(1).strip()
            genres = [g.strip() for g in genre_text.split(",") if g.strip()]

        # Get duration
        duration_match = re.search(r"(\d+)\s*min", section)
        if not duration_match:
            continue
        duration = int(duration_match.group(1))

        # Get screening times - look for time buttons
        times = re.findall(r'btn btn-primary btn-lg">\s*(\d{2}:\d{2})\s*<', section)
        if not times:
            # Try alternate pattern
            times = re.findall(r">\s*(\d{2}:\d{2})\s*\(HTTPS://", section)

        if times:
            start_times = [parse_time(t) for t in times]
            # Remove duplicates while preserving order
            start_times = list(dict.fromkeys(start_times))
            movies.append(Movie(movie_name, start_times, duration, genres))

    # Deduplicate movies (same movie might appear multiple times)
    seen = set()
    unique_movies = []
    for movie in movies:
        if movie.name not in seen:
            seen.add(movie.name)
            unique_movies.append(movie)

    return unique_movies, schedule_date


def parse_cinema_city_pdf(filepath: str) -> list[Movie]:
    """Parse Cinema City PDF schedule by extracting text."""
    try:
        import pdfplumber
    except ImportError:
        # Fallback to basic text extraction
        return parse_cinema_city_pdf_basic(filepath)

    with pdfplumber.open(filepath) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    return parse_cinema_city_text(full_text)


def parse_cinema_city_pdf_basic(filepath: str) -> list[Movie]:
    """Basic PDF parsing using PyMuPDF or falling back to subprocess."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(filepath)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
        return parse_cinema_city_text(full_text)
    except ImportError:
        pass

    # Try pdftotext command
    import subprocess

    try:
        result = subprocess.run(
            ["pdftotext", "-layout", filepath, "-"],
            capture_output=True,
            text=True,
            check=True,
        )
        return parse_cinema_city_text(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Install pdfplumber, PyMuPDF, or poppler-utils for PDF support")
        print("  pip install pdfplumber")
        print("  pip install pymupdf")
        print("  pacman -S poppler")
        sys.exit(1)


def parse_cinema_city_text(text: str) -> list[Movie]:
    """Parse Cinema City schedule from extracted text."""
    movies = []
    lines = text.split("\n")

    current_movie = None
    current_duration = None
    current_times: list[int] = []

    # Patterns for movie titles (all caps, usually)
    movie_title_pattern = re.compile(
        r"^([A-ZĄĆĘŁŃÓŚŹŻ][A-ZĄĆĘŁŃÓŚŹŻ0-9\s:,\.\-\!\?\(\)]+)$"
    )

    # Known movie indicators
    duration_pattern = re.compile(r"(\d+)\s*min")
    time_pattern = re.compile(r"\b(\d{1,2}:\d{2})\b")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check if this looks like a movie title
        # Cinema City format: MOVIE TITLE on its own line, followed by genre | duration
        if movie_title_pattern.match(line) and len(line) > 3:
            # Save previous movie if exists
            if current_movie and current_times:
                movies.append(
                    Movie(
                        current_movie,
                        list(dict.fromkeys(current_times)),
                        current_duration or 120,
                    )
                )

            # Check next lines for duration
            current_movie = line.title()  # Convert to title case
            current_times = []
            current_duration = None

            # Look ahead for duration
            for j in range(i + 1, min(i + 5, len(lines))):
                dur_match = duration_pattern.search(lines[j])
                if dur_match:
                    current_duration = int(dur_match.group(1))
                    break

        # Look for times in current line
        if current_movie:
            times_in_line = time_pattern.findall(line)
            for t in times_in_line:
                try:
                    current_times.append(parse_time(t))
                except ValueError:
                    pass

        i += 1

    # Save last movie
    if current_movie and current_times:
        movies.append(
            Movie(
                current_movie,
                list(dict.fromkeys(current_times)),
                current_duration or 120,
            )
        )

    return movies


def find_best_schedule(movies: list[Movie], buffer: int) -> list[list[Screening]]:
    """Find ALL schedules that maximize number of movies watched."""
    movie_screenings: list[list[Screening]] = []
    for movie in movies:
        # Schedule times are accurate - arrive at start, leave at start + duration
        # (ads are already factored into published times)
        screenings = [
            Screening(movie.name, start, start + movie.duration)
            for start in movie.start_times
        ]
        movie_screenings.append(screenings)

    best_count = 0
    all_best_schedules: list[list[Screening]] = []

    def backtrack(movie_idx: int, current_schedule: list[Screening]):
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
                backtrack(movie_idx + 1, current_schedule)
                current_schedule.pop()

        # Also try skipping this movie
        backtrack(movie_idx + 1, current_schedule)

    backtrack(0, [])

    # Sort each schedule by start time and return
    return [sorted(schedule, key=lambda s: s.start) for schedule in all_best_schedules]


def print_single_schedule(schedule: list[Screening], schedule_num: int | None = None):
    """Print a single schedule."""
    for i, screening in enumerate(schedule, 1):
        duration = screening.end - screening.start
        hours, mins = divmod(duration, 60)
        # Movie starts ~15 min after listed time due to ads
        actual_start = screening.start + ADS_DURATION
        actual_start_str = f"{actual_start // 60:02d}:{actual_start % 60:02d}"
        print(
            f"  {i}. {screening.start_str()} - {screening.end_str()}  {screening.movie}"
        )
        print(f"     Duration: {hours}h {mins}m (movie starts ~{actual_start_str})")
        if i < len(schedule):
            gap = schedule[i].start - screening.end
            if gap > 0:
                print(f"     [{gap} min break]")
        print()


def print_schedules(
    schedules: list[list[Screening]],
    all_movies: list[str],
    date: str | None = None,
    max_display: int = 5,
):
    """Print optimal schedules (up to max_display)."""
    if not schedules or not schedules[0]:
        print("No movies can be scheduled!")
        return

    num_movies = len(schedules[0])
    num_schedules = len(schedules)

    print(f"\n{'=' * 60}")
    if date:
        print(f"  OPTIMAL CINEMA SCHEDULES - {date}")
    else:
        print("  OPTIMAL CINEMA SCHEDULES")
    print(f"  {num_movies} movies, {num_schedules} possible combination(s)")
    print(f"{'=' * 60}\n")

    display_count = min(num_schedules, max_display)
    for idx, schedule in enumerate(schedules[:display_count], 1):
        if num_schedules > 1:
            print(f"{'─' * 60}")
            print(f"  OPTION {idx}:")
            print(f"{'─' * 60}\n")
        print_single_schedule(schedule)

    if num_schedules > display_count:
        print(f"{'─' * 60}")
        print(f"  ... and {num_schedules - display_count} more combinations")
        print("  (use -n to show more, e.g., -n 10)")
        print()

    # Show skipped movies (from first schedule as reference)
    scheduled_movies = {s.movie for s in schedules[0]}
    skipped = [m for m in all_movies if m not in scheduled_movies]
    if skipped and num_schedules == 1:
        print(f"{'─' * 60}")
        print(f"  Skipped movies ({len(skipped)}):")
        for movie in skipped:
            print(f"    - {movie}")
        print()


def print_all_movies(movies: list[Movie], date: str | None = None):
    """Print all parsed movies."""
    print(f"\n{'─' * 60}")
    if date:
        print(f"  Parsed {len(movies)} movies for {date}:")
    else:
        print(f"  Parsed {len(movies)} movies:")
    print(f"{'─' * 60}")
    for movie in movies:
        times_str = ", ".join(
            f"{t//60:02d}:{t%60:02d}" for t in sorted(movie.start_times)
        )
        genre_str = f" [{', '.join(movie.genres)}]" if movie.genres else ""
        print(f"  {movie.name} ({movie.duration} min){genre_str}")
        print(f"    Times: {times_str}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Plan your cinema day to watch as many movies as possible.",
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
        help="Comma-separated list of movie names to include (partial match)",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        type=str,
        help="Comma-separated list of movie names to exclude (partial match)",
    )
    parser.add_argument(
        "-g",
        "--exclude-genre",
        type=str,
        help="Comma-separated list of genres to exclude (e.g., 'Horror,Thriller')",
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
        help="Maximum number of schedule options to display (default: 5)",
    )
    parser.add_argument(
        "-m",
        "--must-watch",
        type=str,
        help="Only show schedules containing this movie (partial match)",
    )

    args = parser.parse_args()

    movies = []
    schedule_date = None

    if args.interactive:
        print("Enter movies (empty line to finish):")
        print("Format: Title, start1 [or start2 ...], duration")
        print("Example: Inception, 10:30 or 14:00, 2h 28m")
        print()
        while True:
            try:
                line = input("> ")
            except EOFError:
                break
            if not line.strip():
                break
            try:
                result = parse_manual_line(line)
                if result:
                    movies.append(result)
                    print(f"  Added: {result.name}")
            except ValueError as e:
                print(f"  Error: {e}")
    elif args.input_file:
        filepath = Path(args.input_file)
        suffix = filepath.suffix.lower()

        print(f"Parsing: {filepath}")

        if suffix == ".html" or suffix == ".htm":
            movies, schedule_date = parse_cinema_city_html(str(filepath))
        elif suffix == ".pdf":
            movies = parse_cinema_city_pdf(str(filepath))
        else:
            # Assume manual format
            with open(filepath) as f:
                for line in f:
                    try:
                        result = parse_manual_line(line)
                        if result:
                            movies.append(result)
                    except ValueError as e:
                        print(f"Warning: {e}", file=sys.stderr)
    else:
        print("Enter movies (Ctrl+D when done):")
        for line in sys.stdin:
            try:
                result = parse_manual_line(line)
                if result:
                    movies.append(result)
            except ValueError as e:
                print(f"Warning: {e}", file=sys.stderr)

    if not movies:
        print("No movies found!")
        sys.exit(1)

    # Filter movies if requested
    if args.select:
        select_terms = [t.strip().lower() for t in args.select.split(",")]
        movies = [m for m in movies if any(t in m.name.lower() for t in select_terms)]
        print(f"Selected {len(movies)} movies matching: {args.select}")

    if args.exclude:
        exclude_terms = [t.strip().lower() for t in args.exclude.split(",")]
        movies = [
            m for m in movies if not any(t in m.name.lower() for t in exclude_terms)
        ]
        print(f"After name exclusion: {len(movies)} movies")

    # Genre filtering
    excluded_genres = set()
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
            print(
                f"Excluded {filtered_count} movies by genre: {', '.join(sorted(excluded_genres))}"
            )

    if args.list:
        print_all_movies(movies, schedule_date)
        return

    print(f"\nOptimizing schedule for {len(movies)} movies...")
    print(f"Buffer time between movies: {args.buffer} minutes")

    schedules = find_best_schedule(movies, args.buffer)
    all_movie_names = [m.name for m in movies]

    # Filter schedules if must-watch movie specified
    if args.must_watch:
        must_watch_lower = args.must_watch.lower()
        filtered = [
            s
            for s in schedules
            if any(must_watch_lower in screening.movie.lower() for screening in s)
        ]
        if filtered:
            print(
                f"Filtered to {len(filtered)} schedules containing '{args.must_watch}'"
            )
            schedules = filtered
        else:
            print(f"Warning: No optimal schedules contain '{args.must_watch}'")
            print("Showing all schedules instead.")

    # Capture output if saving to file
    output_buffer = StringIO()
    with redirect_stdout(output_buffer):
        print_schedules(schedules, all_movie_names, schedule_date, args.max_schedules)

    schedule_output = output_buffer.getvalue()
    print(schedule_output)  # Still show in terminal

    # Save to file
    if args.output or schedule_date:
        if args.output:
            output_file = Path(args.output)
        else:
            output_file = Path(f"cinema_plan_{schedule_date}.txt")

        with open(output_file, "w") as f:
            f.write(f"Generated: {schedule_date or 'unknown date'}\n")
            f.write(f"Movies considered: {len(movies)}\n")
            f.write(f"Buffer time: {args.buffer} minutes\n")
            if excluded_genres:
                f.write(f"Excluded genres: {', '.join(sorted(excluded_genres))}\n")
            f.write(schedule_output)
        print(f"Schedule saved to: {output_file}")


if __name__ == "__main__":
    main()
