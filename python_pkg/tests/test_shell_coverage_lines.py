"""Tests for meta/scripts/lib/shell_coverage_lines.py.

This module decides what counts as a statement and what counts as executed,
so both of its failure modes are silent and one-directional:

* over-detecting continuation lines shrinks the denominator and INFLATES
  coverage, which is the fail-open direction -- it could promote an untested
  lib off the allowlist;
* losing trace lines shrinks the numerator, which merely keeps a lib on the
  allowlist that deserves to come off.

The first is the one worth pinning down hardest, so the quote-state cases
below assert exact line sets rather than counts.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "meta" / "scripts" / "lib" / "shell_coverage_lines.py"


def _load() -> ModuleType:
    """Import the module by path; it lives outside any importable package."""
    spec = importlib.util.spec_from_file_location("shell_coverage_lines", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="mod")
def _mod() -> ModuleType:
    return _load()


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# continuation_lines
# --------------------------------------------------------------------------


def test_single_line_quotes_are_not_continuations(
    mod: ModuleType, tmp_path: Path
) -> None:
    """A quote opened and closed on one line leaves no continuation."""
    src = _write(tmp_path, "a.sh", "echo 'hello'\necho \"world\"\n")
    assert mod.continuation_lines(src) == set()


def test_multiline_single_quote_marks_inner_lines(
    mod: ModuleType, tmp_path: Path
) -> None:
    """This is the real dwm_config.sh perl-block shape: only the inner lines."""
    src = _write(tmp_path, "a.sh", "perl -pe '\ns/a/b/;\ns/c/d/;\n' file\necho after\n")
    # Line 1 opens the quote and IS a statement; 2-4 are inside it; 5 is after.
    assert mod.continuation_lines(src) == {2, 3, 4}


def test_multiline_double_quote_marks_inner_lines(
    mod: ModuleType, tmp_path: Path
) -> None:
    """Double quotes span lines the same way single quotes do."""
    src = _write(tmp_path, "a.sh", 'x="\nline two\n"\necho after\n')
    assert mod.continuation_lines(src) == {2, 3}


def test_comment_outside_quotes_ends_the_line(mod: ModuleType, tmp_path: Path) -> None:
    """An apostrophe inside a comment must not open a quote state."""
    src = _write(tmp_path, "a.sh", "# don't be fooled\necho after\n")
    assert mod.continuation_lines(src) == set()


def test_backslash_escape_outside_quotes_is_skipped(
    mod: ModuleType, tmp_path: Path
) -> None:
    """An escaped quote outside quotes does not open a quote state."""
    src = _write(tmp_path, "a.sh", "echo \\'\necho after\n")
    assert mod.continuation_lines(src) == set()


def test_backslash_escape_inside_double_quotes(mod: ModuleType, tmp_path: Path) -> None:
    """An escaped double quote inside double quotes does not close them."""
    src = _write(tmp_path, "a.sh", 'x="a\\"b\nstill inside\n"\n')
    assert mod.continuation_lines(src) == {2, 3}


def test_backslash_inside_single_quotes_is_literal(
    mod: ModuleType, tmp_path: Path
) -> None:
    """Single quotes honour no escapes, so a trailing backslash closes nothing."""
    src = _write(tmp_path, "a.sh", "x='a\\'\necho after\n")
    assert mod.continuation_lines(src) == set()


def test_hash_inside_quotes_is_not_a_comment(mod: ModuleType, tmp_path: Path) -> None:
    """A # inside an open quote must not be treated as a comment."""
    src = _write(tmp_path, "a.sh", "x='# not a comment\nstill inside\n'\n")
    assert mod.continuation_lines(src) == {2, 3}


# --------------------------------------------------------------------------
# traced_lines / traced_paths
# --------------------------------------------------------------------------


def test_traced_lines_missing_dir_is_empty(mod: ModuleType, tmp_path: Path) -> None:
    """A missing trace dir yields nothing rather than raising."""
    assert mod.traced_lines(tmp_path / "absent", "x.sh") == set()
    assert mod.traced_paths(tmp_path / "absent", "x.sh") == []


def test_traced_lines_filters_by_basename(mod: ModuleType, tmp_path: Path) -> None:
    """Only the subject's own lines are collected."""
    trace = tmp_path / "trace"
    trace.mkdir()
    (trace / "case.1").write_text(
        "+PS4:/a/b/subject.sh:12 cmd\n"
        "++PS4:/a/b/subject.sh:15 cmd\n"
        "+PS4:/a/b/other.sh:99 cmd\n",
        encoding="utf-8",
    )
    assert mod.traced_lines(trace, "subject.sh") == {12, 15}


def test_traced_lines_skips_subdirectories(mod: ModuleType, tmp_path: Path) -> None:
    """A directory inside the trace dir is not read as a trace file."""
    trace = tmp_path / "trace"
    (trace / "nested").mkdir(parents=True)
    (trace / "case.1").write_text("+PS4:/a/subject.sh:3 cmd\n", encoding="utf-8")
    assert mod.traced_lines(trace, "subject.sh") == {3}


def test_traced_lines_survives_invalid_utf8(mod: ModuleType, tmp_path: Path) -> None:
    """A split multi-byte sequence must not discard the whole trace."""
    trace = tmp_path / "trace"
    trace.mkdir()
    (trace / "case.1").write_bytes(b"+PS4:/a/subject.sh:7 cmd\n\xff\xfe\n")
    assert mod.traced_lines(trace, "subject.sh") == {7}


def test_traced_paths_skips_subdirectories(mod: ModuleType, tmp_path: Path) -> None:
    """A directory inside the trace dir is not read when resolving paths."""
    trace = tmp_path / "trace"
    (trace / "nested").mkdir(parents=True)
    (trace / "case.1").write_text("+PS4:/a/subject.sh:3 cmd\n", encoding="utf-8")
    assert mod.traced_paths(trace, "subject.sh") == [Path("/a/subject.sh")]


def test_traced_paths_deduplicates(mod: ModuleType, tmp_path: Path) -> None:
    """The same source path reported many times yields one entry."""
    trace = tmp_path / "trace"
    trace.mkdir()
    (trace / "case.1").write_text(
        "+PS4:/a/subject.sh:1 c\n+PS4:/a/subject.sh:2 c\n+PS4:/b/other.sh:2 c\n",
        encoding="utf-8",
    )
    assert mod.traced_paths(trace, "subject.sh") == [Path("/a/subject.sh")]
