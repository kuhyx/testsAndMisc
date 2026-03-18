"""Parsing functions for Cinema City schedules and manual input."""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
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

# Constants for validation and parsing
_MIN_MANUAL_LINE_PARTS = 3
_MIN_TITLE_LENGTH = 3
_DEFAULT_MOVIE_DURATION = 120
_TITLE_LOOKAHEAD_LINES = 5


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
        genre_match = re.search(r'class="mr-sm"[^>]*>([^<]+)<\s*span', section)
        genres: list[str] = []
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
            start_times = list(dict.fromkeys(parse_time(t) for t in times))
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
    logger.error("Install pdfplumber, PyMuPDF, or poppler-utils for PDF support")
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

        if movie_title_pattern.match(line) and len(line) > _MIN_TITLE_LENGTH:
            if current_movie and current_times:
                movies.append(
                    Movie(
                        current_movie,
                        list(dict.fromkeys(current_times)),
                        current_duration or _DEFAULT_MOVIE_DURATION,
                    )
                )

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
        movies.append(
            Movie(
                current_movie,
                list(dict.fromkeys(current_times)),
                current_duration or _DEFAULT_MOVIE_DURATION,
            )
        )

    return movies
