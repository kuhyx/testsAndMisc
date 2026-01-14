#!/usr/bin/env python3
"""Anki flashcard generator for HTTP status codes with cat images.

Downloads cat images from https://http.cat/ for each HTTP status code
and creates an Anki deck with bidirectional flashcards for memorization.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
from pathlib import Path
import sys
from typing import TYPE_CHECKING

import genanki
import requests

if TYPE_CHECKING:
    from collections.abc import Sequence

_logger = logging.getLogger(__name__)

# Constants
REQUEST_TIMEOUT = 30  # seconds
CACHE_DIR = Path(__file__).parent / "http_cat_cache"

# Comprehensive HTTP status codes available on http.cat
# Data from: https://http.cat/
HTTP_STATUS_CODES = {
    # 1xx Informational
    100: "Continue",
    101: "Switching Protocols",
    102: "Processing",
    103: "Early Hints",
    # 2xx Success
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    207: "Multi-Status",
    208: "Already Reported",
    226: "IM Used",
    # 3xx Redirection
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    # 4xx Client Error
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Payload Too Large",
    414: "URI Too Long",
    415: "Unsupported Media Type",
    416: "Range Not Satisfiable",
    417: "Expectation Failed",
    418: "I'm a teapot",
    420: "Enhance Your Calm",
    421: "Misdirected Request",
    422: "Unprocessable Entity",
    423: "Locked",
    424: "Failed Dependency",
    425: "Too Early",
    426: "Upgrade Required",
    428: "Precondition Required",
    429: "Too Many Requests",
    431: "Request Header Fields Too Large",
    444: "No Response",
    450: "Blocked by Windows Parental Controls",
    451: "Unavailable For Legal Reasons",
    497: "HTTP Request Sent to HTTPS Port",
    498: "Token Expired/Invalid",
    499: "Client Closed Request",
    # 5xx Server Error
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported",
    506: "Variant Also Negotiates",
    507: "Insufficient Storage",
    508: "Loop Detected",
    509: "Bandwidth Limit Exceeded",
    510: "Not Extended",
    511: "Network Authentication Required",
    521: "Web Server Is Down",
    522: "Connection Timed Out",
    523: "Origin Is Unreachable",
    524: "A Timeout Occurred",
    525: "SSL Handshake Failed",
    526: "Invalid SSL Certificate",
    527: "Railgun Error",
    529: "Site is overloaded",
    530: "Site is frozen",
    599: "Network Connect Timeout Error",
}


def _download_cat_image(status_code: int) -> bytes:
    """Download a cat image for the given HTTP status code.

    Args:
        status_code: HTTP status code to download image for.

    Returns:
        Image bytes.

    Raises:
        requests.exceptions.RequestException: If download fails.
    """
    url = f"https://http.cat/{status_code}.jpg"
    _logger.info("Downloading %s", url)
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.content


def _get_cached_image_path(status_code: int) -> Path:
    """Get the cache file path for a status code image.

    Args:
        status_code: HTTP status code.

    Returns:
        Path to cached image file.
    """
    return CACHE_DIR / f"{status_code}.jpg"


def get_or_download_image(status_code: int, *, use_cache: bool = True) -> bytes:
    """Get cat image for status code, using cache if available.

    Args:
        status_code: HTTP status code.
        use_cache: Whether to use cached images if available.

    Returns:
        Image bytes.

    Raises:
        requests.exceptions.RequestException: If download fails.
    """
    cache_path = _get_cached_image_path(status_code)

    # Check cache first
    if use_cache and cache_path.exists():
        _logger.info("Using cached image for %d", status_code)
        return cache_path.read_bytes()

    # Download and cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    image_data = _download_cat_image(status_code)
    cache_path.write_bytes(image_data)
    _logger.info("Cached image for %d at %s", status_code, cache_path)

    return image_data


def generate_anki_package(
    status_codes: dict[int, str],
    deck_name: str = "HTTP Status Codes",
    *,
    use_cache: bool = True,
) -> genanki.Package:
    """Generate Anki package for HTTP status codes with cat images.

    Creates bidirectional flashcards:
    - Code -> Image + Description
    - Description -> Code

    Args:
        status_codes: Dictionary mapping status codes to descriptions.
        deck_name: Name for the Anki deck.
        use_cache: Whether to use cached images.

    Returns:
        Generated Anki package.
    """
    # Generate stable model IDs from deck name
    model_id_hash = hashlib.md5(
        f"http_status_{deck_name}".encode(), usedforsecurity=False
    )
    model_id_code_to_desc = int(model_id_hash.hexdigest()[:8], 16)

    # Different model ID for reverse direction
    reverse_hash = hashlib.md5(
        f"http_status_reverse_{deck_name}".encode(), usedforsecurity=False
    )
    model_id_desc_to_code = int(reverse_hash.hexdigest()[:8], 16)

    card_css = """
