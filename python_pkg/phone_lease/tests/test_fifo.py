"""The fair queue: tickets, FIFO grants, kept places, drain, caps, dead owners."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.phone_lease import (
    QUEUED_EXIT,
    TICKET_TTL,
    WHOLE_PHONE,
    WHOLE_PHONE_MAX_TTL,
    Clock,
    Lease,
    PhoneQueuedError,
    Terms,
    _cleanup,
    acquire,
    queue_of,
    release,
    status_all,
)
from python_pkg.phone_lease import lease as lease_mod
from python_pkg.phone_lease import ops as ops_mod

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class Time:
    """A settable clock shared by every call in one test."""

    def __init__(self) -> None:
        self.now = 0.0

    def clock(self) -> Clock:
        def sleep(secs: float) -> None:
            self.now += secs

        return Clock(now=lambda: self.now, sleep=sleep)


@pytest.fixture(autouse=True)
def cleanup_run(tmp_path: Path) -> Iterator[MagicMock]:
    with (
        patch.object(lease_mod, "LEASE_DIR", tmp_path / "leases"),
        patch.object(_cleanup, "run", return_value=[]) as run,
        patch.object(_cleanup, "spawn_reaper"),
    ):
        yield run


@pytest.fixture
def t(monkeypatch: pytest.MonkeyPatch) -> Time:
    """The test clock; ``release`` and ``status_all`` read it too."""
    clock = Time()
    monkeypatch.setattr(ops_mod, "time", SimpleNamespace(time=lambda: clock.now))
    return clock


def take(
    t: Time,
    owner: str,
    scope: str,
    *,
    ttl: float = 10.0,
    wait: float = 0.0,
    cleanup: tuple[str, ...] = (),
) -> Lease:
    terms = Terms(ttl=ttl, wait=wait, cleanup=cleanup)
    return acquire("P", owner, scope=scope, terms=terms, owner=owner, clock=t.clock())


def queued(t: Time, owner: str, scope: str) -> PhoneQueuedError:
    with pytest.raises(PhoneQueuedError) as caught:
        take(t, owner, scope)
    return caught.value


def test_the_exit_code_is_tempfail() -> None:
    assert QUEUED_EXIT == 75


def test_waiters_get_tickets_in_arrival_order(t: Time) -> None:
    take(t, "A", "pkg:a")
    first, second = queued(t, "B", "pkg:a"), queued(t, "C", "pkg:a")
    assert (first.position, second.position) == (1, 2)
    assert first.number < second.number
    assert "rerun the same command" in str(second)
    assert [(x.owner, x.scope) for x in queue_of("P")] == [
        ("B", "pkg:a"),
        ("C", "pkg:a"),
    ]


def test_a_freed_scope_goes_to_the_first_ticket(t: Time) -> None:
    take(t, "A", "pkg:a")
    queued(t, "B", "pkg:a")
    queued(t, "C", "pkg:a")
    release("P", scope="pkg:a", owner="A")
    assert queued(t, "C", "pkg:a").position == 2  # B is first in line
    take(t, "B", "pkg:a")
    assert queued(t, "C", "pkg:a").position == 1
    assert [x.owner for x in queue_of("P")] == ["C"]


def test_other_packages_pass_the_queue(t: Time) -> None:
    take(t, "A", "pkg:a")
    queued(t, "B", "pkg:a")
    take(t, "C", "pkg:c")
    assert {x.owner for x in status_all("P")} == {"A", "C"}


def test_a_whole_phone_waiter_holds_back_later_packages(t: Time) -> None:
    take(t, "A", "pkg:a")
    queued(t, "B", WHOLE_PHONE)
    assert queued(t, "C", "pkg:c").position == 2


def test_a_retry_keeps_its_place_for_the_ticket_ttl(t: Time) -> None:
    take(t, "A", "pkg:a", ttl=1000)
    queued(t, "B", "pkg:a")
    t.now = TICKET_TTL - 5
    queued(t, "C", "pkg:a")
    t.now = TICKET_TTL - 1
    assert queued(t, "B", "pkg:a").position == 1
    t.now = 2 * TICKET_TTL  # B never came back; C did not either
    assert queued(t, "D", "pkg:a").position == 1


def test_waiting_inside_acquire_keeps_the_ticket_fresh(t: Time) -> None:
    take(t, "A", "pkg:a", ttl=1000)
    with pytest.raises(PhoneQueuedError):
        take(t, "B", "pkg:a", wait=50)
    assert queue_of("P")[0].seen == pytest.approx(t.now)


def test_a_wait_ends_in_a_grant_when_the_holder_expires(t: Time) -> None:
    take(t, "A", "pkg:a", ttl=3)
    got = take(t, "B", "pkg:a", wait=10)
    assert got.owner == "B"
    assert queue_of("P") == []


def test_a_holder_cannot_outlast_a_waiter_by_refreshing(t: Time) -> None:
    take(t, "A", "pkg:a", ttl=10)
    t.now = 5
    assert take(t, "A", "pkg:a", ttl=10).expires == 15
    queued(t, "B", "pkg:a")
    t.now = 8
    assert take(t, "A", "pkg:a", ttl=10).expires == 15


def test_whole_phone_hold_is_capped_from_the_first_grant(t: Time) -> None:
    assert WHOLE_PHONE_MAX_TTL == 30
    first = take(t, "A", WHOLE_PHONE, ttl=9999)
    assert first.expires == 30
    t.now = 20
    assert take(t, "A", WHOLE_PHONE, ttl=9999).expires == 30
    t.now = 31  # expired: a new hold starts its own 30 s
    assert take(t, "A", WHOLE_PHONE, ttl=9999).expires == 61


def test_dead_owners_are_reaped_at_once(t: Time, cleanup_run: MagicMock) -> None:
    take(t, "A", "pkg:x", ttl=1000)
    queued(t, "claude:9", "pkg:x")
    take(t, "claude:9", "pkg:y", ttl=1000, cleanup=("undo",))
    with patch(
        "python_pkg.phone_lease.owner.owner_alive",
        side_effect=lambda owner: owner != "claude:9",
    ):
        assert queued(t, "B", "pkg:x").position == 1
        assert [x.owner for x in queue_of("P")] == ["B"]
        assert take(t, "B", "pkg:y").owner == "B"
    cleanup_run.assert_any_call(("undo",))


def test_refresh_merges_cleanup_and_reaps_new_cleanup() -> None:
    t = Time()
    with patch.object(_cleanup, "spawn_reaper") as spawn:
        take(t, "A", WHOLE_PHONE)
        take(t, "A", WHOLE_PHONE, cleanup=("svc wifi enable",))
        take(t, "A", WHOLE_PHONE, cleanup=("svc data enable",))
        got = take(t, "A", WHOLE_PHONE)
    assert got.cleanup == ("svc wifi enable", "svc data enable")
    spawn.assert_called_once_with("P", "A", WHOLE_PHONE)


def test_release_drops_the_callers_ticket(t: Time) -> None:
    take(t, "A", "pkg:a")
    queued(t, "B", "pkg:a")
    assert release("P", scope="pkg:a", owner="B") is True
    assert queue_of("P") == []


def test_damaged_queue_entries_are_skipped(t: Time, tmp_path: Path) -> None:
    (tmp_path / "leases").mkdir()
    (tmp_path / "leases" / "P.json").write_text(
        json.dumps({"leases": [], "queue": [1, {"bad": 1}], "next": "x", "since": [3]})
    )
    assert queue_of("P") == []
    take(t, "A", "pkg:a")
    assert queued(t, "B", "pkg:a").number == 1


def test_a_file_that_is_not_an_object_reads_as_empty(tmp_path: Path) -> None:
    (tmp_path / "leases").mkdir()
    (tmp_path / "leases" / "P.json").write_text("[1, 2]")
    assert queue_of("P") == []
    assert status_all("P") == []
