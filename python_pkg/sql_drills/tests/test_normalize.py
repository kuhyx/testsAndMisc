"""Output normaliser and diff: pure functions, no Docker."""

from __future__ import annotations

from python_pkg.sql_drills._normalize import diff, matches, normalize


def test_tabs_become_single_spaces() -> None:
    assert normalize("a\tb\tc\n") == ["a b c"]


def test_trailing_whitespace_stripped_per_line() -> None:
    assert normalize("a b  \nc\t\n") == ["a b", "c"]


def test_leading_whitespace_kept() -> None:
    assert normalize("  x\n") == ["  x"]


def test_null_stays_literal() -> None:
    assert normalize("1\tNULL\n") == ["1 NULL"]


def test_crlf_handled() -> None:
    assert normalize("a\r\nb\r\n") == ["a", "b"]


def test_empty_output_is_no_lines() -> None:
    assert normalize("") == []


def test_matches_ignores_trailing_blank_final_newline() -> None:
    assert matches("a\tb\n", "a b")


def test_case_is_strict() -> None:
    assert not matches("Alice\n", "alice\n")


def test_decimals_are_strict() -> None:
    assert not matches("2.5\n", "2.5000\n")


def test_row_order_is_strict() -> None:
    assert not matches("a\nb\n", "b\na\n")


def test_diff_empty_when_equal() -> None:
    assert diff(["a"], ["a"]) == ""


def test_diff_marks_differing_line() -> None:
    out = diff(["a", "b"], ["a", "c"])
    assert "line 2" in out
    assert "expected: b" in out
    assert "actual  : c" in out
    assert "line 1" not in out


def test_diff_reports_missing_rows() -> None:
    out = diff(["a", "b"], ["a"])
    assert "line 2" in out
    assert "expected: b" in out
    assert "actual  : <no line>" in out


def test_diff_reports_extra_rows() -> None:
    out = diff(["a"], ["a", "z"])
    assert "expected: <no line>" in out
    assert "actual  : z" in out


def test_diff_shows_whitespace_visibly() -> None:
    out = diff(["a b"], [" a b"])
    assert "expected: a b" in out
    assert "actual  : ' a b'" in out
