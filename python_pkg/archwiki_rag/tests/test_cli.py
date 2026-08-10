"""Tests for archwiki_rag.cli."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.archwiki_rag import cli
from python_pkg.archwiki_rag.sync import SyncResult

MOD = "python_pkg.archwiki_rag.cli"


class TestBuildParser:
    def test_requires_a_subcommand(self) -> None:
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args([])

    def test_sync_defaults(self) -> None:
        args = cli.build_parser().parse_args(["sync"])
        assert args.command == "sync"
        assert args.reindex is False
        assert args.ignore_load is False

    def test_sync_accepts_overrides(self) -> None:
        args = cli.build_parser().parse_args(
            ["sync", "--source", "/s", "--store", "/d", "--reindex", "--ignore-load"],
        )
        assert args.source == Path("/s")
        assert args.store == Path("/d")
        assert args.reindex is True
        assert args.ignore_load is True


class TestRunSync:
    def test_missing_source_reports_error(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        args = cli.build_parser().parse_args(
            ["sync", "--source", str(tmp_path / "absent"), "--store", str(tmp_path)],
        )
        assert cli.run_sync(args) == 1
        assert "arch-wiki-docs" in capsys.readouterr().out

    @patch(f"{MOD}.sync_pages", return_value=SyncResult(3, 2, 1))
    def test_reports_counts(
        self,
        mock_sync: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        args = cli.build_parser().parse_args(
            ["sync", "--source", str(tmp_path), "--store", str(tmp_path)],
        )
        assert cli.run_sync(args) == 0
        assert "converted 3, changed 2, skipped 1" in capsys.readouterr().out

    @patch(f"{MOD}.reindex_mod.run_reindex")
    @patch(f"{MOD}.sync_pages", return_value=SyncResult(3, 0, 0))
    def test_skips_reindex_when_nothing_changed(
        self,
        mock_sync: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        args = cli.build_parser().parse_args(
            ["sync", "--source", str(tmp_path), "--store", str(tmp_path), "--reindex"],
        )
        assert cli.run_sync(args) == 0
        assert "nothing changed" in capsys.readouterr().out
        mock_run.assert_not_called()

    @patch(f"{MOD}.reindex_mod.run_reindex")
    @patch(
        f"{MOD}.reindex_mod.blocking_reason",
        return_value="machine is busy (load 4.00/core)",
    )
    @patch(f"{MOD}.sync_pages", return_value=SyncResult(3, 3, 0))
    def test_defers_when_blocked(
        self,
        mock_sync: MagicMock,
        mock_reason: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        args = cli.build_parser().parse_args(
            ["sync", "--source", str(tmp_path), "--store", str(tmp_path), "--reindex"],
        )
        assert cli.run_sync(args) == 0
        assert "deferring reindex: machine is busy" in capsys.readouterr().out
        mock_run.assert_not_called()

    @patch(f"{MOD}.reindex_mod.run_reindex", return_value=0)
    @patch(f"{MOD}.reindex_mod.blocking_reason", return_value=None)
    @patch(f"{MOD}.sync_pages", return_value=SyncResult(3, 3, 0))
    def test_runs_reindex_when_clear(
        self,
        mock_sync: MagicMock,
        mock_reason: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        args = cli.build_parser().parse_args(
            ["sync", "--source", str(tmp_path), "--store", str(tmp_path), "--reindex"],
        )
        assert cli.run_sync(args) == 0
        assert "reindexing..." in capsys.readouterr().out
        mock_run.assert_called_once_with(Path(str(tmp_path)))

    @patch(f"{MOD}.reindex_mod.run_reindex", return_value=127)
    @patch(f"{MOD}.reindex_mod.blocking_reason", return_value=None)
    @patch(f"{MOD}.sync_pages", return_value=SyncResult(3, 3, 0))
    def test_propagates_reindex_failure(
        self,
        mock_sync: MagicMock,
        mock_reason: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        args = cli.build_parser().parse_args(
            ["sync", "--source", str(tmp_path), "--store", str(tmp_path), "--reindex"],
        )
        assert cli.run_sync(args) == 127

    @patch(f"{MOD}.reindex_mod.blocking_reason", return_value=None)
    @patch(f"{MOD}.reindex_mod.run_reindex", return_value=0)
    @patch(f"{MOD}.sync_pages", return_value=SyncResult(1, 1, 0))
    def test_ignore_load_is_forwarded(
        self,
        mock_sync: MagicMock,
        mock_run: MagicMock,
        mock_reason: MagicMock,
        tmp_path: Path,
    ) -> None:
        args = cli.build_parser().parse_args(
            [
                "sync",
                "--source",
                str(tmp_path),
                "--store",
                str(tmp_path),
                "--reindex",
                "--ignore-load",
            ],
        )
        cli.run_sync(args)
        assert mock_reason.call_args.kwargs["ignore_load"] is True


class TestMain:
    @patch(f"{MOD}.run_sync", return_value=0)
    def test_dispatches_to_run_sync(self, mock_run_sync: MagicMock) -> None:
        assert cli.main(["sync"]) == 0
        mock_run_sync.assert_called_once()
