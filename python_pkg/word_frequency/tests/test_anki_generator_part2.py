"""Tests for anki_generator missing lines 151-199, 394, 411-431."""

from __future__ import annotations

import argparse
import logging
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from python_pkg.word_frequency.anki_generator import (
    _handle_inverse_mode,
    _run_generation,
    main,
)

if TYPE_CHECKING:
    from pathlib import Path

_MOD = "python_pkg.word_frequency.anki_generator"


class TestHandleInverseMode:
    """Tests for _handle_inverse_mode (lines 151-199)."""

    def _make_args(
        self,
        tmp_path: Path,
        *,
        quiet: bool = False,
        output: str | None = None,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            quiet=quiet,
            max_vocab=50,
            output=output or str(tmp_path / "out.txt"),
            source_lang="en",
            target_lang="es",
            deck_name=None,
            include_context=False,
            no_translate=True,
            force=False,
        )

    def test_verbose_mode(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cover verbose (non-quiet) output lines."""
        fp = tmp_path / "source.txt"
        fp.write_text("hello world", encoding="utf-8")
        args = self._make_args(tmp_path)
        with (
            caplog.at_level(logging.INFO),
            patch(
                f"{_MOD}.generate_flashcards_inverse",
                return_value=("content", "hello world", 2, 3, 5),
            ),
        ):
            result = _handle_inverse_mode(args, fp)
        assert result == 0
        assert "INVERSE MODE" in caplog.text
        assert "top 50" in caplog.text
        assert "Rarest word" in caplog.text
        assert "Flashcards: 3" in caplog.text

    def test_quiet_mode(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Cover quiet mode path."""
        fp = tmp_path / "source.txt"
        fp.write_text("hello", encoding="utf-8")
        args = self._make_args(tmp_path, quiet=True)
        with (
            caplog.at_level(logging.INFO),
            patch(
                f"{_MOD}.generate_flashcards_inverse",
                return_value=("content", "hello", 1, 1, 1),
            ),
        ):
            result = _handle_inverse_mode(args, fp)
        assert result == 0
        assert "INVERSE MODE" not in caplog.text

    def test_default_output_path(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cover auto-generated output path when args.output is None."""
        fp = tmp_path / "source.txt"
        fp.write_text("hello", encoding="utf-8")
        args = self._make_args(tmp_path, quiet=True)
        args.output = None
        with (
            caplog.at_level(logging.INFO),
            patch(
                f"{_MOD}.generate_flashcards_inverse",
                return_value=("content", "hello", 1, 1, 1),
            ),
        ):
            result = _handle_inverse_mode(args, fp)
        assert result == 0
        expected = tmp_path / "source_anki_top50.txt"
        assert expected.exists()


class TestRunGeneration:
    """Tests for _run_generation (line 394: file not found)."""

    def test_file_not_found(self, caplog: pytest.LogCaptureFixture) -> None:
        """Cover filepath.exists() returning False."""
        args = argparse.Namespace(
            file="/nonexistent/path/file.txt",
            max_vocab=None,
            length=10,
        )
        with caplog.at_level(logging.ERROR):
            result = _run_generation(args)
        assert result == 1
        assert "File not found" in caplog.text

    def test_dispatches_to_inverse(self, tmp_path: Path) -> None:
        """Cover max_vocab branch dispatch."""
        fp = tmp_path / "f.txt"
        fp.write_text("hello", encoding="utf-8")
        args = argparse.Namespace(
            file=str(fp),
            max_vocab=10,
            length=None,
        )
        with patch(f"{_MOD}._handle_inverse_mode", return_value=0) as mock:
            result = _run_generation(args)
        assert result == 0
        mock.assert_called_once()


class TestMainErrorHandling:
    """Tests for main() exception handling (lines 411-431)."""

    def test_file_not_found_exception(self) -> None:
        """Cover FileNotFoundError exception handler."""
        with patch(
            f"{_MOD}._run_generation",
            side_effect=FileNotFoundError("gone"),
        ):
            result = main(["--file", "x.txt", "--length", "10"])
        assert result == 1

    def test_called_process_error(self) -> None:
        """Cover CalledProcessError exception handler."""
        with patch(
            f"{_MOD}._run_generation",
            side_effect=subprocess.CalledProcessError(1, "cmd"),
        ):
            result = main(["--file", "x.txt", "--length", "10"])
        assert result == 1

    def test_value_error(self) -> None:
        """Cover ValueError exception handler."""
        with patch(
            f"{_MOD}._run_generation",
            side_effect=ValueError("bad value"),
        ):
            result = main(["--file", "x.txt", "--length", "10"])
        assert result == 1

    def test_no_file_required_error(self) -> None:
        """Cover parser.error for missing --file."""
        with pytest.raises(SystemExit):
            main(["--length", "10"])

    def test_missing_length_and_vocab(self) -> None:
        """Cover parser.error for neither --length nor --max-vocab."""
        with pytest.raises(SystemExit):
            main(["--file", "x.txt"])

    def test_both_length_and_vocab_error(self) -> None:
        """Cover parser.error for both --length and --max-vocab."""
        with pytest.raises(SystemExit):
            main(["--file", "x.txt", "--length", "10", "--max-vocab", "5"])

    def test_cache_stats_flag(self) -> None:
        """Cover --cache-stats early return."""
        with patch(f"{_MOD}._print_cache_stats", return_value=0) as mock:
            result = main(["--cache-stats"])
        assert result == 0
        mock.assert_called_once()

    def test_clear_cache_flag(self) -> None:
        """Cover --clear-cache early return."""
        with patch(f"{_MOD}._clear_caches", return_value=0) as mock:
            result = main(["--clear-cache"])
        assert result == 0
        mock.assert_called_once()
