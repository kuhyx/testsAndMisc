"""Tests for the a11y dump helper: build caching, install, result parsing.

The SDK tools are faked: each fake writes the file the real tool would, so the
build pipeline's wiring (what feeds what, what gets cached) is what is tested.
The real build and a real dump were verified on the Pixel 6a on 2026-09-25.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch
import zipfile

import pytest

from python_pkg.android_ui import _a11y_helper as helper
from python_pkg.android_ui._elements import UiAutomationError

if TYPE_CHECKING:
    from collections.abc import Iterator

MOD = "python_pkg.android_ui._a11y_helper"


@pytest.fixture
def source(tmp_path: Path) -> Iterator[Path]:
    """A tiny helper source: one Java file and its manifest."""
    java = tmp_path / "A11yDump.java"
    java.write_text("class A11yDump {}")
    manifest = tmp_path / "a11y_dump_manifest.xml"
    manifest.write_text("<manifest/>")
    with patch(f"{MOD}._JAVA", java), patch(f"{MOD}._MANIFEST", manifest):
        yield tmp_path


@pytest.fixture
def sdk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake SDK layout, with the cache and HOME inside tmp_path."""
    root = tmp_path / "sdk"
    for d in (
        "build-tools/35.0.0",
        "build-tools/36.0.0",
        "platforms/android-9",
        "platforms/android-36",
        "platforms/android-37.2",
    ):
        (root / d).mkdir(parents=True)
    monkeypatch.setenv("ANDROID_HOME", str(root))
    monkeypatch.setenv("ANDROID_UI_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return root


def fake_tool(calls: list[list[str]]) -> MagicMock:
    """subprocess.run stand-in that produces each tool's output file."""

    def run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        name = Path(cmd[0]).name
        if name == "d8":
            out = Path(cmd[cmd.index("--output") + 1])
            (out / "classes.dex").write_bytes(b"dex")
        elif name == "aapt2":
            with zipfile.ZipFile(cmd[cmd.index("-o") + 1], "w") as zf:
                zf.writestr("AndroidManifest.xml", "m")
        elif name == "zipalign":
            shutil.copy(cmd[-2], cmd[-1])
        elif name == "apksigner":
            shutil.copy(cmd[-1], cmd[cmd.index("--out") + 1])
        elif name == "keytool":
            Path(cmd[cmd.index("-keystore") + 1]).parent.mkdir(parents=True)
            Path(cmd[cmd.index("-keystore") + 1]).write_bytes(b"ks")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    return MagicMock(side_effect=run)


class TestIdentity:
    def test_hash_follows_the_source(self, source: Path) -> None:
        first = helper.source_hash()
        assert first == helper.source_hash()
        (source / "a11y_dump_manifest.xml").write_text("<manifest x=''/>")
        assert helper.source_hash() != first

    def test_cache_dir_defaults_under_home(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ANDROID_UI_CACHE", raising=False)
        assert helper.cache_dir() == Path.home() / ".cache" / "android_ui"


class TestSdk:
    def test_env_wins(self, sdk: Path) -> None:
        assert helper.sdk_root() == sdk

    def test_falls_back_to_home_sdk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ANDROID_HOME", raising=False)
        monkeypatch.setenv("ANDROID_SDK_ROOT", str(tmp_path / "missing"))
        fallback = tmp_path / "sdk" / "Android" / "Sdk"
        fallback.mkdir(parents=True)
        with patch(f"{MOD}.Path.home", return_value=tmp_path):
            assert helper.sdk_root() == fallback

    def test_no_sdk_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ANDROID_HOME", raising=False)
        monkeypatch.delenv("ANDROID_SDK_ROOT", raising=False)
        with (
            patch(f"{MOD}.Path.home", return_value=tmp_path),
            pytest.raises(UiAutomationError, match="no Android SDK"),
        ):
            helper.sdk_root()

    def test_build_tool_is_in_the_newest_build_tools(self, sdk: Path) -> None:
        assert helper.build_tool("aapt2") == sdk / "build-tools" / "36.0.0" / "aapt2"

    def test_newest_version_wins_and_empty_raises(self, sdk: Path) -> None:
        assert helper._newest(sdk / "build-tools").name == "36.0.0"
        assert helper._newest(sdk / "platforms", "android-").name == "android-37.2"
        with pytest.raises(UiAutomationError, match="nothing matching"):
            helper._newest(sdk / "platforms", "nope-")


class TestBuild:
    def test_builds_signs_and_caches(self, source: Path, sdk: Path) -> None:
        del source, sdk
        calls: list[list[str]] = []
        with patch(f"{MOD}.subprocess.run", fake_tool(calls)):
            apk = helper.build()
            assert apk.name == f"a11ydump-{helper.source_hash()}.apk"
            with zipfile.ZipFile(apk) as zf:
                assert "classes.dex" in zf.namelist()
            tools = [Path(c[0]).name for c in calls]
            assert tools == ["javac", "d8", "aapt2", "zipalign", "keytool", "apksigner"]
            assert f"{Path.home()}/.android/debug.keystore" in calls[4]
            calls.clear()
            assert helper.build() == apk
            assert calls == [], "a cached build runs no tool"

    def test_an_existing_keystore_is_reused(self, source: Path, sdk: Path) -> None:
        del source, sdk
        keystore = Path.home() / ".android" / "debug.keystore"
        keystore.parent.mkdir(parents=True)
        keystore.write_bytes(b"ks")
        calls: list[list[str]] = []
        with patch(f"{MOD}.subprocess.run", fake_tool(calls)):
            helper.build()
        assert "keytool" not in [Path(c[0]).name for c in calls]

    def test_a_failing_tool_is_reported(self, source: Path, sdk: Path) -> None:
        del source, sdk
        failed = subprocess.CompletedProcess(["javac"], 1, "", "boom")
        with (
            patch(f"{MOD}.subprocess.run", return_value=failed),
            pytest.raises(UiAutomationError, match=r"javac\nboom"),
        ):
            helper.build()


class TestDevice:
    def test_skips_install_when_the_phone_has_this_build(self, source: Path) -> None:
        del source
        run = MagicMock(return_value=f"versionName={helper.source_hash()}\n")
        helper.ensure_installed(run)
        run.assert_called_once_with("shell", "dumpsys", "package", helper.PACKAGE)

    def test_installs_when_missing_or_stale(self, source: Path, tmp_path: Path) -> None:
        del source
        run = MagicMock(return_value="versionName=old\n")
        with patch(f"{MOD}.build", return_value=tmp_path / "a.apk"):
            helper.ensure_installed(run)
        run.assert_called_with(
            "install", "-r", "-t", str(tmp_path / "a.apk"), timeout=120.0
        )

    def test_parse_result(self) -> None:
        out = "INSTRUMENTATION_RESULT: xml=<hierarchy/>\nINSTRUMENTATION_CODE: -1\n"
        assert helper.parse_result(out) == "<hierarchy/>"
        with pytest.raises(UiAutomationError, match=r"failed: java\.lang\.X"):
            helper.parse_result("INSTRUMENTATION_RESULT: error=java.lang.X\n")
        with pytest.raises(UiAutomationError, match="no tree"):
            helper.parse_result("INSTRUMENTATION_STATUS: nothing\n")

    def test_dump_display(self) -> None:
        run = MagicMock(return_value="INSTRUMENTATION_RESULT: xml=<h/>\n")
        with patch(f"{MOD}.ensure_installed") as ensure:
            assert helper.dump_display(run, 9) == "<h/>"
        ensure.assert_called_once_with(run)
        run.assert_called_once_with(
            "shell",
            "am",
            "instrument",
            "-w",
            "-e",
            "display",
            "9",
            "com.kuhy.a11ydump/.A11yDump",
            timeout=45.0,
        )
