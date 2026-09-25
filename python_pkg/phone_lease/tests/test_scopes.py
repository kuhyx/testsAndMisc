"""Scoped leases: packages, the whole phone, cleanup, holds, and the reaper."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.phone_lease import (
    WHOLE_PHONE_MAX_TTL,
    Clock,
    Lease,
    PhoneBusyError,
    Terms,
    _cleanup,
    acquire,
    holds,
    reap,
    release,
    scope_of,
    status,
    status_all,
)
from python_pkg.phone_lease import lease as lease_mod

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

WHOLE = scope_of(whole_phone=True)


@dataclass
class Mocks:
    """The two subprocess-touching hooks, replaced for every test."""

    run: MagicMock
    spawn: MagicMock


@pytest.fixture(autouse=True)
def mocks(tmp_path: Path) -> Iterator[Mocks]:
    """Own lease directory; cleanup commands and reapers never really run."""
    with (
        patch.object(lease_mod, "LEASE_DIR", tmp_path / "leases"),
        patch.object(_cleanup, "run", return_value=[]) as run,
        patch.object(_cleanup, "spawn_reaper") as spawn,
    ):
        yield Mocks(run=run, spawn=spawn)


@pytest.fixture
def lease_dir(tmp_path: Path) -> Path:
    """Where this test's lease files live."""
    return tmp_path / "leases"


def _take(owner: str, scope: str, cleanup: tuple[str, ...] = ()) -> Lease:
    terms = Terms(wait=0, cleanup=cleanup)
    return acquire("P", owner, scope=scope, terms=terms, owner=owner)


class TestScopeOf:
    def test_names(self) -> None:
        assert scope_of() == "pkg:__screen__"
        assert scope_of("a.b") == "pkg:a.b"
        assert scope_of("a.b", whole_phone=True) == "whole-phone"


class TestConflicts:
    def test_different_packages_coexist(self) -> None:
        _take("A", "pkg:a")
        _take("B", "pkg:b")
        assert {x.owner for x in status_all("P")} == {"A", "B"}

    def test_same_package_is_exclusive(self) -> None:
        _take("A", "pkg:a")
        with pytest.raises(PhoneBusyError, match=r"\[pkg:a\] held by A"):
            _take("B", "pkg:a")

    def test_whole_phone_waits_for_every_foreign_lease(self) -> None:
        _take("A", "pkg:a")
        with pytest.raises(PhoneBusyError):
            _take("B", WHOLE)

    def test_whole_phone_blocks_every_foreign_lease(self) -> None:
        _take("A", WHOLE)
        with pytest.raises(PhoneBusyError, match="whole-phone"):
            _take("B", "pkg:z")

    def test_own_leases_never_conflict(self) -> None:
        _take("A", "pkg:a")
        assert _take("A", WHOLE).scope == WHOLE


class TestWholePhone:
    def test_ttl_is_capped(self) -> None:
        clock = Clock(now=lambda: 100.0, sleep=lambda _s: None)
        got = acquire("P", scope=WHOLE, terms=Terms(ttl=9999), owner="A", clock=clock)
        assert got.expires == 100.0 + WHOLE_PHONE_MAX_TTL

    def test_reaper_only_for_a_new_lease_with_cleanup(self, mocks: Mocks) -> None:
        _take("A", WHOLE, cleanup=("undo",))
        _take("A", WHOLE, cleanup=("undo",))
        _take("A", "pkg:b")
        mocks.spawn.assert_called_once_with("P", "A", WHOLE)

    def test_release_runs_cleanup_once(self, mocks: Mocks) -> None:
        _take("A", WHOLE, cleanup=("undo",))
        assert release("P", scope=WHOLE, owner="A") is True
        assert release("P", scope=WHOLE, owner="A") is False
        mocks.run.assert_called_once_with(("undo",))

    def test_expired_lease_is_cleaned_by_the_next_caller(self, mocks: Mocks) -> None:
        early = Clock(now=lambda: 0.0, sleep=lambda _s: None)
        acquire(
            "P",
            scope=WHOLE,
            terms=Terms(ttl=5, cleanup=("undo",)),
            owner="A",
            clock=early,
        )
        _take("B", "pkg:b")
        mocks.run.assert_any_call(("undo",))
        assert [x.owner for x in status_all("P")] == ["B"]


class TestHoldsAndStatus:
    def test_holds_scope_or_whole_phone(self) -> None:
        _take("A", "pkg:a")
        assert holds("P", "A", "pkg:a") is True
        assert holds("P", "A", "pkg:b") is False
        assert holds("P", "B", "pkg:a") is False
        _take("C", "pkg:c")
        release("P", scope="pkg:a", owner="A")
        release("P", scope="pkg:c", owner="C")
        _take("A", WHOLE)
        assert holds("P", "A", "pkg:anything") is True

    def test_status_by_scope(self) -> None:
        _take("A", "pkg:a")
        assert status("P", scope="pkg:a") is not None
        assert status("P") is None

    def test_reads_a_pre_scope_lease_file(self, lease_dir: Path) -> None:
        lease_dir.mkdir()
        (lease_dir / "P.json").write_text(
            json.dumps({"serial": "P", "owner": "old", "expires": 9e12, "note": "n"})
        )
        (live,) = status_all("P")
        assert (live.owner, live.scope) == ("old", "pkg:__screen__")

    def test_skips_entries_that_are_not_objects(self, lease_dir: Path) -> None:
        lease_dir.mkdir()
        good = {"serial": "P", "owner": "o", "expires": 9e12, "note": "n"}
        (lease_dir / "P.json").write_text(json.dumps({"leases": [1, "x", good]}))
        assert [x.owner for x in status_all("P")] == ["o"]

    def test_describe_names_non_screen_scopes(self) -> None:
        assert "[pkg:a]" in _take("A", "pkg:a").describe()
        assert "[" not in _take("B", "pkg:__screen__").describe()


class TestReap:
    def _clock(self, start: float) -> tuple[Clock, list[float]]:
        now = [start]
        slept: list[float] = []

        def sleep(secs: float) -> None:
            slept.append(secs)
            now[0] += secs

        return Clock(now=lambda: now[0], sleep=sleep), slept

    def test_runs_cleanup_after_expiry(self, mocks: Mocks) -> None:
        clock, slept = self._clock(0.0)
        acquire(
            "P",
            scope=WHOLE,
            terms=Terms(ttl=12, cleanup=("undo",)),
            owner="A",
            clock=clock,
        )
        assert reap("P", "A", WHOLE, clock=clock) is True
        assert slept == [5.0, 5.0, 2.0]
        mocks.run.assert_called_once_with(("undo",))

    def test_released_first_means_nothing_to_do(self) -> None:
        clock, _ = self._clock(0.0)
        assert reap("P", "A", WHOLE, clock=clock) is False

    def test_stops_when_told(self) -> None:
        _take("A", WHOLE)
        assert reap("P", "A", WHOLE, alive=lambda: False) is False

    def test_defaults_to_the_real_clock(self) -> None:
        assert reap("P", "nobody", WHOLE) is False
