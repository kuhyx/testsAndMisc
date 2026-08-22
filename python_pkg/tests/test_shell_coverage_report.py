"""Tests for meta/scripts/shell_coverage_report.py.

The report combines two instruments that are each wrong on their own
(``docs/kcov-under-report.md``): kcov supplies the line SET but under-reports
hits, and a PS4 trace supplies the executed set but cannot see a line that
never ran. The arithmetic here is what makes the shell-coverage gate mean
something, so the tests below pin the fail-open direction hardest: a trace
must never be able to add a line that is not in the denominator.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "meta" / "scripts" / "shell_coverage_report.py"

_XML = """<?xml version="1.0" ?>
<coverage><packages><package><classes>
<class name="s" filename="{name}">
<lines>{lines}</lines>
</class>
</classes></package></packages></coverage>
"""


def _load() -> ModuleType:
    """Import the script by path; it lives outside any importable package."""
    spec = importlib.util.spec_from_file_location("shell_coverage_report", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="mod")
def _mod() -> ModuleType:
    return _load()


def _cov(tmp_path: Path, name: str, hits: dict[int, int]) -> Path:
    """Write a minimal kcov cov.xml tree for *name*."""
    out = tmp_path / "cov" / "proc"
    out.mkdir(parents=True)
    lines = "".join(f'<line number="{n}" hits="{h}"/>' for n, h in sorted(hits.items()))
    (out / "cov.xml").write_text(_XML.format(name=name, lines=lines), encoding="utf-8")
    return tmp_path / "cov"


def _trace(tmp_path: Path, source: Path, numbers: list[int]) -> Path:
    trace = tmp_path / "trace"
    trace.mkdir()
    (trace / "case.1").write_text(
        "".join(f"+PS4:{source}:{n} cmd\n" for n in numbers), encoding="utf-8"
    )
    return trace


def test_kcov_hits_alone_are_used_without_a_trace(
    mod: ModuleType, tmp_path: Path
) -> None:
    """With no trace dir the result is kcov's own reading."""
    cov = _cov(tmp_path, "s.sh", {1: 1, 2: 0})
    covered, total, uncovered, off_set = mod._measure(cov, "s.sh", None)
    assert (covered, total, uncovered, off_set) == (1, 2, ["2"], 0)


def test_trace_rescues_a_line_kcov_missed(mod: ModuleType, tmp_path: Path) -> None:
    """Defect (b): a line kcov reports as 0 hits but that provably ran."""
    source = tmp_path / "s.sh"
    source.write_text("echo one\necho two\n", encoding="utf-8")
    cov = _cov(tmp_path, "s.sh", {1: 1, 2: 0})
    trace = _trace(tmp_path, source, [2])
    covered, total, uncovered, _ = mod._measure(cov, "s.sh", trace)
    assert (covered, total, uncovered) == (2, 2, [])


def test_continuation_lines_leave_the_denominator(
    mod: ModuleType, tmp_path: Path
) -> None:
    """Defect (a): inner lines of a multi-line quoted argument are not statements."""
    source = tmp_path / "s.sh"
    # The real dwm_config.sh shape: the closing quote shares a line with the
    # rest of the command, so only the middle line is a continuation.
    source.write_text("perl -pe '\ns/a/b/;\n' f\necho after\n", encoding="utf-8")
    cov = _cov(tmp_path, "s.sh", {1: 1, 2: 0, 4: 1})
    # The trace must be non-empty: it is what tells the report where the
    # source lives, since kcov's XML carries only a basename.
    trace = _trace(tmp_path, source, [1, 4])
    covered, total, uncovered, _ = mod._measure(cov, "s.sh", trace)
    # Line 2 is inside the quote, so the denominator is 1 and 4 only.
    assert (covered, total, uncovered) == (2, 2, [])


def test_traced_line_outside_the_line_set_is_counted_not_credited(
    mod: ModuleType, tmp_path: Path
) -> None:
    """A traced line kcov never listed cannot inflate coverage, but is reported."""
    source = tmp_path / "s.sh"
    source.write_text("echo one\necho two\necho three\n", encoding="utf-8")
    cov = _cov(tmp_path, "s.sh", {1: 1})
    trace = _trace(tmp_path, source, [1, 3])
    covered, total, _, off_set = mod._measure(cov, "s.sh", trace)
    assert (covered, total, off_set) == (1, 1, 1)


