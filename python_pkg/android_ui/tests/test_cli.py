"""Tests for :mod:`python_pkg.android_ui.cli`.

Every subcommand must exit non-zero and name the query when an element is
missing or ambiguous. A CLI that exits 0 on a failed tap is indistinguishable
from one that worked, which is the whole failure mode this package removes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.android_ui import cli
from python_pkg.android_ui.driver import (
    ElementNotFoundError,
    UiElement,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

MOD = "python_pkg.android_ui.cli"


def _element(label: str = "Connect Firebase") -> UiElement:
    """Build a representative element."""
    return UiElement(
        text=label,
        content_desc="",
        resource_id="",
        class_name="android.widget.Button",
        bounds=(0, 0, 100, 50),
        enabled=True,
        focused=False,
    )


@pytest.fixture
def ui() -> Iterator[MagicMock]:
    """Patch out the real device driver."""
    with patch(f"{MOD}.AndroidUi") as factory:
        instance = MagicMock()
        factory.return_value = instance
        yield instance


class TestDump:
    def test_prints_every_element(
        self, ui: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ui.dump.return_value = [_element("A"), _element("B")]
        assert cli.main(["dump"]) == 0
        assert "'A'" in capsys.readouterr().out


class TestFind:
    def test_prints_the_match(
        self, ui: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ui.find.return_value = _element()
        assert cli.main(["find", "Connect"]) == 0
        assert "Connect Firebase" in capsys.readouterr().out

    def test_missing_element_exits_non_zero(self, ui: MagicMock) -> None:
        ui.find.side_effect = ElementNotFoundError("no element matches 'Nope'")
        assert cli.main(["find", "Nope"]) == 1

    def test_exact_flag_is_forwarded(self, ui: MagicMock) -> None:
        ui.find.return_value = _element()
        cli.main(["--exact", "find", "Back"])
        assert ui.find.call_args.kwargs["exact"] is True


class TestTap:
    def test_reports_what_was_tapped(
        self, ui: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ui.tap.return_value = _element()
        assert cli.main(["tap", "Connect"]) == 0
        assert "tapped" in capsys.readouterr().out

    def test_failure_exits_non_zero(self, ui: MagicMock) -> None:
        ui.tap.side_effect = ElementNotFoundError("gone")
        assert cli.main(["tap", "Connect"]) == 1

    def test_timeout_is_forwarded(self, ui: MagicMock) -> None:
        ui.tap.return_value = _element()
        cli.main(["tap", "Connect", "--timeout", "42"])
        assert ui.tap.call_args.kwargs["timeout"] == 42.0


class TestWait:
    def test_prints_the_element_once_it_appears(
        self, ui: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ui.wait_for.return_value = _element("Connected.")
        assert cli.main(["wait", "Connected."]) == 0
        assert "Connected." in capsys.readouterr().out

    def test_timeout_exits_non_zero(self, ui: MagicMock) -> None:
        ui.wait_for.side_effect = ElementNotFoundError("waited 5s")
        assert cli.main(["wait", "Nope"]) == 1


class TestType:
    def test_confirms_the_text_was_verified(
        self, ui: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert cli.main(["type", "Email", "a@b.c"]) == 0
        assert "verified" in capsys.readouterr().out

    def test_unverified_typing_exits_non_zero(self, ui: MagicMock) -> None:
        ui.type_into.side_effect = ElementNotFoundError("did not change")
        assert cli.main(["type", "Email", "a@b.c"]) == 1


class TestMisc:
    def test_dismiss_keyboard(self, ui: MagicMock) -> None:
        assert cli.main(["dismiss-keyboard"]) == 0
        ui.dismiss_keyboard.assert_called_once_with()

    def test_focus_prints_the_activity(
        self, ui: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ui.current_focus.return_value = "com.example/.Main"
        assert cli.main(["focus"]) == 0
        assert "com.example/.Main" in capsys.readouterr().out

    def test_serial_is_forwarded_to_the_driver(self) -> None:
        with patch(f"{MOD}.AndroidUi") as factory:
            factory.return_value = MagicMock()
            cli.main(["-s", "ABC123", "focus"])
            assert factory.call_args.kwargs["serial"] == "ABC123"

    def test_an_unhandled_command_still_exits_cleanly(
        self, ui: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Guards the final elif's fall-through: a subcommand added to the
        # parser but not to the dispatch chain must not crash.
        real_parse = cli._build_parser().parse_args

        def _parse(argv: list[str] | None = None) -> object:
            args = real_parse(["focus"])
            args.command = "not-wired-up"
            return args

        monkeypatch.setattr(cli, "_build_parser", lambda: MagicMock(parse_args=_parse))
        assert cli.main(["focus"]) == 0

    def test_a_missing_subcommand_is_rejected(self) -> None:
        with pytest.raises(SystemExit):
            cli.main([])
