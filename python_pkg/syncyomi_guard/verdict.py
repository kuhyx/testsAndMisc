"""Decide whether a payload change is normal drift or a silent collapse.

The thresholds here encode one real incident. A pure "is it zero?" check would
have caught 2026-08-09, but Kamiruku's report on upstream #1634 describes the
harder case — a restore that keeps *some* entries and drops the rest. A library
does not lose a tenth of itself between two syncs, so that is the line.

Categories get their own rule because on 2026-08-09 all 2182 manga survived the
round trip and all 18 categories did not. A manga-only check would have called
that a clean sync.
"""

from __future__ import annotations

from dataclasses import dataclass
import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python_pkg.syncyomi_guard.payload import PayloadStats


class Status(enum.Enum):
    """Outcome of comparing a payload against the last known good one."""

    OK = "ok"
    FIRST_RUN = "first-run"
    COLLAPSED = "collapsed"


@dataclass(frozen=True)
class Thresholds:
    """Limits distinguishing acceptable shrinkage from data loss.

    ``max_drop_ratio`` is a fraction: 0.10 fails a drop of more than 10 %.
    Removing a few finished series is normal; losing a tenth of a 2000-entry
    library in one sync is not something that happens on purpose.
    """

    max_drop_ratio: float = 0.10

    def __post_init__(self) -> None:
        """Reject a ratio outside the open interval (0, 1).

        Raises:
            ValueError: If ``max_drop_ratio`` is not a usable fraction.
        """
        if not 0.0 < self.max_drop_ratio < 1.0:
            msg = f"max_drop_ratio must be in (0, 1), got {self.max_drop_ratio}"
            raise ValueError(msg)


@dataclass(frozen=True)
class Verdict:
    """The guard's decision, plus the reason, for logs and notifications."""

    status: Status
    reason: str
    current: PayloadStats
    previous: PayloadStats | None

    @property
    def is_failure(self) -> bool:
        """Whether this verdict should fail the run and alert."""
        return self.status is Status.COLLAPSED


def _drop_reason(
    label: str,
    previous: int,
    current: int,
    thresholds: Thresholds,
) -> str | None:
    """Return a failure reason if ``label`` dropped too far, else ``None``."""
    if previous == 0 or current >= previous:
        return None
    if current == 0:
        return f"{label} went from {previous} to 0"
    dropped = (previous - current) / previous
    if dropped > thresholds.max_drop_ratio:
        return (
            f"{label} dropped {dropped:.0%} "
            f"({previous} to {current}, limit {thresholds.max_drop_ratio:.0%})"
        )
    return None


def compare(
    current: PayloadStats,
    previous: PayloadStats | None,
    thresholds: Thresholds | None = None,
) -> Verdict:
    """Compare a payload against the last known good snapshot.

    A missing ``previous`` is reported as ``FIRST_RUN`` rather than success, so
    that a lost state file cannot quietly turn the guard into a no-op that
    reports OK forever.
    """
    limits = thresholds or Thresholds()

    if previous is None:
        return Verdict(
            status=Status.FIRST_RUN,
            reason=f"no baseline yet; recording {current.describe()}",
            current=current,
            previous=None,
        )

    failures = [
        reason
        for label, before, after in (
            ("manga", previous.manga, current.manga),
            ("chapters", previous.chapters, current.chapters),
            ("categories", previous.categories, current.categories),
        )
        if (reason := _drop_reason(label, before, after, limits)) is not None
    ]

    if failures:
        return Verdict(
            status=Status.COLLAPSED,
            reason="; ".join(failures),
            current=current,
            previous=previous,
        )

    return Verdict(
        status=Status.OK,
        reason=current.describe(),
        current=current,
        previous=previous,
    )
