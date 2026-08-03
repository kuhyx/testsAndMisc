"""Tests for the billsplit coverage gate."""

from __future__ import annotations

import runpy
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.billsplit_coverage import checker

if TYPE_CHECKING:
    import pathlib


def make_project(
    root: pathlib.Path,
    lcov: str | None = None,
    dart_files: tuple[str, ...] = ("lib/main.dart",),
) -> pathlib.Path:
    """Build a throwaway Flutter project tree.

    Parameters:
    root (pathlib.Path): Directory to build the project in.
    lcov (str | None): Contents of ``coverage/lcov.info``; None writes no
        report at all, which is the missing-report case.
    dart_files (tuple[str, ...]): Project-relative Dart files to create.

    Returns:
    pathlib.Path: The project root.
    """
    for relative in dart_files:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("void main() {}\n", encoding="utf-8")
    if lcov is not None:
        report = root / "coverage" / "lcov.info"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(lcov, encoding="utf-8")
    return root


class TestParseLcov:
    def test_records_only_unhit_lines(self, tmp_path: pathlib.Path) -> None:
        report = tmp_path / "lcov.info"
        report.write_text(
            "SF:lib/main.dart\nDA:1,3\nDA:2,0\nDA:9,0\nend_of_record\n",
            encoding="utf-8",
        )
        assert checker.parse_lcov(report) == {"lib/main.dart": [2, 9]}

    def test_fully_covered_file_maps_to_empty_list(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Present-and-covered must be distinguishable from absent."""
        report = tmp_path / "lcov.info"
        report.write_text("SF:lib/a.dart\nDA:1,1\nend_of_record\n", encoding="utf-8")
        assert checker.parse_lcov(report) == {"lib/a.dart": []}

    def test_normalises_windows_separators(self, tmp_path: pathlib.Path) -> None:
        report = tmp_path / "lcov.info"
        report.write_text("SF:lib\\ui\\home.dart\nDA:1,1\n", encoding="utf-8")
        assert "lib/ui/home.dart" in checker.parse_lcov(report)

    def test_da_before_any_sf_is_ignored(self, tmp_path: pathlib.Path) -> None:
        """A DA: line with no preceding SF: has no file to attribute to."""
        report = tmp_path / "lcov.info"
        report.write_text("DA:1,0\nSF:lib/a.dart\nDA:2,0\n", encoding="utf-8")
        assert checker.parse_lcov(report) == {"lib/a.dart": [2]}

    def test_unrelated_lines_are_skipped(self, tmp_path: pathlib.Path) -> None:
        report = tmp_path / "lcov.info"
        report.write_text(
            "TN:\nSF:lib/a.dart\nLF:2\nLH:1\nDA:1,0\nend_of_record\n",
            encoding="utf-8",
        )
        assert checker.parse_lcov(report) == {"lib/a.dart": [1]}

    def test_empty_report_yields_nothing(self, tmp_path: pathlib.Path) -> None:
        report = tmp_path / "lcov.info"
        report.write_text("", encoding="utf-8")
        assert checker.parse_lcov(report) == {}


class TestFindFailures:
    def test_no_gaps_returns_empty(self, tmp_path: pathlib.Path) -> None:
        project = make_project(tmp_path, lcov="")
        assert checker.find_failures({"lib/main.dart": []}, project) == []

    def test_reports_uncovered_lines(self, tmp_path: pathlib.Path) -> None:
        project = make_project(tmp_path, lcov="")
        failures = checker.find_failures({"lib/main.dart": [2, 7]}, project)
        assert failures == ["lib/main.dart: uncovered lines [2, 7]"]

    def test_reports_file_absent_from_report(self, tmp_path: pathlib.Path) -> None:
        project = make_project(
            tmp_path, lcov="", dart_files=("lib/main.dart", "lib/orphan.dart")
        )
        failures = checker.find_failures({"lib/main.dart": []}, project)
        assert failures == ["lib/orphan.dart: not executed by any test (0% coverage)"]

    def test_reports_both_kinds_together(self, tmp_path: pathlib.Path) -> None:
        project = make_project(
            tmp_path, lcov="", dart_files=("lib/main.dart", "lib/orphan.dart")
        )
        failures = checker.find_failures({"lib/main.dart": [4]}, project)
        assert failures == [
            "lib/main.dart: uncovered lines [4]",
            "lib/orphan.dart: not executed by any test (0% coverage)",
        ]

    def test_finds_dart_files_in_subdirectories(self, tmp_path: pathlib.Path) -> None:
        project = make_project(
            tmp_path, lcov="", dart_files=("lib/domain/split_engine.dart",)
        )
        failures = checker.find_failures({}, project)
        assert failures == [
            "lib/domain/split_engine.dart: not executed by any test (0% coverage)"
        ]


class TestCheck:
    def test_missing_report_exits_two(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        project = make_project(tmp_path)
        assert checker.check(project) == checker.EXIT_NO_REPORT
        assert "flutter test --coverage" in capsys.readouterr().err

    def test_incomplete_coverage_exits_one_and_names_files(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        project = make_project(
            tmp_path,
            lcov="SF:lib/main.dart\nDA:1,1\nDA:2,0\n",
            dart_files=("lib/main.dart", "lib/orphan.dart"),
        )
        assert checker.check(project) == checker.EXIT_INCOMPLETE
        err = capsys.readouterr().err
        assert "COVERAGE < 100%:" in err
        assert "lib/main.dart: uncovered lines [2]" in err
        assert "lib/orphan.dart: not executed by any test" in err

    def test_full_coverage_exits_zero(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        project = make_project(tmp_path, lcov="SF:lib/main.dart\nDA:1,1\n")
        assert checker.check(project) == 0
        assert "100% line coverage across 1 lib files." in capsys.readouterr().out


class TestMain:
    def test_project_flag_selects_the_tree(self, tmp_path: pathlib.Path) -> None:
        project = make_project(tmp_path, lcov="SF:lib/main.dart\nDA:1,1\n")
        assert checker.main(["--project", str(project)]) == 0

    def test_defaults_to_the_repo_billsplit_app(self) -> None:
        """With no --project, the gate resolves billsplit/ from this file."""
        with patch.object(checker, "check", return_value=0) as mock_check:
            assert checker.main([]) == 0
        assert mock_check.call_args[0][0].name == "billsplit"

    def test_propagates_failure_status(self, tmp_path: pathlib.Path) -> None:
        project = make_project(tmp_path)
        assert checker.main(["--project", str(project)]) == checker.EXIT_NO_REPORT


class TestModuleEntry:
    def test_main_called_when_run_as_module(self) -> None:
        """python3 -m python_pkg.billsplit_coverage runs main() and exits."""
        mock_main = MagicMock(return_value=0)
        # runpy warns if __main__ is already imported, and the suite may run in
        # a random order, so another test could have imported it first.
        sys.modules.pop("python_pkg.billsplit_coverage.__main__", None)
        with (
            patch("python_pkg.billsplit_coverage.checker.main", mock_main),
            pytest.raises(SystemExit) as excinfo,
        ):
            runpy.run_module("python_pkg.billsplit_coverage", run_name="__main__")
        assert excinfo.value.code == 0
        mock_main.assert_called_once()

    def test_main_not_called_on_plain_import(self) -> None:
        """Importing __main__ must not run the gate as a side effect."""
        mock_main = MagicMock()
        with patch("python_pkg.billsplit_coverage.checker.main", mock_main):
            sys.modules.pop("python_pkg.billsplit_coverage.__main__", None)
            runpy.run_module("python_pkg.billsplit_coverage.__main__")
        mock_main.assert_not_called()
