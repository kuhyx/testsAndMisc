#!/usr/bin/env python3
"""Command-line dispatch for transcribe.sh's Python helpers.

transcribe.sh branches on the exit status, so the codes are the contract:
7 means faster_whisper is missing, 2 means a required argument is missing,
and 1 means the requested operation failed.
"""

from __future__ import annotations

import argparse
import logging
import sys

from _transcribe_probes import (
    check_ctranslate2,
    check_diarization_deps,
    check_faster_whisper,
    generate_sine_wav,
    get_python_version,
    prepare_model,
    print_deps_installed,
    test_cuda,
)

logger = logging.getLogger(__name__)


def _handle_python_version() -> None:
    """Handle python-version command."""
    logger.info("%s", get_python_version())


def _handle_check_faster_whisper() -> None:
    """Handle check-faster-whisper command."""
    if not check_faster_whisper():
        logger.error(
            "Python dependency 'faster_whisper' not found in "
            "offline mode. Run with --online to install.",
        )
        sys.exit(7)


def _handle_check_diarization() -> None:
    """Handle check-diarization command."""
    check_diarization_deps()


def _handle_check_ctranslate2() -> None:
    """Handle check-ctranslate2 command."""
    if not check_ctranslate2():
        sys.exit(1)


def _handle_deps_installed() -> None:
    """Handle deps-installed command."""
    print_deps_installed()


def _handle_generate_wav(args: argparse.Namespace) -> None:
    """Handle generate-wav command."""
    if not args.file:
        logger.error("--file is required for generate-wav")
        sys.exit(2)
    if not generate_sine_wav(args.file):
        sys.exit(1)


def _handle_prepare_model(args: argparse.Namespace) -> None:
    """Handle prepare-model command."""
    if not args.model or not args.model_dir:
        logger.error(
            "--model and --model-dir are required for prepare-model",
        )
        sys.exit(2)
    if not prepare_model(args.model, args.model_dir):
        sys.exit(1)


def _handle_test_cuda() -> None:
    """Handle test-cuda command."""
    if not test_cuda():
        sys.exit(1)


def main() -> None:
    """Parse arguments and dispatch helper commands."""
    logging.basicConfig(format="%(message)s", level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Helper utilities for transcribe.sh",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  python-version       Print Python major.minor version
  check-faster-whisper Check if faster_whisper is installed
  check-diarization    Check diarization deps (warn if missing)
  check-ctranslate2    Check if ctranslate2 is installed
  deps-installed       Print deps installed confirmation
  generate-wav FILE    Generate a 3s 1kHz sine wave WAV
  prepare-model        Download model for offline use
  test-cuda            Test CUDA initialization
""",
    )
    parser.add_argument(
        "command",
        choices=[
            "python-version",
            "check-faster-whisper",
            "check-diarization",
            "check-ctranslate2",
            "deps-installed",
            "generate-wav",
            "prepare-model",
            "test-cuda",
        ],
        help="Command to run",
    )
    parser.add_argument("--file", help="Output file path (for generate-wav)")
    parser.add_argument("--model", help="Model name (for prepare-model)")
    parser.add_argument("--model-dir", help="Model directory (for prepare-model)")

    args = parser.parse_args()

    dispatch: dict[str, object] = {
        "python-version": _handle_python_version,
        "check-faster-whisper": _handle_check_faster_whisper,
        "check-diarization": _handle_check_diarization,
        "check-ctranslate2": _handle_check_ctranslate2,
        "deps-installed": _handle_deps_installed,
        "generate-wav": lambda: _handle_generate_wav(args),
        "prepare-model": lambda: _handle_prepare_model(args),
        "test-cuda": _handle_test_cuda,
    }

    handler = dispatch.get(args.command)
    if handler is not None and callable(handler):
        handler()


if __name__ == "__main__":
    main()
