"""Tests for the pure scheduling and retry helpers."""

from __future__ import annotations

import pytest

from python_pkg.wsg_grabber import scanner
from python_pkg.wsg_grabber.constants import (
    BACKOFF_BASE_S,
    BACKOFF_CAP_S,
    MIN_REQUEST_INTERVAL_S,
)
from python_pkg.wsg_grabber.models import ResumePlan, TaskKind, ThreadRef


def test_downloads_are_preferred_so_a_video_appears_early() -> None:
    """The user watches while the rest load; fetching must outrank scanning."""
    assert scanner.choose_task(5, 10, catalog_fresh=True) is TaskKind.DOWNLOAD
    assert scanner.choose_task(1, 0, catalog_fresh=False) is TaskKind.DOWNLOAD


def test_scanning_happens_when_nothing_is_queued() -> None:
    assert scanner.choose_task(0, 3, catalog_fresh=True) is TaskKind.SCAN
    assert scanner.choose_task(0, 0, catalog_fresh=False) is TaskKind.SCAN


def test_idle_only_when_the_board_is_exhausted() -> None:
    assert scanner.choose_task(0, 0, catalog_fresh=True) is TaskKind.IDLE


def test_stale_threads_picks_unseen_and_bumped_threads() -> None:
    known = {1: 100, 2: 200}
    live = [ThreadRef(1, 100), ThreadRef(2, 250), ThreadRef(3, 10)]
    assert [ref.thread_no for ref in scanner.stale_threads(known, live)] == [2, 3]


def test_stale_threads_is_empty_on_an_unchanged_board() -> None:
    known = {1: 100}
    assert scanner.stale_threads(known, [ThreadRef(1, 100)]) == []


def test_next_delay_enforces_one_request_per_second() -> None:
    assert scanner.next_delay(0.0, 0.0) == pytest.approx(MIN_REQUEST_INTERVAL_S)
    assert scanner.next_delay(10.0, 10.5) == pytest.approx(0.5)


def test_next_delay_never_goes_negative() -> None:
    assert scanner.next_delay(10.0, 99.0) == 0.0


def test_backoff_doubles_and_then_caps() -> None:
    assert scanner.backoff_seconds(1) == pytest.approx(BACKOFF_BASE_S)
    assert scanner.backoff_seconds(2) == pytest.approx(BACKOFF_BASE_S * 2)
    assert scanner.backoff_seconds(3) == pytest.approx(BACKOFF_BASE_S * 4)
    assert scanner.backoff_seconds(99) == pytest.approx(BACKOFF_CAP_S)


def test_backoff_treats_attempt_zero_as_the_first_failure() -> None:
    assert scanner.backoff_seconds(0) == pytest.approx(BACKOFF_BASE_S)


def test_an_explicit_retry_after_wins_but_is_still_capped() -> None:
    assert scanner.backoff_seconds(1, retry_after=7.0) == pytest.approx(7.0)
    assert scanner.backoff_seconds(1, retry_after=9999.0) == pytest.approx(
        BACKOFF_CAP_S,
    )


def test_a_zero_retry_after_falls_back_to_exponential_backoff() -> None:
    assert scanner.backoff_seconds(2, retry_after=0.0) == pytest.approx(
        BACKOFF_BASE_S * 2,
    )


def test_parse_retry_after_handles_the_forms_we_accept() -> None:
    assert scanner.parse_retry_after("30") == pytest.approx(30.0)
    assert scanner.parse_retry_after("  12  ") == pytest.approx(12.0)
    assert scanner.parse_retry_after(None) is None
    assert scanner.parse_retry_after("Wed, 21 Oct 2026 07:28:00 GMT") is None
    assert scanner.parse_retry_after("-5") is None


def test_resume_plan_starts_from_scratch_when_nothing_is_on_disk() -> None:
    plan = scanner.resume_plan(0, 1000)
    assert plan == ResumePlan(offset=0, discard=False)


def test_resume_plan_continues_a_genuine_partial() -> None:
    plan = scanner.resume_plan(400, 1000)
    assert plan.offset == 400
    assert not plan.discard


def test_resume_plan_bins_an_oversized_leftover() -> None:
    """A .part at or beyond the expected size is corrupt, not resumable."""
    assert scanner.resume_plan(1000, 1000).discard
    assert scanner.resume_plan(1500, 1000).discard


def test_resume_plan_with_unknown_expected_size_still_resumes() -> None:
    plan = scanner.resume_plan(400, 0)
    assert plan.offset == 400
    assert not plan.discard
