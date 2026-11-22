"""Shared fakes for the game-rec D-Bus tests; this module holds no tests.

Named ``test_*`` only because the name-tests-test hook allows nothing else
under ``tests/`` besides conftest. ``FakeBus`` replays systemd signals in the
shapes jeepney decodes them to, per the org.freedesktop.systemd1 D-Bus API;
``FakeConn`` is just enough of jeepney's blocking connection for
``JeepneyBus``. Neither opens a real bus.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any

import game_rec_dbus as grd
from jeepney import DBusAddress, new_method_return, new_signal
from jeepney.wrappers import DBusErrorResponse, new_error

if TYPE_CHECKING:
    from jeepney import MatchRule, Message

RAT = "app-steam-app3347910-325827.scope"
RAT_PATH = "/org/freedesktop/systemd1/unit/app_2dsteam_2dapp3347910_2d325827_2escope"
FOX = "app-firefox-12.scope"
FOX_PATH = "/org/freedesktop/systemd1/unit/app_2dfirefox_2d12_2escope"


class EndError(Exception):
    """Raised by the fake bus when its scripted signals run out."""


def list_row(name: str, path: str, active: str) -> tuple[Any, ...]:
    return (name, "", "loaded", active, "running", "", path, 0, "", "/")


class FakeBus:
    """Scripted bus: canned replies per method, signals as plain tuples."""

    def __init__(
        self,
        listed: list[tuple[Any, ...]] | None = None,
        states: dict[str, str | None] | None = None,
        signals: list[tuple[str, str, str, tuple[Any, ...]]] | None = None,
        before_get: list[tuple[str, str, str, tuple[Any, ...]]] | None = None,
        reload: list[tuple[str, str, str, tuple[Any, ...]]] | None = None,
    ) -> None:
        self.listed = listed or []
        # Loaded units (name -> path), what GetUnit answers. Delivered signals
        # update it and ``states``, so a Get after an event sees its result.
        self.units = {row[0]: row[6] for row in self.listed}
        # Delivered before ``signals`` but never applied: a daemon-reload
        # replays unit signals while systemd's real state stays the same.
        self.reload = deque(reload or [])
        # Signals that reach the connection while a Get is in flight, so the
        # Get reply is newer than them.
        self.before_get = before_get or []
        self.pending: deque[tuple[str, str, str, tuple[Any, ...]]] = deque()
        self.states = states or {}
        self.signals = deque(signals or [])
        self.calls: list[str] = []
        self.matches: list[str] = []

    def call(
        self,
        path: str,
        interface: str,
        method: str,
        signature: str | None = None,
        body: tuple[Any, ...] = (),
    ) -> tuple[Any, ...]:
        del interface, signature
        self.calls.append(method)
        if method == "ListUnitsByPatterns":
            assert body == ([], ["app-steam-app*"])
            return (self.listed,)
        if method == "GetUnit":
            if body[0] not in self.units:
                raise DBusErrorResponse(error_msg())
            return (self.units[body[0]],)
        if method == "Get":
            state = self.states.get(path)
            self.pending.extend(self.before_get)
            if state is None:
                raise DBusErrorResponse(error_msg())
            return (("s", state),)
        return ()

    def add_match(self, rule: MatchRule) -> None:
        self.matches.append("+" + rule.serialise())

    def remove_match(self, rule: MatchRule) -> None:
        self.matches.append("-" + rule.serialise())

    def discard_pending(self, path: str) -> None:
        self.pending = deque(
            sig
            for sig in self.pending
            if not (sig[0] == path and sig[2] == "PropertiesChanged")
        )

    def next_signal(self) -> tuple[str, str, str, tuple[Any, ...]]:
        if self.pending:
            return self.pending.popleft()
        if self.reload:
            return self.reload.popleft()
        if not self.signals:
            raise EndError
        sig = self.signals.popleft()
        self._apply(sig)
        return sig

    def _apply(self, sig: tuple[str, str, str, tuple[Any, ...]]) -> None:
        path, _iface, member, body = sig
        if member == "UnitNew":
            self.units[body[0]] = body[1]
        elif member == "UnitRemoved":
            self.units.pop(body[0], None)
        elif member == "PropertiesChanged" and "ActiveState" in body[1]:
            self.states[path] = body[1]["ActiveState"][1]


def error_msg() -> Message:
    call = new_signal(DBusAddress("/x", interface="org.example.I"), "m")
    call.header.serial = 1
    return new_error(call, "org.freedesktop.DBus.Error.UnknownObject")


def unit_new(name: str, path: str) -> tuple[str, str, str, tuple[Any, ...]]:
    return (grd.MANAGER_PATH, grd.MANAGER_IFACE, "UnitNew", (name, path))


def unit_removed(name: str, path: str) -> tuple[str, str, str, tuple[Any, ...]]:
    return (grd.MANAGER_PATH, grd.MANAGER_IFACE, "UnitRemoved", (name, path))


def state_change(path: str, state: str) -> tuple[str, str, str, tuple[Any, ...]]:
    changed = {"ActiveState": ("s", state), "SubState": ("s", "running")}
    return (path, grd.PROPS_IFACE, "PropertiesChanged", (grd.UNIT_IFACE, changed, []))


class FakeConn:
    """Just enough of jeepney's blocking DBusConnection for ``JeepneyBus``."""

    def __init__(self, incoming: list[Message]) -> None:
        self.incoming = deque(incoming)
        self.sent: list[Message] = []
        self.queues: list[tuple[MatchRule, deque[Message]]] = []

    def filter(self, rule: MatchRule, *, queue: deque[Message]) -> object:
        self.queues.append((rule, queue))
        return object()

    def send_and_get_reply(self, msg: Message) -> Message:
        self.sent.append(msg)
        msg.header.serial = len(self.sent)
        return new_method_return(msg, "s", ("ok",))

    def recv_messages(self) -> None:
        msg = self.incoming.popleft()
        for rule, queue in self.queues:
            if rule.matches(msg):
                queue.append(msg)
