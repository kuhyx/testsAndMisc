"""Tests for python_pkg.repo_explorer._discovery."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from unittest.mock import MagicMock, patch

from python_pkg.repo_explorer._discovery import (
    IGNORED_DIRS,
    _desc_from_run_sh,
    _find_terminal,
    _is_ignored,
    _strip_ansi,
    find_projects,
    get_description,
)

# ── _strip_ansi ──────────────────────────────────────────────────────


class TestStripAnsi:
    def test_removes_colour_codes(self) -> None:
        assert _strip_ansi("\x1b[31mred\x1b[0m") == "red"

    def test_no_ansi(self) -> None:
        assert _strip_ansi("plain text") == "plain text"

    def test_empty_string(self) -> None:
        assert _strip_ansi("") == ""

    def test_complex_ansi(self) -> None:
        assert _strip_ansi("\x1b[1;32mgreen\x1b[0m rest") == "green rest"


# ── _find_terminal ───────────────────────────────────────────────────


class TestFindTerminal:
    @patch("python_pkg.repo_explorer._discovery.shutil.which")
    def test_first_candidate_found(self, mock_which: MagicMock) -> None:
        mock_which.return_value = "/usr/bin/kitty"
        result = _find_terminal()
        assert result == ["kitty", "--"]

    @patch("python_pkg.repo_explorer._discovery.shutil.which")
    def test_later_candidate_found(self, mock_which: MagicMock) -> None:
        def side_effect(exe: str) -> str | None:
            return "/usr/bin/xterm" if exe == "xterm" else None

        mock_which.side_effect = side_effect
        result = _find_terminal()
        assert result == ["xterm", "-e"]

    @patch("python_pkg.repo_explorer._discovery.shutil.which")
    def test_none_found(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None
        result = _find_terminal()
        assert result == []


# ── _is_ignored ──────────────────────────────────────────────────────


class TestIsIgnored:
    def test_ignored_dir(self) -> None:
        assert _is_ignored(Path("project/.git/config"))

    def test_not_ignored(self) -> None:
        assert not _is_ignored(Path("project/src/main.py"))

    def test_ignored_pycache(self) -> None:
        assert _is_ignored(Path("a/__pycache__/b.pyc"))

    def test_all_ignored_dirs_recognized(self) -> None:
        for d in IGNORED_DIRS:
            assert _is_ignored(Path(d) / "file.txt")


# ── find_projects ────────────────────────────────────────────────────


class TestFindProjects:
    @patch("python_pkg.repo_explorer._discovery._is_ignored")
    def test_finds_run_sh(self, mock_ignored: MagicMock) -> None:
        mock_ignored.return_value = False
        root = MagicMock(spec=Path)
        run1 = MagicMock(spec=Path)
        proj1 = MagicMock(spec=Path)
        run1.parent = proj1
        proj1.name = "proj1"
        proj1.relative_to.return_value = PurePosixPath("sub/proj1")
        root.rglob.return_value = [run1]
        result = find_projects(root)
        assert len(result) == 1
        assert result[0]["path"] is proj1
        assert result[0]["name"] == "proj1"

    @patch("python_pkg.repo_explorer._discovery._is_ignored")
    def test_filters_ignored(self, mock_ignored: MagicMock) -> None:
        mock_ignored.return_value = True
        root = MagicMock(spec=Path)
        run1 = MagicMock(spec=Path)
        root.rglob.return_value = [run1]
        result = find_projects(root)
        assert result == []

    def test_empty_root(self) -> None:
        root = MagicMock(spec=Path)
        root.rglob.return_value = []
        result = find_projects(root)
        assert result == []


# ── _desc_from_run_sh ────────────────────────────────────────────────


class TestDescFromRunSh:
    def test_with_shebang_and_comments(self) -> None:
        run_sh = MagicMock(spec=Path)
        run_sh.read_text.return_value = (
            "#!/bin/bash\n# First line\n# Second line\necho hi"
        )
        result = _desc_from_run_sh(run_sh)
        assert result == "First line Second line"

    def test_only_shebang(self) -> None:
        run_sh = MagicMock(spec=Path)
        run_sh.read_text.return_value = "#!/bin/bash\necho hi"
        result = _desc_from_run_sh(run_sh)
        assert result == ""

    def test_comments_only(self) -> None:
        run_sh = MagicMock(spec=Path)
        run_sh.read_text.return_value = "# Just a comment\n# Another one"
        result = _desc_from_run_sh(run_sh)
        assert result == "Just a comment Another one"

    def test_empty_file(self) -> None:
        run_sh = MagicMock(spec=Path)
        run_sh.read_text.return_value = ""
        result = _desc_from_run_sh(run_sh)
        assert result == ""

    def test_truncates_at_300(self) -> None:
        run_sh = MagicMock(spec=Path)
        long_comment = "# " + "x" * 400
        run_sh.read_text.return_value = long_comment
        result = _desc_from_run_sh(run_sh)
        assert len(result) == 300

    def test_non_comment_line_without_prior_comments(self) -> None:
        """Non-comment before comments: comments still collected."""
        run_sh = MagicMock(spec=Path)
        run_sh.read_text.return_value = "echo hello\n# comment after code"
        result = _desc_from_run_sh(run_sh)
        assert result == "comment after code"

    def test_break_on_non_comment_after_comments(self) -> None:
        run_sh = MagicMock(spec=Path)
        run_sh.read_text.return_value = "# first\ncode\n# ignored"
        result = _desc_from_run_sh(run_sh)
        assert result == "first"


# ── get_description ──────────────────────────────────────────────────


class TestGetDescription:
    def test_readme_md_with_heading(self) -> None:
        mock_path = MagicMock(spec=Path)
        readme = MagicMock(spec=Path)
        readme.exists.return_value = True
        readme.read_text.return_value = "# My Project\nDetails here"

        def truediv(_self: object, name: str) -> MagicMock:
            if name == "README.md":
                return readme
            m = MagicMock(spec=Path)
            m.exists.return_value = False
            return m

        mock_path.__truediv__ = truediv
        result = get_description(mock_path)
        assert result == "My Project"

    def test_readme_txt(self) -> None:
        mock_path = MagicMock(spec=Path)

        def truediv(_self: object, name: str) -> MagicMock:
            m = MagicMock(spec=Path)
            if name == "README.txt":
                m.exists.return_value = True
                m.read_text.return_value = "Text readme content"
            else:
                m.exists.return_value = False
            return m

        mock_path.__truediv__ = truediv
        result = get_description(mock_path)
        assert result == "Text readme content"

    def test_readme_lower(self) -> None:
        mock_path = MagicMock(spec=Path)

        def truediv(_self: object, name: str) -> MagicMock:
            m = MagicMock(spec=Path)
            if name == "readme.md":
                m.exists.return_value = True
                m.read_text.return_value = "## Lower readme"
            else:
                m.exists.return_value = False
            return m

        mock_path.__truediv__ = truediv
        result = get_description(mock_path)
        assert result == "Lower readme"

    def test_readme_all_empty_lines(self) -> None:
        """README exists but all lines strip to empty."""
        mock_path = MagicMock(spec=Path)

        def truediv(_self: object, name: str) -> MagicMock:
            m = MagicMock(spec=Path)
            if name == "README.md":
                m.exists.return_value = True
                m.read_text.return_value = "###\n   \n"
            else:
                m.exists.return_value = False
            return m

        mock_path.__truediv__ = truediv
        # README.md has only empty/whitespace lines → falls through
        # README.txt and readme.md don't exist → falls to run.sh
        result = get_description(mock_path)
        # run.sh also doesn't exist so "(no description)"
        assert result == "(no description)"

    @patch("python_pkg.repo_explorer._discovery._desc_from_run_sh")
    def test_no_readme_run_sh_with_desc(self, mock_desc: MagicMock) -> None:
        mock_desc.return_value = "From run.sh"
        mock_path = MagicMock(spec=Path)
        run_sh = MagicMock(spec=Path)
        run_sh.exists.return_value = True

        def truediv(_self: object, name: str) -> MagicMock:
            if name == "run.sh":
                return run_sh
            m = MagicMock(spec=Path)
            m.exists.return_value = False
            return m

        mock_path.__truediv__ = truediv
        result = get_description(mock_path)
        assert result == "From run.sh"

    @patch("python_pkg.repo_explorer._discovery._desc_from_run_sh")
    def test_no_readme_run_sh_empty_desc(self, mock_desc: MagicMock) -> None:
        mock_desc.return_value = ""
        mock_path = MagicMock(spec=Path)
        run_sh = MagicMock(spec=Path)
        run_sh.exists.return_value = True

        def truediv(_self: object, name: str) -> MagicMock:
            if name == "run.sh":
                return run_sh
            m = MagicMock(spec=Path)
            m.exists.return_value = False
            return m

        mock_path.__truediv__ = truediv
        result = get_description(mock_path)
        assert result == "(no description)"

    def test_no_readme_no_run_sh(self) -> None:
        mock_path = MagicMock(spec=Path)

        def truediv(_self: object, _name: str) -> MagicMock:
            m = MagicMock(spec=Path)
            m.exists.return_value = False
            return m

        mock_path.__truediv__ = truediv
        result = get_description(mock_path)
        assert result == "(no description)"
