"""Shared fixtures for the endurain_import orchestration tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from python_pkg.endurain_import.upload import Result


@pytest.fixture
def inbox(tmp_path: Path) -> Path:
    path = tmp_path / "inbox"
    path.mkdir()
    return path


def _file(inbox: Path, name: str = "RunnerUp_ts_Running.tcx") -> Path:
    path = inbox / name
    path.write_text("<xml/>")
    return path


class _StubMainClient:
    """Stands in for EndurainClient across a whole main() run."""

    def __init__(
        self,
        result: Result,
        *,
        reachable: bool = True,
        remote: list[datetime] | None = None,
    ) -> None:
        self._result = result
        self._reachable = reachable
        self._remote = remote
        self.uploads = 0

    def about(self) -> dict[str, object]:
        if not self._reachable:
            message = "connection refused"
            raise OSError(message)
        return {"version": "test"}

    def recent_start_times(self, _user_id: int) -> list[datetime] | None:
        return self._remote

    def upload(self, _path: Path) -> Result:
        self.uploads += 1
        return self._result


def _env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path, **extra: str
) -> None:
    monkeypatch.setenv("ENDURAIN_API_KEY", "k")
    monkeypatch.setenv("ENDURAIN_INBOX", str(inbox))
    monkeypatch.setenv("ENDURAIN_STATE", str(tmp_path / "state"))
    monkeypatch.setenv("ENDURAIN_NO_ADB", "1")
    for key, value in extra.items():
        monkeypatch.setenv(key, value)


def _patch_client(monkeypatch: pytest.MonkeyPatch, client: _StubMainClient) -> None:
    import python_pkg.endurain_import.__main__ as mod

    monkeypatch.setattr(mod, "EndurainClient", lambda *_a, **_k: client)
