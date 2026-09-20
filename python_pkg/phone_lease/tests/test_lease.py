"""The lease: owner identity, atomic take/refresh, expiry, release, status."""

from __future__ import annotations

from pathlib import Path
import time
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from python_pkg.phone_lease import (
    Clock,
    Lease,
    PhoneBusyError,
    acquire,
    owner_id,
    release,
    status,
)
from python_pkg.phone_lease import lease as lease_mod

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


class FakeClock:
    """A clock `acquire` can be handed instead of `time`."""

    def __init__(self, now: float = 1000.0) -> None:
        self.now = now
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, secs: float) -> None:
        self.slept.append(secs)
        self.now += secs

    def as_clock(self) -> Clock:
        return Clock(now=self.time, sleep=self.sleep)


@pytest.fixture(autouse=True)
def lease_dir(tmp_path: Path) -> Iterator[Path]:
    """Every test gets its own lease directory."""
    with patch.object(lease_mod, "LEASE_DIR", tmp_path / "leases"):
        yield tmp_path / "leases"


class TestOwnerId:
    def test_explicit_env_wins(self) -> None:
        assert owner_id(environ={"PHONE_LEASE_OWNER": "ci-run-7"}) == "ci-run-7"

    def test_finds_the_claude_ancestor(self, tmp_path: Path) -> None:
        proc = tmp_path / "proc"
        for pid, comm, ppid in (
            (300, "zsh", 200),
            (200, "claude", 100),
            (100, "systemd", 1),
        ):
            d = proc / str(pid)
            d.mkdir(parents=True)
            (d / "comm").write_text(f"{comm}\n")
            (d / "stat").write_text(f"{pid} ({comm}) S {ppid} 1 1 0 -1\n")
        with patch.object(lease_mod.Path, "read_text", _proc_reader(proc)):
            assert owner_id(pid=300, environ={}) == "claude:200"

    def test_falls_back_to_own_pid_without_a_claude_ancestor(
        self, tmp_path: Path
    ) -> None:
        proc = tmp_path / "proc"
        d = proc / "300"
        d.mkdir(parents=True)
        (d / "comm").write_text("zsh\n")
        (d / "stat").write_text("300 (zsh) S 1 1 1 0 -1\n")
        with patch.object(lease_mod.Path, "read_text", _proc_reader(proc)):
            assert owner_id(pid=300, environ={}) == "pid:300"

    def test_unreadable_proc_falls_back_to_own_pid(self) -> None:
        assert owner_id(pid=2**22 + 12345, environ={}) == f"pid:{2**22 + 12345}"

    def test_defaults_to_this_process(self) -> None:
        assert owner_id(environ={}).split(":")[0] in {"claude", "pid"}


def _proc_reader(proc: Path) -> Callable[..., str]:
    real = Path.read_text

    def read_text(self: Path, *args: object, **kwargs: object) -> str:
        if str(self).startswith("/proc/"):
            return real(proc / str(self)[len("/proc/") :], *args, **kwargs)
        return real(self, *args, **kwargs)

    return read_text


class TestAcquire:
    def test_takes_a_free_phone(self, lease_dir: Path) -> None:
        clock = FakeClock()
        got = acquire(
            "PIXEL", "deploy", owner="claude:1", ttl=10, clock=clock.as_clock()
        )
        assert got == Lease(
            serial="PIXEL", owner="claude:1", expires=1010.0, note="deploy"
        )
        assert (lease_dir / "PIXEL.json").exists()

    def test_refreshes_the_same_owner(self) -> None:
        clock = FakeClock()
        acquire("PIXEL", "a", owner="claude:1", ttl=10, clock=clock.as_clock())
        clock.now += 5
        got = acquire("PIXEL", "b", owner="claude:1", ttl=10, clock=clock.as_clock())
        assert got.expires == 1015.0
        assert got.note == "b"
        assert clock.slept == []

    def test_waits_for_a_foreign_lease_to_expire(self) -> None:
        clock = FakeClock()
        acquire("PIXEL", "other", owner="claude:2", ttl=3, clock=clock.as_clock())
        got = acquire(
            "PIXEL", "mine", owner="claude:1", ttl=10, wait=60, clock=clock.as_clock()
        )
        assert got.owner == "claude:1"
        assert clock.slept == [1.0, 1.0, 1.0]

    def test_gives_up_naming_the_holder(self) -> None:
        clock = FakeClock()
        acquire("PIXEL", "manga", owner="claude:2", ttl=1000, clock=clock.as_clock())
        with pytest.raises(
            PhoneBusyError, match=r"held by claude:2 \(manga\).*waited 2s"
        ):
            acquire("PIXEL", "mine", owner="claude:1", wait=2, clock=clock.as_clock())

    def test_uses_the_real_clock_by_default(self) -> None:
        got = acquire("PIXEL", owner="claude:1", ttl=5)
        assert got.expires == pytest.approx(time.time() + 5, abs=2)

    def test_uses_the_real_owner_by_default(self) -> None:
        assert acquire("PIXEL").owner == owner_id()

    def test_serial_with_slash_is_a_safe_filename(self, lease_dir: Path) -> None:
        acquire("192.168.1.5:5555/x", owner="claude:1")
        assert (lease_dir / "192.168.1.5:5555_x.json").exists()


class TestCorruptLeaseFile:
    def test_garbage_is_treated_as_free(self, lease_dir: Path) -> None:
        lease_dir.mkdir()
        (lease_dir / "PIXEL.json").write_text("not json")
        assert acquire("PIXEL", owner="claude:1").owner == "claude:1"

    def test_wrong_shape_is_treated_as_free(self, lease_dir: Path) -> None:
        lease_dir.mkdir()
        (lease_dir / "PIXEL.json").write_text('{"unexpected": 1}')
        assert status("PIXEL") is None


class TestRelease:
    def test_drops_own_lease(self) -> None:
        acquire("PIXEL", owner="claude:1")
        assert release("PIXEL", owner="claude:1") is True
        assert status("PIXEL") is None

    def test_leaves_a_foreign_lease_alone(self) -> None:
        acquire("PIXEL", owner="claude:2")
        assert release("PIXEL", owner="claude:1") is False
        assert status("PIXEL") is not None

    def test_nothing_to_release(self) -> None:
        assert release("PIXEL", owner="claude:1") is False

    def test_defaults_to_this_owner(self) -> None:
        acquire("PIXEL")
        assert release("PIXEL") is True


class TestStatus:
    def test_free(self) -> None:
        assert status("PIXEL") is None

    def test_expired_is_free(self) -> None:
        acquire("PIXEL", owner="claude:1", ttl=1, clock=FakeClock(now=100.0).as_clock())
        assert status("PIXEL", now=200.0) is None

    def test_live_describes_the_holder(self) -> None:
        acquire("PIXEL", "deploy", owner="claude:1", ttl=1000)
        live = status("PIXEL")
        assert live is not None
        assert live.describe().startswith(
            "phone PIXEL held by claude:1 (deploy) until "
        )
