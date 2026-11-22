"""Tests for linux_configuration/gaming/game_rec_dbus.py (jeepney plumbing).

``FakeConn`` (tests/test_game_rec_fakes.py) stands in for jeepney's blocking
connection; no test opens a real bus.
"""

from __future__ import annotations

import game_rec_dbus as grd
from jeepney import DBusAddress, HeaderFields, new_method_return, new_signal

from tests.test_game_rec_fakes import FOX_PATH, RAT, RAT_PATH, FakeConn


class TestJeepneyBus:
    """``JeepneyBus`` maps the small bus interface onto jeepney calls."""

    def test_call_targets_systemd_and_unwraps(self) -> None:
        conn = FakeConn([])
        bus = grd.JeepneyBus(conn)
        assert bus.call(grd.MANAGER_PATH, grd.MANAGER_IFACE, "Subscribe") == ("ok",)
        fields = conn.sent[0].header.fields
        assert fields[HeaderFields.destination] == grd.SYSTEMD
        assert fields[HeaderFields.member] == "Subscribe"

    def test_matches_go_to_the_bus_daemon(self) -> None:
        conn = FakeConn([])
        bus = grd.JeepneyBus(conn)
        rule = grd.props_rule(RAT_PATH)
        bus.add_match(rule)
        bus.remove_match(rule)
        members = [m.header.fields[HeaderFields.member] for m in conn.sent]
        assert members == ["AddMatch", "RemoveMatch"]
        assert conn.sent[0].body == (rule.serialise(),)

    def test_next_signal_skips_non_signals(self) -> None:
        sig = new_signal(
            DBusAddress(grd.MANAGER_PATH, interface=grd.MANAGER_IFACE),
            "UnitNew",
            "so",
            (RAT, RAT_PATH),
        )
        reply = new_method_return(
            new_signal(DBusAddress("/x", interface="org.example.I"), "m")
        )
        conn = FakeConn([reply, sig])
        bus = grd.JeepneyBus(conn)
        assert bus.next_signal() == (
            grd.MANAGER_PATH,
            grd.MANAGER_IFACE,
            "UnitNew",
            (RAT, RAT_PATH),
        )


class TestJeepneyDiscard:
    """``JeepneyBus.discard_pending`` drops only that unit's queued changes."""

    def test_drops_only_matching_properties_changed(self) -> None:
        conn = FakeConn([])
        bus = grd.JeepneyBus(conn)
        props = DBusAddress(RAT_PATH, interface=grd.PROPS_IFACE)
        stale = new_signal(
            props, "PropertiesChanged", "sa{sv}as", (grd.UNIT_IFACE, {}, [])
        )
        other = new_signal(
            DBusAddress(FOX_PATH, interface=grd.PROPS_IFACE),
            "PropertiesChanged",
            "sa{sv}as",
            (grd.UNIT_IFACE, {}, []),
        )
        new = new_signal(
            DBusAddress(grd.MANAGER_PATH, interface=grd.MANAGER_IFACE),
            "UnitNew",
            "so",
            (RAT, RAT_PATH),
        )
        queue = conn.queues[0][1]
        queue.extend([stale, other, new])
        bus.discard_pending(RAT_PATH)
        assert list(queue) == [other, new]
