"""End-to-end orchestration: environment wiring and exit status."""

from __future__ import annotations

from pathlib import Path

import pytest

from python_pkg.endurain_import.__main__ import _route_rejected, main
from python_pkg.endurain_import.tests.conftest import (
    _env,
    _file,
    _patch_client,
    _StubMainClient,
)
from python_pkg.endurain_import.upload import Outcome, Result


def test_main_returns_one_when_unreachable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    _env(monkeypatch, tmp_path, inbox)
    _patch_client(
        monkeypatch,
        _StubMainClient(Result(Outcome.OK, 1, "ok"), reachable=False),
    )
    assert main() == 1


def test_main_succeeds_with_empty_inbox(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    _env(monkeypatch, tmp_path, inbox)
    _patch_client(monkeypatch, _StubMainClient(Result(Outcome.OK, 1, "ok")))
    assert main() == 0


def test_main_imports_and_returns_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    _file(inbox)
    _env(monkeypatch, tmp_path, inbox)
    _patch_client(monkeypatch, _StubMainClient(Result(Outcome.OK, 3, "ok")))
    assert main() == 0
    assert (inbox / "processed" / "RunnerUp_ts_Running.tcx").exists()


def test_main_fails_closed_on_ambiguous(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    _file(inbox)
    _env(monkeypatch, tmp_path, inbox)
    _patch_client(
        monkeypatch, _StubMainClient(Result(Outcome.AMBIGUOUS, None, "timeout"))
    )
    assert main() == 1


def test_main_fails_closed_on_rejection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    _file(inbox)
    _env(monkeypatch, tmp_path, inbox, ENDURAIN_BULK_DIR=str(tmp_path / "bulk"))
    _patch_client(monkeypatch, _StubMainClient(Result(Outcome.REJECTED, None, "400")))
    assert main() == 1


def test_main_prefers_tcx_over_gpx(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    """When both formats are pending, the richer TCX must be the one uploaded."""
    stem = "RunnerUp_2026-08-22-23-51-04_Running"
    (inbox / f"{stem}.gpx").write_text("<gpx/>")
    (inbox / f"{stem}.tcx").write_text("<tcx/>")
    _env(monkeypatch, tmp_path, inbox)

    uploaded: list[str] = []

    class _Recorder(_StubMainClient):
        def upload(self, path: Path) -> Result:
            uploaded.append(path.name)
            return Result(Outcome.OK, 1, "ok")

    _patch_client(monkeypatch, _Recorder(Result(Outcome.OK, 1, "ok")))
    assert main() == 0
    assert uploaded == [f"{stem}.tcx"]


def test_main_runs_adb_fallback_when_enabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    _env(monkeypatch, tmp_path, inbox)
    monkeypatch.delenv("ENDURAIN_NO_ADB")
    called: list[Path] = []
    import python_pkg.endurain_import.__main__ as mod

    def _record(path: Path) -> list[Path]:
        called.append(path)
        return []

    monkeypatch.setattr(mod, "pull_from_phone", _record)
    _patch_client(monkeypatch, _StubMainClient(Result(Outcome.OK, 1, "ok")))
    assert main() == 0
    assert called == [inbox]


def test_route_rejected_handles_unwritable_bulk_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A broken bulk_import must not take down the whole run."""
    path = tmp_path / "f.tcx"
    path.write_text("x")

    import shutil

    def _boom(*_a: object, **_k: object) -> None:
        message = "read-only filesystem"
        raise OSError(message)

    monkeypatch.setattr(shutil, "copy2", _boom)
    _route_rejected(path, tmp_path / "bulk")
    assert path.exists()


def test_main_handles_requests_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    import requests

    _env(monkeypatch, tmp_path, inbox)

    class _Failing(_StubMainClient):
        def about(self) -> dict[str, object]:
            message = "refused"
            raise requests.ConnectionError(message)

    _patch_client(monkeypatch, _Failing(Result(Outcome.OK, 1, "ok")))
    assert main() == 1
