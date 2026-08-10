"""Tests for the collapse-detection rules.

Anchored on the real 2026-08-09 numbers so the thresholds are judged against
what actually happened, not against invented ones.
"""

from __future__ import annotations

import pytest

from python_pkg.syncyomi_guard.payload import PayloadStats
from python_pkg.syncyomi_guard.verdict import Status, Thresholds, compare

# The library as it stood before the failed restore.
_GOOD = PayloadStats(
    size_bytes=14_083_674,
    manga=2182,
    categories=18,
    chapters=75_376,
    sources=24,
)

# What the "successful" restore pushed to the server at 22:53.
_STUB = PayloadStats(
    size_bytes=267_737,
    manga=0,
    categories=0,
    chapters=0,
    sources=24,
)

# After the good restore: manga intact, duplicate chapters collapsed,
# categories silently gone.
_DEDUPED = PayloadStats(
    size_bytes=12_277_887,
    manga=2182,
    categories=0,
    chapters=68_418,
    sources=24,
)


def test_the_real_incident_is_reported_as_collapsed() -> None:
    verdict = compare(_STUB, _GOOD)
    assert verdict.status is Status.COLLAPSED
    assert verdict.is_failure
    assert "manga went from 2182 to 0" in verdict.reason


def test_category_only_loss_is_still_a_collapse() -> None:
    """The subtle half of the incident.

    Every manga and every distinct chapter survived; only the categories went.
    A manga-only check would have called this a clean sync.
    """
    verdict = compare(_DEDUPED, _GOOD)
    assert verdict.is_failure
    assert "categories went from 18 to 0" in verdict.reason


def test_chapter_dedup_alone_does_not_trip_the_guard() -> None:
    """68418 vs 75376 is a 9.2 % drop caused by removing duplicates.

    Real event: the restore collapsed 6958 duplicate chapter entries while the
    distinct chapter count was unchanged. Failing here would make the guard cry
    wolf on a legitimate cleanup.
    """
    previous = PayloadStats(
        size_bytes=14_083_674,
        manga=2182,
        categories=18,
        chapters=75_376,
        sources=24,
    )
    current = PayloadStats(
        size_bytes=12_277_887,
        manga=2182,
        categories=18,
        chapters=68_418,
        sources=24,
    )
    assert compare(current, previous).status is Status.OK


def test_growth_is_healthy() -> None:
    bigger = PayloadStats(
        size_bytes=15_000_000,
        manga=2200,
        categories=19,
        chapters=76_000,
        sources=24,
    )
    assert compare(bigger, _GOOD).status is Status.OK


def test_small_drop_is_tolerated() -> None:
    """Finishing and removing a few series is normal."""
    smaller = PayloadStats(
        size_bytes=14_000_000,
        manga=2100,
        categories=18,
        chapters=75_000,
        sources=24,
    )
    assert compare(smaller, _GOOD).status is Status.OK


def test_drop_past_the_threshold_fails() -> None:
    halved = PayloadStats(
        size_bytes=7_000_000,
        manga=1000,
        categories=18,
        chapters=40_000,
        sources=24,
    )
    verdict = compare(halved, _GOOD)
    assert verdict.is_failure
    assert "manga dropped" in verdict.reason


def test_missing_baseline_is_first_run_not_success() -> None:
    """A lost state file must not silently turn the guard into a no-op."""
    verdict = compare(_GOOD, None)
    assert verdict.status is Status.FIRST_RUN
    assert not verdict.is_failure
    assert verdict.previous is None


def test_growth_from_a_zero_baseline_is_not_a_drop() -> None:
    assert compare(_GOOD, _STUB).status is Status.OK


def test_threshold_is_configurable() -> None:
    slightly_smaller = PayloadStats(
        size_bytes=13_000_000,
        manga=2100,
        categories=18,
        chapters=75_000,
        sources=24,
    )
    strict = Thresholds(max_drop_ratio=0.01)
    assert compare(slightly_smaller, _GOOD, strict).is_failure


@pytest.mark.parametrize("ratio", [0.0, 1.0, -0.5, 2.0])
def test_nonsense_thresholds_are_rejected(ratio: float) -> None:
    with pytest.raises(ValueError, match="max_drop_ratio"):
        Thresholds(max_drop_ratio=ratio)


def test_reason_describes_a_healthy_payload() -> None:
    assert "2182 manga" in compare(_GOOD, _GOOD).reason
