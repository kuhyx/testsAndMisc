#!/usr/bin/python3
"""systemd D-Bus plumbing for ``game_rec_scopes.py``.

The small :class:`Bus` interface the scope watcher talks to, its jeepney
implementation (:class:`JeepneyBus`), the match rules, and :func:`unit_live`,
which asks systemd whether a unit still runs. Imported from the script's own
directory; no test opens a real bus (they pass a fake :class:`Bus`/``Conn``).
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any, Protocol

from jeepney import DBusAddress, HeaderFields, MatchRule, new_method_call
from jeepney.bus_messages import message_bus
from jeepney.wrappers import DBusErrorResponse, unwrap_msg

if TYPE_CHECKING:
    from jeepney import Message
    from jeepney.io.common import FilterHandle

LIVE_STATES = frozenset({"active", "reloading"})

SYSTEMD = "org.freedesktop.systemd1"
MANAGER_PATH = "/org/freedesktop/systemd1"
MANAGER_IFACE = "org.freedesktop.systemd1.Manager"
UNIT_IFACE = "org.freedesktop.systemd1.Unit"
PROPS_IFACE = "org.freedesktop.DBus.Properties"

Signal = tuple[str, str, str, tuple[Any, ...]]


class Bus(Protocol):
    """The four bus operations the watcher needs (jeepney or a test fake)."""

    def call(
        self,
        path: str,
        interface: str,
        method: str,
        signature: str | None = None,
        body: tuple[Any, ...] = (),
    ) -> tuple[Any, ...]:
        """Call a systemd method and return the reply body."""

    def add_match(self, rule: MatchRule) -> None:
        """Ask the bus daemon to route signals matching ``rule`` to us."""

    def remove_match(self, rule: MatchRule) -> None:
        """Undo :meth:`add_match`."""

    def discard_pending(self, path: str) -> None:
        """Drop queued PropertiesChanged of ``path`` (older than a Get reply)."""

    def next_signal(self) -> Signal:
        """Block until the next signal: (path, interface, member, body)."""


class Conn(Protocol):
    """The parts of jeepney's blocking DBusConnection that are used here."""

    def filter(self, rule: MatchRule, *, queue: deque[Message]) -> FilterHandle:
        """Queue incoming messages that match ``rule``."""

    def send_and_get_reply(self, message: Message) -> Message:
        """Send a method call and block for its reply."""

    def recv_messages(self) -> None:
        """Block for one message and run it through the filters."""


def manager_rule() -> MatchRule:
    """Match systemd's Manager signals (UnitNew, UnitRemoved, jobs)."""
    return MatchRule(
        type="signal", sender=SYSTEMD, interface=MANAGER_IFACE, path=MANAGER_PATH
    )


def props_rule(path: str) -> MatchRule:
    """Match PropertiesChanged of one unit's Unit interface."""
    rule = MatchRule(
        type="signal",
        sender=SYSTEMD,
        interface=PROPS_IFACE,
        member="PropertiesChanged",
        path=path,
    )
    rule.add_arg_condition(0, UNIT_IFACE)
    return rule


class JeepneyBus:
    """:class:`Bus` over a jeepney blocking connection."""

    def __init__(self, conn: Conn) -> None:
        """Queue every incoming signal, including those that arrive mid-call."""
        self._conn = conn
        self._signals: deque[Message] = deque()
        self._filter = conn.filter(MatchRule(type="signal"), queue=self._signals)

    def call(
        self,
        path: str,
        interface: str,
        method: str,
        signature: str | None = None,
        body: tuple[Any, ...] = (),
    ) -> tuple[Any, ...]:
        """Call a systemd method; raises DBusErrorResponse on an error reply."""
        addr = DBusAddress(path, bus_name=SYSTEMD, interface=interface)
        reply = self._conn.send_and_get_reply(
            new_method_call(addr, method, signature, body)
        )
        result: tuple[Any, ...] = unwrap_msg(reply)
        return result

    def add_match(self, rule: MatchRule) -> None:
        """AddMatch on the bus daemon."""
        unwrap_msg(self._conn.send_and_get_reply(message_bus.AddMatch(rule)))

    def remove_match(self, rule: MatchRule) -> None:
        """RemoveMatch on the bus daemon."""
        unwrap_msg(self._conn.send_and_get_reply(message_bus.RemoveMatch(rule)))

    def discard_pending(self, path: str) -> None:
        """Drop queued PropertiesChanged of ``path``.

        Everything queued when a reply arrives was sent before it (one
        connection keeps order), so after a Get these are stale.
        """
        kept = [
            msg
            for msg in self._signals
            if not (
                msg.header.fields.get(HeaderFields.path) == path
                and msg.header.fields.get(HeaderFields.member) == "PropertiesChanged"
            )
        ]
        self._signals.clear()
        self._signals.extend(kept)

    def next_signal(self) -> Signal:
        """Block in recv until a signal is queued, then decode its header.

        The local filter queues signals only; replies and errors are dropped.
        """
        while not self._signals:
            self._conn.recv_messages()
        msg = self._signals.popleft()
        fields = msg.header.fields
        return (
            fields.get(HeaderFields.path, ""),
            fields.get(HeaderFields.interface, ""),
            fields.get(HeaderFields.member, ""),
            msg.body,
        )


def unit_live(bus: Bus, name: str, path: str) -> bool:
    """Return whether systemd still has ``name`` loaded and live.

    systemd answers only after a running daemon-reload has finished, so the
    reply is the state after any replayed signals.
    """
    try:
        (unit_path,) = bus.call(MANAGER_PATH, MANAGER_IFACE, "GetUnit", "s", (name,))
        ((_sig, active),) = bus.call(
            str(unit_path), PROPS_IFACE, "Get", "ss", (UNIT_IFACE, "ActiveState")
        )
    except DBusErrorResponse:
        # NoSuchUnit: unloaded, so really gone.
        return False
    # Changes queued before the reply are older than it, as in
    # game_rec_scopes._follow.
    bus.discard_pending(path)
    return str(active) in LIVE_STATES
