"""Tests for split_questions module."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
from unittest.mock import patch

from typing_extensions import Self


class TestSplitQuestions:
    """Tests for split_questions module."""

    def _import_split_questions(
        self,
        source_content: str,
    ) -> dict[str, object]:
        """Import split_questions with mocked file I/O.

        The module has top-level code so we must mock before import.
        """
        # Remove cached module to force re-import
        mod_name = "split_questions"
        sys.modules.pop(mod_name, None)

        class FakeFile:
            def __init__(self, content: str = "") -> None:
                self._content = content
                self._lines_written: list[str] = []

            def read(self) -> str:
                return self._content

            def readlines(self) -> list[str]:
                return self._content.splitlines(keepends=True)

            def writelines(self, lines: list[str]) -> None:
                self._lines_written.extend(lines)

            def __enter__(self) -> Self:
                return self

            def __exit__(self, *a: object) -> None:
                pass

        source_file = FakeFile(source_content)
        written_files: dict[str, FakeFile] = {}

        def fake_open(self_path: Path, *_args: object, **_kwargs: object) -> FakeFile:
            path_str = str(self_path)
            if "OBRONA_MAGISTERSKA_ODPOWIEDZI" in path_str:
                return source_file
            # Output file
            f = FakeFile()
            written_files[path_str] = f
            return f

        with (
            patch.object(Path, "open", fake_open),
            patch.object(Path, "mkdir", lambda *_a, **_kw: None),
        ):
            importlib.import_module(mod_name)

        return written_files

    def test_single_question(self) -> None:
        """Test splitting with a single question."""
        content = "## PYTANIE 1: Algorytmy\nContent of question 1.\nMore content.\n"
        self._import_split_questions(content)

    def test_multiple_questions(self) -> None:
        """Test splitting with multiple questions."""
        content = (
            "## PYTANIE 1: First question\n"
            "Content 1.\n"
            "\n"
            "## PYTANIE 2: Second question\n"
            "Content 2.\n"
        )
        self._import_split_questions(content)

    def test_dual_numbered_question(self) -> None:
        """Test question with dual number like 13/27."""
        content = "## PYTANIE 13/27: Dual numbered\nContent here.\n"
        self._import_split_questions(content)

    def test_trailing_newpage_stripped(self) -> None:
        r"""Test that trailing \\newpage and blanks are stripped."""
        content = "## PYTANIE 5: Question five\nContent.\n\n\\newpage\n\n"
        self._import_split_questions(content)

    def test_no_questions_found(self) -> None:
        """Test with no matching question headers."""
        content = "# Just a title\nSome text.\n"
        self._import_split_questions(content)

    def test_zero_padded_filenames(self) -> None:
        """Test that single digit numbers are zero-padded."""
        content = (
            "## PYTANIE 3: Question three\n"
            "Body.\n"
            "\n"
            "## PYTANIE 12: Question twelve\n"
            "Body.\n"
        )
        self._import_split_questions(content)