.card {
    font-family: Arial, sans-serif;
    font-size: 24px;
    text-align: center;
    color: #333;
    background-color: #fff;
}
.card.night_mode {
    color: #eee;
    background-color: #2f2f2f;
}
.status-code {
    font-size: 48px;
    font-weight: bold;
    margin: 20px;
    color: #2C3E50;
}
.card.night_mode .status-code {
    color: #ECF0F1;
}
.description {
    font-size: 32px;
    margin: 20px;
    color: #34495E;
}
.card.night_mode .description {
    color: #BDC3C7;
}
.image-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 60vh;
    margin: 20px;
}
.image-container img {
    max-width: 90%;
    max-height: 60vh;
    object-fit: contain;
    border-radius: 10px;
}
"""

    # Model 1: Status Code -> Image + Description
    model_code_to_desc = genanki.Model(
        model_id_code_to_desc,
        "HTTP Status Code to Description",
        fields=[
            {"name": "StatusCode"},
            {"name": "Description"},
            {"name": "Image"},
        ],
        templates=[
            {
                "name": "Code to Description",
                "qfmt": '<div class="status-code">{{StatusCode}}</div>',
                "afmt": '<div class="status-code">{{StatusCode}}</div>'
                '<hr id="answer">'
                '<div class="description">{{Description}}</div>'
                '<div class="image-container">{{Image}}</div>',
            },
        ],
        css=card_css,
    )

    # Model 2: Description -> Status Code
    model_desc_to_code = genanki.Model(
        model_id_desc_to_code,
        "HTTP Status Description to Code",
        fields=[
            {"name": "StatusCode"},
            {"name": "Description"},
            {"name": "Image"},
        ],
        templates=[
            {
                "name": "Description to Code",
                "qfmt": '<div class="description">{{Description}}</div>'
                '<div class="image-container">{{Image}}</div>',
                "afmt": '<div class="description">{{Description}}</div>'
                '<div class="image-container">{{Image}}</div>'
                '<hr id="answer">'
                '<div class="status-code">{{StatusCode}}</div>',
            },
        ],
        css=card_css,
    )

    # Use MD5 hash of deck name for stable deck ID
    deck_id_hash = hashlib.md5(deck_name.encode(), usedforsecurity=False)
    deck_id = int(deck_id_hash.hexdigest()[:8], 16)

    my_deck = genanki.Deck(deck_id, deck_name)
    media_files = []

    for status_code, description in status_codes.items():
        try:
            image_data = get_or_download_image(status_code, use_cache=use_cache)
            filename = f"http_cat_{status_code}.jpg"

            # Save to temp directory for genanki
            temp_path = Path(f"/tmp/{filename}")  # noqa: S108
            temp_path.write_bytes(image_data)
            media_files.append(str(temp_path))

            image_html = f'<img src="{filename}">'

            # Add card: Code -> Description + Image
            note_code_to_desc = genanki.Note(
                model=model_code_to_desc,
                fields=[str(status_code), description, image_html],
                tags=["http", "status-codes", "programming"],
            )
            my_deck.add_note(note_code_to_desc)

            # Add card: Description + Image -> Code
            note_desc_to_code = genanki.Note(
                model=model_desc_to_code,
                fields=[str(status_code), description, image_html],
                tags=["http", "status-codes", "programming"],
            )
            my_deck.add_note(note_desc_to_code)

            _logger.info("Added cards for status code %d", status_code)

        except requests.exceptions.RequestException:
            _logger.exception(
                "Failed to download image for status code %d", status_code
            )

    package = genanki.Package(my_deck)
    package.media_files = media_files
    return package


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command-line arguments.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Generate Anki flashcards for HTTP status codes with cat images.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: http_status_codes.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="HTTP Status Codes",
        help="Name for the Anki deck",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Download images even if cached versions exist",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args(argv)
    output_path = Path(args.output) if args.output else Path("http_status_codes.apkg")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    try:
        sys.stdout.write("Generating HTTP status code flashcards...\n")
        sys.stdout.write(f"Total status codes: {len(HTTP_STATUS_CODES)}\n")
        sys.stdout.write(f"Cache directory: {CACHE_DIR}\n")
        sys.stdout.write(f"Using cache: {not args.no_cache}\n\n")

        package = generate_anki_package(
            HTTP_STATUS_CODES,
            args.deck_name,
            use_cache=not args.no_cache,
        )
        package.write_to_file(str(output_path))

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Total cards: {len(HTTP_STATUS_CODES) * 2} ")
        sys.stdout.write("(bidirectional)\n")
        sys.stdout.write(f"Output file: {output_path.absolute()}\n")
        sys.stdout.write(f"Cache location: {CACHE_DIR.absolute()}\n")
        sys.stdout.write("\nImport the .apkg file into Anki to start learning!\n")

    except (OSError, ValueError, RuntimeError) as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
