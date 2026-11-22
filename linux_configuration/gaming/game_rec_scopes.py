#!/usr/bin/python3
"""Print Steam game scopes of the systemd user manager as they come and go.

Steam runs each game in a transient user scope ``app-steam-app<AppID>-<pid>.scope``.
This helper prints one line per change on stdout (flushed) for
``game_rec_watch.sh``: ``new <unit>`` once a scope is active, ``removed <unit>``
once it is inactive/failed or unloaded, and a single ``sync`` after the scopes
that already ran at startup.

Event-driven, zero polling: one D-Bus connection blocks in recv. systemd only
broadcasts UnitNew/UnitRemoved while some client has called Manager.Subscribe,
so this one does (on the same connection, before listing, so no scope falls in
between). ActiveState comes from PropertiesChanged, matched per Steam scope
only. A UnitNew alone proves nothing: ``systemctl status <missing>`` loads a
stub unit and fires one, so a scope counts only once its ActiveState is live.
A ``systemctl --user daemon-reload`` replays UnitRemoved / ActiveState changes
for scopes that never stopped, so systemd is asked before any ``removed``.
It never uses BecomeMonitor/eavesdropping (a long-lived ``busctl monitor``
once exhausted the dbus-broker quota). The bus plumbing lives in
``game_rec_dbus.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
import sys
from typing import TYPE_CHECKING, TextIO

from game_rec_dbus import (
    LIVE_STATES,
    MANAGER_IFACE,
    MANAGER_PATH,
    PROPS_IFACE,
    UNIT_IFACE,
    JeepneyBus,
    manager_rule,
    props_rule,
    unit_live,
)
from jeepney.io.blocking import open_dbus_connection
from jeepney.wrappers import DBusErrorResponse

if TYPE_CHECKING:
    from collections.abc import Callable

    from game_rec_dbus import Bus, Signal

PREFIX = "app-steam-app"
SUFFIX = ".scope"
# Only these end a scope; activating/deactivating are on the way.
GONE_STATES = frozenset({"inactive", "failed"})
# ListUnitsByPatterns rows: (name, description, load, active, sub, following,
# object path, job id, job type, job path).
_ROW_NAME, _ROW_ACTIVE, _ROW_PATH = 0, 3, 6


def _never_live(_name: str, _path: str) -> bool:
    return False


@dataclass
class ScopeTracker:
    """Steam scopes seen so far, so each prints ``new``/``removed`` once.

    ``still_live(name, path)`` is asked before a ``removed``: True means the
    signal was a reload replay and the scope still runs.
    """

    names: dict[str, str] = field(default_factory=dict)
    live: set[str] = field(default_factory=set)
    still_live: Callable[[str, str], bool] = _never_live

    @staticmethod
    def wanted(name: str) -> bool:
        """Return whether ``name`` looks like a Steam game scope."""
        return name.startswith(PREFIX) and name.endswith(SUFFIX)

    def track(self, name: str, path: str) -> bool:
        """Start following ``path``; False if unwanted or already followed."""
        if not self.wanted(name) or path in self.names:
            return False
        self.names[path] = name
        return True

    def state(self, path: str, active_state: str) -> str | None:
        """Record a new ActiveState; return the line to print, if any."""
        name = self.names.get(path)
        if name is None:
            return None
        if active_state in LIVE_STATES:
            if name in self.live:
                return None
            self.live.add(name)
            return f"new {name}"
        if active_state not in GONE_STATES or name not in self.live:
            return None
        if self.still_live(name, path):
            return None
        self.live.discard(name)
        return f"removed {name}"

    def forget(self, path: str) -> tuple[bool, str | None]:
        """Stop following ``path``: (was followed, line to print).

        A live scope that systemd still runs stays followed: after a reload
        it keeps its object path and match rule, so its real exit still counts.
        """
        name = self.names.get(path)
        if name is None:
            return False, None
        if name in self.live and self.still_live(name, path):
            return False, None
        del self.names[path]
        if name not in self.live:
            return True, None
        self.live.discard(name)
        return True, f"removed {name}"


def _emit(out: TextIO, line: str | None) -> None:
    if line is not None:
        out.write(line + "\n")
        out.flush()


def _follow(
    bus: Bus, tracker: ScopeTracker, name: str, path: str, active: str | None
) -> str | None:
    """Follow a newly seen unit; return its first line, if any."""
    if not tracker.track(name, path):
        return None
    bus.add_match(props_rule(path))
    if active is None:
        try:
            ((_sig, active),) = bus.call(
                path, PROPS_IFACE, "Get", "ss", (UNIT_IFACE, "ActiveState")
            )
        except DBusErrorResponse:
            # Gone already (or a status-query stub): wait for UnitRemoved.
            return None
        # Changes queued while the Get was in flight predate its answer:
        # replaying them printed a false removed/new pair in vmbox.
        bus.discard_pending(path)
    return tracker.state(path, str(active))


def _handle(bus: Bus, tracker: ScopeTracker, sig: Signal) -> str | None:
    path, interface, member, body = sig
    if interface == MANAGER_IFACE and member == "UnitNew":
        return _follow(bus, tracker, body[0], body[1], None)
    if interface == MANAGER_IFACE and member == "UnitRemoved":
        followed, line = tracker.forget(body[1])
        if followed:
            bus.remove_match(props_rule(body[1]))
        return line
    if interface == PROPS_IFACE and member == "PropertiesChanged":
        iface, changed = body[0], body[1]
        if iface == UNIT_IFACE and "ActiveState" in changed:
            return tracker.state(path, str(changed["ActiveState"][1]))
    return None


def run(bus: Bus, out: TextIO) -> None:
    """Subscribe, print the running scopes and ``sync``, then follow changes."""
    tracker = ScopeTracker(still_live=partial(unit_live, bus))
    bus.add_match(manager_rule())
    bus.call(MANAGER_PATH, MANAGER_IFACE, "Subscribe")
    (rows,) = bus.call(
        MANAGER_PATH, MANAGER_IFACE, "ListUnitsByPatterns", "asas", ([], [PREFIX + "*"])
    )
    for row in rows:
        _emit(
            out, _follow(bus, tracker, row[_ROW_NAME], row[_ROW_PATH], row[_ROW_ACTIVE])
        )
    _emit(out, "sync")
    while True:
        _emit(out, _handle(bus, tracker, bus.next_signal()))


def main() -> int:
    """Run on the session (user) bus until the reader goes away."""
    try:
        run(JeepneyBus(open_dbus_connection(bus="SESSION")), sys.stdout)
    except BrokenPipeError:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
