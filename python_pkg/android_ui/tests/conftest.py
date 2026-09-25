"""Shared fixtures and a scripted adb stand-in for the android_ui tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

MOD = "python_pkg.android_ui.cli"


@pytest.fixture
def phone() -> Iterator[None]:
    """One resolved phone, and no virtual display unless a test adds one."""
    with (
        patch(f"{MOD}.resolve_serial", side_effect=lambda s=None: s or "SER1"),
        patch(f"{MOD}.owner_id", return_value="claude:1"),
        patch(f"{MOD}.own_display", return_value=None),
        patch(f"{MOD}.display_owner", return_value=None),
    ):
        yield


def node(text: str = "", **attrs: str) -> str:
    """Render one ``<node>`` element for a fake dump.

    ``attrs`` accepts ``desc``, ``hint``, ``res``, ``cls``, ``bounds``,
    ``enabled`` and ``focused``; each falls back to a representative default.
    """
    return (
        f'<node text="{text}" content-desc="{attrs.get("desc", "")}" '
        f'hint="{attrs.get("hint", "")}" '
        f'resource-id="{attrs.get("res", "")}" '
        f'class="{attrs.get("cls", "android.widget.TextView")}" '
        f'bounds="{attrs.get("bounds", "[0,0][100,50]")}" '
        f'enabled="{attrs.get("enabled", "true")}" '
        f'focused="{attrs.get("focused", "false")}"/>'
    )


def tree(*nodes: str) -> str:
    """Wrap ``nodes`` in a hierarchy document."""
    return f"<?xml version='1.0'?><hierarchy rotation='0'>{''.join(nodes)}</hierarchy>"


class FakeDevice:
    """Scripted stand-in for adb, recording every command it is given."""

    def __init__(self, trees: list[str] | None = None) -> None:
        self.trees = trees or [tree(node("Connect"))]
        self.calls: list[tuple[str, ...]] = []
        self.keyboard_shown = False
        self.pulled = 0

    def run(self, *args: str, timeout: float = 30.0) -> str:
        """Answer an adb invocation."""
        del timeout
        self.calls.append(args)
        if args[:2] == ("shell", "dumpsys") and args[2] == "input_method":
            return f"mInputShown={'true' if self.keyboard_shown else 'false'}"
        if args[:2] == ("shell", "dumpsys") and args[2] == "window":
            return "mCurrentFocus=Window{ab12 u0 com.example/com.example.Main}"
        if args[0] == "pull":
            index = min(self.pulled, len(self.trees) - 1)
            self.pulled += 1
            Path(args[2]).write_text(self.trees[index], encoding="utf-8")
        if args[:5] == ("shell", "input", "-d", "0", "keyevent") and args[5] in {
            "111",
            "4",
        }:
            self.keyboard_shown = False
        return ""

    def taps(self) -> list[tuple[int, int]]:
        """Return every tap coordinate, in order."""
        return [
            (int(c[5]), int(c[6]))
            for c in self.calls
            if c[:5] == ("shell", "input", "-d", "0", "tap")
        ]
