"""Tests for linux_configuration/fixes/g29_shifter_capture.py (G29 shifter grader)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import g29_shifter_capture as gsc
import pytest

if TYPE_CHECKING:
    from conftest import G29Reports

NEUTRAL_Y = 105
TOP_Y = 200
BOTTOM_Y = 45
X_LEFT = 60
X_CENTRE = 120
X_RIGHT = 180


class TestParse:
    """``parse`` decodes xxd lines and skips anything malformed."""

    def test_decodes_fields(self, g29: type[G29Reports]) -> None:
        (report,) = g29.parse_lines(
            [g29.xxd_line(gears=0x04, x=X_CENTRE, y=TOP_Y, down=True)]
        )
        assert (report.gears, report.x, report.y, report.down) == (
            0x04,
            X_CENTRE,
            TOP_Y,
            True,
        )

    def test_skips_non_xxd_lines(self, g29: type[G29Reports]) -> None:
        assert g29.parse_lines(["not a capture line\n", "\n"]) == []

    def test_skips_truncated_reports(self, g29: type[G29Reports]) -> None:
        assert g29.parse_lines(["00000000: 0800 0000 b984\n"]) == []


class TestGate:
    """``Report.gate`` maps raw X/Y onto the physical H-pattern."""

    @pytest.mark.parametrize(
        ("x", "y", "down", "expected"),
        [
            (X_LEFT, TOP_Y, False, "1st"),
            (X_LEFT, BOTTOM_Y, False, "2nd"),
            (X_CENTRE, TOP_Y, False, "3rd"),
            (X_CENTRE, BOTTOM_Y, False, "4th"),
            (X_RIGHT, TOP_Y, False, "5th"),
            (X_RIGHT, BOTTOM_Y, False, "6th"),
            (X_RIGHT, BOTTOM_Y, True, "R"),
            (X_CENTRE, NEUTRAL_Y, False, None),
            (X_LEFT, TOP_Y, True, "1st"),
        ],
    )
    def test_gate(
        self, g29: type[G29Reports], x: int, y: int, *, down: bool, expected: str | None
    ) -> None:
        (report,) = g29.parse_lines([g29.xxd_line(x=x, y=y, down=down)])
        assert report.gate == expected


class TestRuns:
    """``runs`` collapses equal gear masks and tracks the X/Y envelope."""

    def test_collapses_and_tracks_envelope(self, g29: type[G29Reports]) -> None:
        reports = g29.parse_lines(
            [
                g29.xxd_line(gears=0x01, x=X_LEFT, y=TOP_Y),
                g29.xxd_line(gears=0x01, x=X_LEFT + 10, y=TOP_Y - 20),
                g29.xxd_line(gears=0x00, x=X_CENTRE, y=NEUTRAL_Y),
            ]
        )
        first, second = gsc.runs(reports)
        assert (first.mask, first.length, first.start) == (0x01, 2, 0)
        assert (first.x_min, first.x_max) == (X_LEFT, X_LEFT + 10)
        assert (first.y_min, first.y_max) == (TOP_Y - 20, TOP_Y)
        assert (second.mask, second.length) == (0x00, 1)


class TestEdges:
    """``edges`` reports each gear bit transition once, in order."""

    def test_on_then_off(self, g29: type[G29Reports]) -> None:
        reports = g29.parse_lines(
            [g29.xxd_line(gears=0x01), g29.xxd_line(gears=0x01), g29.xxd_line()]
        )
        assert [(name, on) for _, name, on, _ in gsc.edges(reports)] == [
            ("1st", True),
            ("1st", False),
        ]


class TestMisses:
    """A dwell is a miss when the gear bit stays clear for MIN_DWELL reports."""

    def test_registered_dwell_is_not_a_miss(self, g29: type[G29Reports]) -> None:
        lines = [g29.xxd_line(gears=0x01, x=X_LEFT, y=TOP_Y)] * (gsc.MIN_DWELL + 5)
        assert gsc.misses(g29.parse_lines(lines))["1st"] == (1, 0)

    def test_unregistered_dwell_is_a_miss(self, g29: type[G29Reports]) -> None:
        lines = [g29.xxd_line(x=X_LEFT, y=TOP_Y)] * (gsc.MIN_DWELL + 5)
        assert gsc.misses(g29.parse_lines(lines))["1st"] == (1, 1)

    def test_short_dwell_is_not_an_attempt(self, g29: type[G29Reports]) -> None:
        lines = [g29.xxd_line(x=X_LEFT, y=TOP_Y)] * (gsc.MIN_DWELL - 1)
        assert gsc.misses(g29.parse_lines(lines))["1st"] == (0, 0)

    def test_brief_dropout_inside_a_dwell_is_forgiven(
        self, g29: type[G29Reports]
    ) -> None:
        lines = (
            [g29.xxd_line(gears=0x01, x=X_LEFT, y=TOP_Y)] * gsc.MIN_DWELL
            + [g29.xxd_line(x=X_LEFT, y=TOP_Y)] * (gsc.MIN_DWELL - 1)
            + [g29.xxd_line(gears=0x01, x=X_LEFT, y=TOP_Y)] * gsc.MIN_DWELL
        )
        assert gsc.misses(g29.parse_lines(lines))["1st"] == (1, 0)

    def test_neutral_reports_are_not_a_gate(self, g29: type[G29Reports]) -> None:
        lines = [g29.xxd_line()] * (gsc.MIN_DWELL + 5)
        assert all(
            stat == (0, 0) for stat in gsc.misses(g29.parse_lines(lines)).values()
        )


class TestReport:
    """``report`` prints the summary and exits non-zero only on a miss."""

    def test_clean_capture_returns_zero(
        self, g29: type[G29Reports], capsys: pytest.CaptureFixture[str]
    ) -> None:
        reports = g29.parse_lines(
            [g29.xxd_line(gears=0x01, x=X_LEFT, y=TOP_Y)] * (gsc.MIN_DWELL + 1)
        )
        assert gsc.report(reports, show_runs=False, show_edges=False) == 0
        assert "1st:   1 attempts, 0 missed" in capsys.readouterr().out

    def test_miss_returns_one(
        self, g29: type[G29Reports], capsys: pytest.CaptureFixture[str]
    ) -> None:
        reports = g29.parse_lines(
            [g29.xxd_line(x=X_LEFT, y=TOP_Y)] * (gsc.MIN_DWELL + 1)
        )
        assert gsc.report(reports, show_runs=False, show_edges=False) == 1
        assert "1 missed" in capsys.readouterr().out

    def test_runs_and_edges_are_optional_output(
        self, g29: type[G29Reports], capsys: pytest.CaptureFixture[str]
    ) -> None:
        reports = g29.parse_lines([g29.xxd_line(gears=0x01, x=X_LEFT, y=TOP_Y)] * 25)
        gsc.report(reports, show_runs=True, show_edges=True)
        out = capsys.readouterr().out
        assert "1st" in out
        assert "ON " in out

    def test_short_runs_are_omitted(
        self, g29: type[G29Reports], capsys: pytest.CaptureFixture[str]
    ) -> None:
        reports = g29.parse_lines([g29.xxd_line(gears=0x01, x=X_LEFT, y=TOP_Y)] * 5)
        gsc.report(reports, show_runs=True, show_edges=False)
        assert "X=" not in capsys.readouterr().out
