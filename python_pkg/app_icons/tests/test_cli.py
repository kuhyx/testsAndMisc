"""Tests for app_icons.cli."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.app_icons import apps, cli

MOD = "python_pkg.app_icons.cli"


class TestSelected:
    def test_defaults_to_every_app(self) -> None:
        assert cli._selected(None) == list(apps.APPS)

    def test_keeps_registry_order(self) -> None:
        assert cli._selected(["todo", "dufs_client"]) == ["dufs_client", "todo"]


class TestListCommand:
    def test_prints_apps_and_glyphs(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert cli.main(["list"]) == 0
        out = capsys.readouterr().out
        assert "todo" in out
        assert "checklist" in out


class TestPreviewCommand:
    @patch(f"{MOD}.preview.build_contact_sheet")
    def test_passes_output_path(
        self, sheet: MagicMock, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        target = tmp_path / "sheet.png"
        sheet.return_value = target
        assert cli.main(["preview", "--app", "todo", "-o", str(target)]) == 0
        assert sheet.call_args.args == (["todo"], target)
        assert str(target) in capsys.readouterr().out


class TestGenerateCommand:
    @patch(f"{MOD}.render.safe_box_overflow", return_value=(0, 0))
    @patch(f"{MOD}.generate.write_assets", return_value=[Path("a"), Path("b")])
    def test_writes_assets_only_by_default(
        self,
        write: MagicMock,
        mock_overflow: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert cli.main(["generate", "--app", "todo"]) == 0
        assert write.call_count == 1
        assert "wrote 2 asset files" in capsys.readouterr().out

    @patch(f"{MOD}.render.safe_box_overflow", return_value=(12, 0))
    @patch(f"{MOD}.generate.write_assets", return_value=[])
    def test_warns_on_safe_box_overflow(
        self,
        mock_write: MagicMock,
        mock_overflow: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cli.main(["generate", "--app", "todo"])
        assert "safe box" in capsys.readouterr().out

    @patch(f"{MOD}.generate.run_flutter_launcher_icons")
    @patch(f"{MOD}.render.safe_box_overflow", return_value=(0, 0))
    @patch(f"{MOD}.generate.write_assets", return_value=[])
    def test_android_flag_runs_generator(
        self,
        mock_write: MagicMock,
        mock_overflow: MagicMock,
        launcher: MagicMock,
    ) -> None:
        cli.main(["generate", "--app", "todo", "--android"])
        assert launcher.call_count == 1

    @patch(f"{MOD}.generate.write_linux_icons", return_value=[Path("x")])
    @patch(f"{MOD}.render.safe_box_overflow", return_value=(0, 0))
    @patch(f"{MOD}.generate.write_assets", return_value=[])
    def test_linux_out_only_for_linux_apps(
        self,
        mock_write: MagicMock,
        mock_overflow: MagicMock,
        linux: MagicMock,
        tmp_path: Path,
    ) -> None:
        cli.main(
            [
                "generate",
                "--app",
                "todo",
                "--app",
                "dufs_client",
                "--linux-out",
                str(tmp_path),
            ]
        )
        # The todo app has a Linux desktop target; dufs_client does not.
        assert linux.call_count == 1


class TestParser:
    def test_requires_a_subcommand(self) -> None:
        with pytest.raises(SystemExit):
            cli.main([])
