"""What each adb call needs, from the Bash command that runs it."""

from __future__ import annotations

import pytest

from python_pkg.phone_guard._need import SCREEN, WHOLE_PHONE, Need
from python_pkg.phone_guard.classify import adb_calls, needs


def only(command: str) -> Need:
    found = needs(command)
    assert len(found) == 1, found
    return found[0]


@pytest.mark.parametrize(
    ("command", "scope"),
    [
        # reads and file transfer never need a lease
        ("adb devices", None),
        ("adb logcat -d", None),
        ("adb pull /sdcard/a.png /tmp", None),
        ("adb push a.jpg /sdcard/", None),
        ("adb shell getprop ro.x", None),
        ("adb exec-out screencap -p", None),
        ("adb shell dumpsys window", None),
        ("adb shell settings get global x", None),
        ("adb shell cmd connectivity get-chain3-enabled", None),
        ("adb shell cmd package list", None),
        ("adb shell pm list packages", None),
        ("adb shell am broadcast -a X", None),
        ("adb shell am instrument -w a/.B", None),
        ("adb shell wm size", None),
        ("adb shell uiautomator dump", None),
        ("adb", None),
        ("adb frobnicate", None),
        # the real screen
        ("adb shell input tap 1 2", SCREEN),
        ("adb shell input -d 0 text hi", SCREEN),
        ("adb shell input swipe 1 2 3 4", SCREEN),
        ("adb shell am start -n a/.B", SCREEN),
        ("adb shell monkey -p a 1", SCREEN),
        ("adb shell wm size 1080x2400", SCREEN),
        ("adb shell pm clear --user 0", SCREEN),
        ("adb install -r unknown.apk", SCREEN),
        # one app
        ("adb shell am force-stop dev.kuhy.todo", "pkg:dev.kuhy.todo"),
        ("adb shell pm grant a.b android.permission.X", "pkg:a.b"),
        ("adb shell pm clear --user 0 -f a.b", "pkg:a.b"),
        (
            "adb shell cmd connectivity set-package-networking-enabled false a.b",
            "pkg:a.b",
        ),
        ("adb uninstall a.b", "pkg:a.b"),
        # the whole phone
        ("adb reboot", WHOLE_PHONE),
        ("adb kill-server", WHOLE_PHONE),
        ("adb shell svc wifi disable", WHOLE_PHONE),
        ("adb shell settings put global airplane_mode_on 1", WHOLE_PHONE),
        ("adb shell cmd connectivity airplane-mode enable", WHOLE_PHONE),
        ("adb shell cmd connectivity set-chain3-enabled true", WHOLE_PHONE),
        (
            "adb shell cmd connectivity set-package-networking-enabled false",
            WHOLE_PHONE,
        ),
        ("adb shell dumpsys deviceidle force-idle", WHOLE_PHONE),
        ("adb shell dumpsys battery unplug", WHOLE_PHONE),
        ("adb shell reboot", WHOLE_PHONE),
        ("adb shell setprop a b", WHOLE_PHONE),
    ],
)
def test_scopes(command: str, scope: str | None) -> None:
    need = only(command)
    assert need.scope == scope
    assert need.block is None


def test_text_without_display_is_blocked() -> None:
    for verb in ("text hi", "keyevent 4", "keycombination 113 29"):
        assert "without -d" in (only(f"adb shell input {verb}").block or "")


def test_a_virtual_display_is_reported_not_leased() -> None:
    need = only("adb shell input -d 9 text hi")
    assert (need.display, need.scope) == (9, None)
    assert only("adb shell am start --display 9 -n a/.B").display == 9


def test_a_display_flag_without_a_number_is_not_a_display() -> None:
    assert only("adb shell am start --display main -n a/.B").display is None


def test_serial_and_global_options() -> None:
    need = only("adb -s R58M1 -t 3 shell am force-stop a.b")
    assert (need.serial, need.scope) == ("R58M1", "pkg:a.b")
    assert only("adb -e -H host shell input tap 1 1").scope == SCREEN


def test_installs_use_the_resolved_package() -> None:
    found = needs("adb install -r -t app.apk", {"app.apk": "a.b"})
    assert found[0].scope == "pkg:a.b"


def test_every_call_in_a_compound_command() -> None:
    found = needs(
        "adb logcat -d | grep x && "
        "/opt/sdk/adb -s S shell 'svc data disable; input tap 1 1'"
    )
    assert [n.scope for n in found] == [None, WHOLE_PHONE, SCREEN]


def test_text_that_only_mentions_adb_is_ignored() -> None:
    assert needs('echo "adb shell input tap 1 1"') == []
    assert needs("cat <<'EOF' > s.sh\nadb shell input tap 1 1\nEOF\nls") == []
    assert needs("grep adbd log") == []


def test_unparseable_quoting_is_left_alone() -> None:
    assert needs("adb shell 'input tap") == []
    assert adb_calls("") == []
