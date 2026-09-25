"""Tests for ``android_ui --display``: which display a call may drive.

The real screen is shared, so it takes the screen lease; a session's own
virtual display takes only its app's lease; anyone else's display is refused
before the driver or a lease is touched.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from python_pkg.android_ui import cli
from python_pkg.phone_guard.vd_state import SessionDisplay

MOD = "python_pkg.android_ui.cli"
SCREEN_SCOPE = "pkg:__screen__"
pytestmark = pytest.mark.usefixtures("phone")


def _mine(display: int = 9, package: str = "dev.kuhy.todo") -> SessionDisplay:
    return SessionDisplay("claude_1", display, "sf", package)


class TestDisplay:
    def test_self_drives_this_sessions_display_under_its_app_lease(self) -> None:
        with (
            patch(f"{MOD}.own_display", return_value=_mine()),
            patch(f"{MOD}.AndroidUi") as factory,
            patch(f"{MOD}.acquire") as acquire,
        ):
            assert cli.main(["--display", "self", "focus"]) == 0
        factory.assert_called_once_with(serial="SER1", display=9)
        assert acquire.call_args.kwargs["scope"] == "pkg:dev.kuhy.todo"

    def test_an_explicit_id_of_ones_own_display_works(self) -> None:
        with (
            patch(f"{MOD}.own_display", return_value=_mine()),
            patch(f"{MOD}.AndroidUi") as factory,
            patch(f"{MOD}.acquire"),
        ):
            assert cli.main(["--display", "9", "focus"]) == 0
        assert factory.call_args.kwargs["display"] == 9

    def test_display_0_is_the_real_screen(self) -> None:
        with patch(f"{MOD}.AndroidUi") as factory, patch(f"{MOD}.acquire") as acquire:
            assert cli.main(["--display", "0", "focus"]) == 0
        assert factory.call_args.kwargs["display"] is None
        assert acquire.call_args.kwargs["scope"] == SCREEN_SCOPE

    @pytest.mark.parametrize(
        ("requested", "mine", "other", "needle"),
        [
            ("self", None, None, "phone_vd.sh start"),
            ("abc", None, None, "display id or 'self'"),
            ("7", None, None, "not this session's"),
            (
                "7",
                _mine(9),
                SessionDisplay("claude_2", 7, "sf", "x"),
                "owned by claude_2",
            ),
        ],
    )
    def test_refuses_what_is_not_this_sessions(
        self,
        capsys: pytest.CaptureFixture[str],
        requested: str,
        mine: SessionDisplay | None,
        other: SessionDisplay | None,
        needle: str,
    ) -> None:
        with (
            patch(f"{MOD}.own_display", return_value=mine),
            patch(f"{MOD}.display_owner", return_value=other),
            patch(f"{MOD}.AndroidUi") as factory,
            patch(f"{MOD}.acquire") as acquire,
        ):
            assert cli.main(["--display", requested, "focus"]) == 5
        factory.assert_not_called()
        acquire.assert_not_called()
        assert needle in capsys.readouterr().err