def test_empty_kcov_output_reports_zero_total(mod: ModuleType, tmp_path: Path) -> None:
    """No instrumented lines is a distinct, reportable state."""
    cov = _cov(tmp_path, "other.sh", {1: 1})
    assert mod._measure(cov, "s.sh", None) == (0, 0, [], 0)


def test_line_without_a_number_is_skipped(mod: ModuleType, tmp_path: Path) -> None:
    """A malformed <line> entry must not abort the report."""
    out = tmp_path / "cov" / "proc"
    out.mkdir(parents=True)
    (out / "cov.xml").write_text(
        _XML.format(name="s.sh", lines='<line hits="1"/><line number="4" hits="1"/>'),
        encoding="utf-8",
    )
    covered, total, _, _ = mod._measure(tmp_path / "cov", "s.sh", None)
    assert (covered, total) == (1, 1)


def test_find_source_prefers_the_trace_path(mod: ModuleType, tmp_path: Path) -> None:
    """kcov records only a basename, so the trace is the source of the path."""
    source = tmp_path / "s.sh"
    source.write_text("echo one\n", encoding="utf-8")
    assert mod._find_source("s.sh", _trace(tmp_path, source, [1])) == source


def test_find_source_ignores_a_trace_path_that_is_gone(
    mod: ModuleType, tmp_path: Path
) -> None:
    """A traced path that no longer exists falls through to the repo search."""
    missing = tmp_path / "absent.sh"
    trace = _trace(tmp_path, missing, [1])
    # Nothing in the repo is called absent.sh, so the fallback finds nothing.
    assert mod._find_source("absent.sh", trace) is None


def test_find_source_without_a_trace_searches_the_repo(mod: ModuleType) -> None:
    """The fallback resolves a uniquely-named file in the repo."""
    found = mod._find_source("shell_coverage_jail.sh", None)
    assert found is not None
    assert found.name == "shell_coverage_jail.sh"


def test_find_source_refuses_an_ambiguous_name(mod: ModuleType) -> None:
    """Two files with one name yields no exclusion rather than a wrong guess."""
    assert mod._find_source("run_all.sh", None) is None


# --------------------------------------------------------------------------
# main(): the gate itself
# --------------------------------------------------------------------------


def _run_main(
    mod: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
) -> None:
    monkeypatch.setattr("sys.argv", ["shell_coverage_report.py", *argv])
    mod.main()


def test_main_prints_the_summary(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A fully covered subject prints its percentage and passes the gate."""
    cov = _cov(tmp_path, "s.sh", {1: 1, 2: 1})
    _run_main(mod, monkeypatch, [str(cov), "s.sh", "100"])
    assert "s.sh: 2/2 lines = 100.00%" in capsys.readouterr().out


def test_main_lists_uncovered_lines(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A gap is named, because the numbers alone do not help close it."""
    cov = _cov(tmp_path, "s.sh", {1: 1, 2: 0})
    with pytest.raises(SystemExit):
        _run_main(mod, monkeypatch, [str(cov), "s.sh", "100"])
    assert "uncovered: 2" in capsys.readouterr().out


def test_main_notes_lines_outside_the_line_set(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A traced line kcov never listed is surfaced as a third-defect signal."""
    source = tmp_path / "s.sh"
    source.write_text("echo one\necho two\n", encoding="utf-8")
    cov = _cov(tmp_path, "s.sh", {1: 1})
    trace = _trace(tmp_path, source, [1, 2])
    _run_main(mod, monkeypatch, [str(cov), "s.sh", "100", str(trace)])
    assert "absent from kcov's line set" in capsys.readouterr().out


def test_main_exits_when_below_the_minimum(
    mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Below the bar is a non-zero exit, which is what makes this a gate."""
    cov = _cov(tmp_path, "s.sh", {1: 1, 2: 0})
    with pytest.raises(SystemExit) as excinfo:
        _run_main(mod, monkeypatch, [str(cov), "s.sh", "100"])
    assert "below the required" in str(excinfo.value)


def test_main_exits_when_nothing_was_instrumented(
    mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Zero instrumented lines is an error, never a vacuous 100%."""
    cov = _cov(tmp_path, "other.sh", {1: 1})
    with pytest.raises(SystemExit) as excinfo:
        _run_main(mod, monkeypatch, [str(cov), "s.sh", "100"])
    assert "instrumented no lines" in str(excinfo.value)
