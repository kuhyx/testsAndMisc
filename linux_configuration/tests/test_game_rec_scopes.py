"""Tests for linux_configuration/gaming/game_rec_scopes.py (Steam scope events).

A fake bus (tests/test_game_rec_fakes.py) replays systemd signals; no test
opens a real bus. On 2026-11-22 the live helper printed
`new app-steam-app2708450-1226153.scope` then `sync`, the line format
game_rec_watch.sh reads.
"""

from __future__ import annotations

import io
from typing import Any

import game_rec_dbus as grd
import game_rec_scopes as grs
import pytest

from tests.test_game_rec_fakes import (
    FOX,
    FOX_PATH,
    RAT,
    RAT_PATH,
    EndError,
    FakeBus,
    FakeConn,
    list_row,
    state_change,
    unit_new,
    unit_removed,
)


def _run(bus: FakeBus) -> list[str]:
    out = io.StringIO()
    with pytest.raises(EndError):
        grs.run(bus, out)
    return out.getvalue().splitlines()


class TestRun:
    """``run`` turns systemd's unit signals into new/removed/sync lines."""

    def test_subscribes_before_listing(self) -> None:
        bus = FakeBus()
        assert _run(bus) == ["sync"]
        assert bus.calls[:2] == ["Subscribe", "ListUnitsByPatterns"]
        first = bus.matches[0]
        assert first.startswith("+")
        assert "type='signal'" in first
        assert "sender='org.freedesktop.systemd1'" in first

    def test_lists_running_scopes_before_sync(self) -> None:
        bus = FakeBus(listed=[list_row(RAT, RAT_PATH, "active")])
        assert _run(bus) == [f"new {RAT}", "sync"]
        assert any(RAT_PATH in m and "PropertiesChanged" in m for m in bus.matches)

    def test_new_scope_waits_for_active(self) -> None:
        bus = FakeBus(
            states={RAT_PATH: "inactive"},
            signals=[unit_new(RAT, RAT_PATH), state_change(RAT_PATH, "active")],
        )
        assert _run(bus) == ["sync", f"new {RAT}"]

    def test_already_active_scope_is_new_at_once(self) -> None:
        bus = FakeBus(states={RAT_PATH: "active"}, signals=[unit_new(RAT, RAT_PATH)])
        assert _run(bus) == ["sync", f"new {RAT}"]

    def test_inactive_then_unloaded_is_removed_once(self) -> None:
        bus = FakeBus(
            states={RAT_PATH: "active"},
            signals=[
                unit_new(RAT, RAT_PATH),
                state_change(RAT_PATH, "active"),
                state_change(RAT_PATH, "failed"),
                unit_removed(RAT, RAT_PATH),
            ],
        )
        assert _run(bus) == ["sync", f"new {RAT}", f"removed {RAT}"]
        assert bus.matches[-1].startswith("-")
        assert RAT_PATH in bus.matches[-1]

    def test_unloaded_while_active_is_removed(self) -> None:
        bus = FakeBus(
            states={RAT_PATH: "active"},
            signals=[unit_new(RAT, RAT_PATH), unit_removed(RAT, RAT_PATH)],
        )
        assert _run(bus) == ["sync", f"new {RAT}", f"removed {RAT}"]

    def test_status_query_stub_never_reports(self) -> None:
        # `systemctl --user status <missing>` loads a stub: UnitNew, Get fails.
        bus = FakeBus(signals=[unit_new(RAT, RAT_PATH), unit_removed(RAT, RAT_PATH)])
        assert _run(bus) == ["sync"]

    def test_duplicate_unit_new_is_ignored(self) -> None:
        bus = FakeBus(
            states={RAT_PATH: "active"},
            signals=[unit_new(RAT, RAT_PATH), unit_new(RAT, RAT_PATH)],
        )
        assert _run(bus) == ["sync", f"new {RAT}"]
        assert bus.calls.count("Get") == 1

    def test_stale_states_queued_before_get_are_dropped(self) -> None:
        # vmbox 2026-11-22: Get said active, then the queued inactive and
        # activating changes printed a false removed/new pair.
        bus = FakeBus(
            states={RAT_PATH: "active"},
            before_get=[
                state_change(RAT_PATH, "inactive"),
                state_change(RAT_PATH, "activating"),
                unit_new(FOX, FOX_PATH),
            ],
            signals=[unit_new(RAT, RAT_PATH)],
        )
        assert _run(bus) == ["sync", f"new {RAT}"]

    def test_transitional_states_are_not_removal(self) -> None:
        bus = FakeBus(
            states={RAT_PATH: "active"},
            signals=[
                unit_new(RAT, RAT_PATH),
                state_change(RAT_PATH, "deactivating"),
                state_change(RAT_PATH, "inactive"),
            ],
        )
        assert _run(bus) == ["sync", f"new {RAT}", f"removed {RAT}"]
        bus = FakeBus(
            states={RAT_PATH: "active"},
            signals=[unit_new(RAT, RAT_PATH), state_change(RAT_PATH, "activating")],
        )
        assert _run(bus) == ["sync", f"new {RAT}"]

    @pytest.mark.parametrize(
        "replayed",
        [
            pytest.param(
                [unit_removed(RAT, RAT_PATH), unit_new(RAT, RAT_PATH)],
                id="unit-removed",
            ),
            pytest.param(
                [state_change(RAT_PATH, "inactive"), state_change(RAT_PATH, "active")],
                id="state",
            ),
        ],
    )
    def test_daemon_reload_of_live_scope_is_not_removed(
        self, replayed: list[tuple[str, str, str, tuple[Any, ...]]]
    ) -> None:
        # Journal 2026-11-22: a user daemon-reload printed "gone 2708450",
        # "grace", then "resume"; a reload past the 30 s grace stops the
        # recording of a game that never exited. The real exit still counts.
        bus = FakeBus(
            listed=[list_row(RAT, RAT_PATH, "active")],
            states={RAT_PATH: "active"},
            reload=replayed,
            signals=[state_change(RAT_PATH, "inactive"), unit_removed(RAT, RAT_PATH)],
        )
        assert _run(bus) == [f"new {RAT}", "sync", f"removed {RAT}"]

    def test_other_units_and_signals_are_ignored(self) -> None:
        bus = FakeBus(
            states={FOX_PATH: "active"},
            signals=[
                unit_new(FOX, FOX_PATH),
                unit_new("app-steam-app1-2.service", "/u/s"),
                state_change(FOX_PATH, "active"),
                (grd.MANAGER_PATH, grd.MANAGER_IFACE, "JobNew", (1, "/j", FOX)),
                (
                    "/org/freedesktop/DBus",
                    "org.freedesktop.DBus",
                    "NameAcquired",
                    (":1.5",),
                ),
                (
                    RAT_PATH,
                    grd.PROPS_IFACE,
                    "PropertiesChanged",
                    ("other.iface", {}, []),
                ),
                unit_removed(FOX, FOX_PATH),
            ],
        )
        assert _run(bus) == ["sync"]
        assert bus.calls.count("Get") == 0


class TestMain:
    """``main`` exits quietly when the watcher closes the pipe."""

    def test_broken_pipe_is_a_clean_exit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom(*_args: object) -> None:
            raise BrokenPipeError

        monkeypatch.setattr(grs, "open_dbus_connection", lambda **_kw: FakeConn([]))
        monkeypatch.setattr(grs, "run", boom)
        assert grs.main() == 0
