"""Tests for archwiki_rag.reindex."""

from __future__ import annotations

from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.archwiki_rag import reindex
from python_pkg.archwiki_rag.constants import DATA_SUBDIR, LOCK_FILENAME

MOD = "python_pkg.archwiki_rag.reindex"


def _write_lock(store: Path, contents: str) -> None:
    """Create a knowledge-rag instance lock file.

    Parameters:
    store (Path): Store root.
    contents (str): Raw lock file body.
    """
    data = store / DATA_SUBDIR
    data.mkdir(parents=True, exist_ok=True)
    (data / LOCK_FILENAME).write_text(contents, encoding="utf-8")


class TestReadLockPid:
    def test_missing_lock(self, tmp_path: Path) -> None:
        assert reindex.read_lock_pid(tmp_path) is None

    def test_reads_pid(self, tmp_path: Path) -> None:
        _write_lock(tmp_path, "4321\n")
        assert reindex.read_lock_pid(tmp_path) == 4321

    def test_non_numeric_lock(self, tmp_path: Path) -> None:
        _write_lock(tmp_path, "not-a-pid\n")
        assert reindex.read_lock_pid(tmp_path) is None

    def test_empty_lock(self, tmp_path: Path) -> None:
        _write_lock(tmp_path, "")
        assert reindex.read_lock_pid(tmp_path) is None


class TestIsServerRunning:
    def test_no_lock(self, tmp_path: Path) -> None:
        assert reindex.is_server_running(tmp_path) is False

    def test_live_process(self, tmp_path: Path) -> None:
        _write_lock(tmp_path, "1\n")  # pid 1 always exists
        assert reindex.is_server_running(tmp_path) is True

    def test_stale_lock_treated_as_free(self, tmp_path: Path) -> None:
        _write_lock(tmp_path, "999999999\n")
        assert reindex.is_server_running(tmp_path) is False


class TestLoadPerCore:
    def test_divides_load_by_cpu_count(self, tmp_path: Path) -> None:
        loadavg = tmp_path / "loadavg"
        loadavg.write_text("8.00 4.00 2.00 3/1234 5678\n", encoding="utf-8")
        with (
            patch(f"{MOD}.LOADAVG_PATH", loadavg),
            patch(f"{MOD}.os.cpu_count", return_value=4),
        ):
            assert reindex.load_per_core() == 2.0

    def test_missing_file_is_not_busy(self, tmp_path: Path) -> None:
        with patch(f"{MOD}.LOADAVG_PATH", tmp_path / "absent"):
            assert reindex.load_per_core() == 0.0

    def test_unparseable_content_is_not_busy(self, tmp_path: Path) -> None:
        loadavg = tmp_path / "loadavg"
        loadavg.write_text("garbage\n", encoding="utf-8")
        with patch(f"{MOD}.LOADAVG_PATH", loadavg):
            assert reindex.load_per_core() == 0.0

    def test_empty_file_is_not_busy(self, tmp_path: Path) -> None:
        loadavg = tmp_path / "loadavg"
        loadavg.write_text("", encoding="utf-8")
        with patch(f"{MOD}.LOADAVG_PATH", loadavg):
            assert reindex.load_per_core() == 0.0

    def test_unknown_cpu_count_falls_back_to_one(self, tmp_path: Path) -> None:
        loadavg = tmp_path / "loadavg"
        loadavg.write_text("3.00 1.00 1.00 1/1 1\n", encoding="utf-8")
        with (
            patch(f"{MOD}.LOADAVG_PATH", loadavg),
            patch(f"{MOD}.os.cpu_count", return_value=None),
        ):
            assert reindex.load_per_core() == 3.0


class TestBlockingReason:
    @patch(f"{MOD}.is_server_running", return_value=True)
    def test_server_running_blocks(self, mock_running: MagicMock) -> None:
        reason = reindex.blocking_reason(Path("/store"))
        assert reason is not None
        assert "already using this store" in reason

    @patch(f"{MOD}.load_per_core", return_value=4.0)
    @patch(f"{MOD}.is_server_running", return_value=False)
    def test_busy_machine_blocks(
        self,
        mock_running: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        reason = reindex.blocking_reason(Path("/store"))
        assert reason is not None
        assert "machine is busy" in reason

    @patch(f"{MOD}.load_per_core", return_value=4.0)
    @patch(f"{MOD}.is_server_running", return_value=False)
    def test_ignore_load_overrides(
        self,
        mock_running: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        assert reindex.blocking_reason(Path("/store"), ignore_load=True) is None

    @patch(f"{MOD}.load_per_core", return_value=0.2)
    @patch(f"{MOD}.is_server_running", return_value=False)
    def test_idle_machine_is_clear(
        self,
        mock_running: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        assert reindex.blocking_reason(Path("/store")) is None


class TestRunReindex:
    def test_missing_interpreter(self) -> None:
        with patch(f"{MOD}.KNOWLEDGE_RAG_PYTHON", Path("/nonexistent/python")):
            assert reindex.run_reindex(Path("/store")) == 127

    @patch(f"{MOD}.subprocess.run")
    def test_passes_store_and_repo_root(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.dict(f"{MOD}.os.environ", {}, clear=True),
        ):
            assert reindex.run_reindex(Path("/store")) == 0

        env = mock_run.call_args.kwargs["env"]
        assert env["KNOWLEDGE_RAG_DIR"] == "/store"
        expected_root = Path(reindex.__file__).resolve().parents[2]
        assert env["PYTHONPATH"] == str(expected_root)

    @patch(f"{MOD}.subprocess.run")
    def test_prepends_to_existing_pythonpath(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess([], returncode=3)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.dict(f"{MOD}.os.environ", {"PYTHONPATH": "/pre"}, clear=True),
        ):
            assert reindex.run_reindex(Path("/store")) == 3

        assert mock_run.call_args.kwargs["env"]["PYTHONPATH"].endswith(":/pre")
