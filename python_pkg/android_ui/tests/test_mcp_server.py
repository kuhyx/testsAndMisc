"""Tests for :mod:`python_pkg.android_ui.mcp_server`.

The server runs in-process (FastMCP's in-memory client) over the REAL
:class:`AndroidUi`, wired to the scripted adb stand-in, so every ``isError``
asserted here comes from the driver's own verification -- not from a mock
that was told to fail. No real adb runs.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

from fastmcp import Client
import pytest

from python_pkg.android_ui import mcp_server
from python_pkg.android_ui.driver import AndroidUi, UiAutomationError
from python_pkg.android_ui.tests.conftest import FakeDevice, node, tree
from python_pkg.phone_guard.vd_state import SessionDisplay
from python_pkg.phone_lease import PhoneBusyError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from mcp.types import CallToolResult

TARGET = "python_pkg.android_ui._mcp_target"
CLI = "python_pkg.android_ui.cli"
TOOLS = {
    "dump",
    "find",
    "tap",
    "type_into",
    "type_into_field",
    "wait_for",
    "scroll_to",
    "focus",
}
# Real screen, so FakeDevice's display-0 bookkeeping applies.
REAL = {"display": 0}
FIELD = "android.widget.EditText"


@dataclass
class Rig:
    """The scripted adb plus the lease mock every tool call goes through."""

    adb: FakeDevice
    acquire: MagicMock


@pytest.fixture
def rig(monkeypatch: pytest.MonkeyPatch) -> Iterator[Rig]:
    """One phone (SER1), no virtual display, a free lease, a fake adb."""
    fake = FakeDevice()

    def build(serial: str | None = None, display: int | None = None) -> AndroidUi:
        ui = AndroidUi(serial=serial, display=display, settle_seconds=0.0)
        monkeypatch.setattr(ui, "_run", fake.run)
        return ui

    with (
        patch(f"{TARGET}.resolve_serial", side_effect=lambda s=None: s or "SER1"),
        patch(f"{TARGET}.acquire") as acquire,
        patch(f"{TARGET}.AndroidUi", side_effect=build),
        patch(f"{CLI}.owner_id", return_value="claude:1"),
        patch(f"{CLI}.own_display", return_value=None),
        patch(f"{CLI}.display_owner", return_value=None),
    ):
        yield Rig(fake, acquire)


def call(name: str, args: dict[str, Any] | None = None) -> CallToolResult:
    """Call one tool through a real MCP client session."""

    async def _go() -> CallToolResult:
        async with Client(mcp_server.mcp) as client:
            return await client.call_tool(name, args or {}, raise_on_error=False)

    return asyncio.run(_go())


def error_text(result: CallToolResult) -> str:
    """Return the error message of a failed call, asserting it failed."""
    assert result.is_error, f"expected isError, got {result}"
    return " ".join(getattr(c, "text", "") for c in result.content)


def _two_backs() -> str:
    return tree(
        node("Back", bounds="[0,0][100,50]"),
        node("OFFLINE BACKUP", bounds="[0,100][100,150]"),
    )


class TestToolList:
    def test_exactly_the_eight_driver_tools(self) -> None:
        async def _go() -> set[str]:
            async with Client(mcp_server.mcp) as client:
                return {t.name for t in await client.list_tools()}

        assert asyncio.run(_go()) == TOOLS

    def test_every_tool_takes_serial_and_display(self) -> None:
        async def _go() -> list[dict[str, Any]]:
            async with Client(mcp_server.mcp) as client:
                return [t.inputSchema for t in await client.list_tools()]

        for schema in asyncio.run(_go()):
            assert {"serial", "display"} <= set(schema["properties"])


class TestHappyPaths:
    def test_dump_lists_elements(self, rig: Rig) -> None:
        rig.adb.trees = [tree(node("Settings"), node("Home"))]
        result = call("dump", REAL)
        assert not result.is_error
        assert any("Settings" in line for line in result.data)

    def test_find_returns_bounds_without_tapping(self, rig: Rig) -> None:
        rig.adb.trees = [tree(node("Settings", bounds="[10,20][110,70]"))]
        result = call("find", {"query": "Settings", **REAL})
        assert result.data["bounds"] == [10, 20, 110, 70]
        assert result.data["center"] == [60, 45]
        assert rig.adb.taps() == []

    def test_tap_taps_the_one_match(self, rig: Rig) -> None:
        rig.adb.trees = [tree(node("Connect", bounds="[0,0][100,50]"))]
        result = call("tap", {"query": "Connect", **REAL})
        assert not result.is_error
        assert rig.adb.taps() == [(50, 25)]

    def test_exact_disambiguates(self, rig: Rig) -> None:
        rig.adb.trees = [_two_backs()]
        result = call("tap", {"query": "Back", "exact": True, **REAL})
        assert not result.is_error
        assert rig.adb.taps() == [(50, 25)]

    def test_wait_for_and_scroll_to(self, rig: Rig) -> None:
        rig.adb.trees = [tree(node("Connected."))]
        assert call("wait_for", {"query": "Connected.", **REAL}).data["label"] == (
            "Connected."
        )
        assert not call("scroll_to", {"query": "Connected.", **REAL}).is_error

    def test_focus_names_the_window(self, rig: Rig) -> None:
        assert call("focus", REAL).data == "com.example/com.example.Main"

    def test_type_into_verified(self, rig: Rig) -> None:
        before = node(desc="Email", cls=FIELD)
        after = node("a@b.c", desc="Email", cls=FIELD)
        rig.adb.trees = [tree(before), tree(before), tree(after)]
        result = call("type_into", {"query": "Email", "text": "a@b.c", **REAL})
        assert not result.is_error

    def test_type_into_field_verified(self, rig: Rig) -> None:
        rig.adb.trees = [tree(node(cls=FIELD)), tree(node("a@b.c", cls=FIELD))]
        result = call("type_into_field", {"index": 0, "text": "a@b.c", **REAL})
        assert not result.is_error


class TestErrorContract:
    def test_tap_with_no_match_is_an_error(self, rig: Rig) -> None:
        rig.adb.trees = [tree(node("Settings"))]
        result = call("tap", {"query": "No Such Button", "timeout": 0.2, **REAL})
        message = error_text(result)
        assert "No Such Button" in message
        assert "Settings" in message  # what IS on screen
        assert rig.adb.taps() == []

    def test_tap_with_two_matches_is_an_error(self, rig: Rig) -> None:
        rig.adb.trees = [_two_backs()]
        message = error_text(call("tap", {"query": "Back", "timeout": 0.2, **REAL}))
        assert "2 elements match 'Back'" in message
        assert rig.adb.taps() == []

    def test_unchanged_type_into_is_an_error(self, rig: Rig) -> None:
        rig.adb.trees = [tree(node("old", desc="Email", cls=FIELD))]
        result = call("type_into", {"query": "Email", "text": "hunter2!", **REAL})
        message = error_text(result)
        assert "'Email'" in message
        assert "length 3 before and after" in message
        assert "hunter2" not in message

    def test_unchanged_type_into_field_is_an_error(self, rig: Rig) -> None:
        rig.adb.trees = [tree(node(cls=FIELD))]
        result = call("type_into_field", {"index": 0, "text": "hunter2!", **REAL})
        message = error_text(result)
        assert "field #0" in message
        assert "length 0 before and after" in message
        assert "hunter2" not in message

    def test_adb_failure_while_typing_never_echoes_the_text(
        self, rig: Rig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rig.adb.trees = [tree(node(cls=FIELD))]
        real_run = rig.adb.run

        def failing(*args: str, timeout: float = 30.0) -> str:
            if "text" in args:
                msg = f"adb failed (1): {' '.join(args)}\nerror: hunter2secret"
                raise UiAutomationError(msg)
            return real_run(*args, timeout=timeout)

        monkeypatch.setattr(rig.adb, "run", failing)
        result = call("type_into_field", {"index": 0, "text": "hunter2secret", **REAL})
        message = error_text(result)
        assert "hunter2" not in message
        assert "redacted" in message

    def test_lease_held_elsewhere_is_an_error(self, rig: Rig) -> None:
        rig.acquire.side_effect = PhoneBusyError("held by claude:9")
        message = error_text(call("dump", REAL))
        assert "held by claude:9" in message
        assert rig.adb.calls == []


class TestDisplay:
    def test_default_is_self_and_errors_without_a_virtual_display(
        self, rig: Rig
    ) -> None:
        message = error_text(call("dump"))
        assert "no virtual display" in message
        assert rig.adb.calls == []  # nothing created, nothing driven

    def test_self_drives_the_sessions_own_display(self, rig: Rig) -> None:
        mine = SessionDisplay(owner_dir="d", display=7, sf="sf", package="com.example")
        with (
            patch(f"{CLI}.own_display", return_value=mine),
            patch("python_pkg.android_ui._a11y_helper.dump_display") as dump_vd,
        ):
            dump_vd.return_value = tree(node("Settings"))
            result = call("find", {"query": "Settings"})
        assert not result.is_error
        assert dump_vd.call_args.args[1] == 7
        assert rig.acquire.call_args.kwargs["scope"] == "pkg:com.example"

    def test_display_zero_is_the_real_screen(self, rig: Rig) -> None:
        call("dump", {"display": "0"})
        assert rig.acquire.call_args.kwargs["scope"] == "pkg:__screen__"
        assert any(c[:2] == ("shell", "uiautomator") for c in rig.adb.calls)
