"""Skipping runs Endurain already holds.

RunnerUp's own uploader writes straight to the server and leaves no ledger
trace, so the server is the only place these runs are visible.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from python_pkg.endurain_import.__main__ import main
from python_pkg.endurain_import.tests.conftest import (
    _env,
    _file,
    _patch_client,
    _StubMainClient,
)
from python_pkg.endurain_import.upload import Outcome, Result

# The name encodes 23:51:04 LOCAL time; the UTC instant depends on the zone,
# so these derive it the same way production does rather than hardcoding it.
_RUN_NAME = "RunnerUp_2026-08-22-23-51-04_Running.tcx"


def _run_start() -> datetime:
    return datetime(
        2026, 8, 22, 23, 51, 4, tzinfo=datetime.now().astimezone().tzinfo
    ).astimezone(timezone.utc)


def test_run_already_in_endurain_is_skipped_not_reuploaded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    """RunnerUp's own uploader leaves no ledger trace; only the server knows."""
    _env(monkeypatch, tmp_path, inbox)
    _file(inbox, _RUN_NAME)
    client = _StubMainClient(Result(Outcome.OK, 1, "ok"), remote=[_run_start()])
    _patch_client(monkeypatch, client)
    assert main() == 0
    assert client.uploads == 0
    assert (inbox / "processed" / _RUN_NAME).exists()


def test_remote_skip_is_recorded_so_the_next_run_needs_no_query(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    _env(monkeypatch, tmp_path, inbox)
    _file(inbox, _RUN_NAME)
    _patch_client(
        monkeypatch,
        _StubMainClient(Result(Outcome.OK, 1, "ok"), remote=[_run_start()]),
    )
    assert main() == 0
    assert _RUN_NAME in (tmp_path / "state" / "ledger.json").read_text()


def test_a_genuinely_new_run_still_uploads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    """The remote check must not become a blanket refusal to upload."""
    _env(monkeypatch, tmp_path, inbox)
    _file(inbox, _RUN_NAME)
    other = datetime(2026, 1, 1, tzinfo=timezone.utc)
    client = _StubMainClient(Result(Outcome.OK, 7, "ok"), remote=[other])
    _patch_client(monkeypatch, client)
    assert main() == 0
    assert client.uploads == 1


def test_unavailable_query_falls_back_to_the_ledger(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    """A failed lookup must not read as 'nothing exists' -- nor block imports."""
    _env(monkeypatch, tmp_path, inbox)
    _file(inbox, _RUN_NAME)
    client = _StubMainClient(Result(Outcome.OK, 1, "ok"), remote=None)
    _patch_client(monkeypatch, client)
    assert main() == 0
    assert client.uploads == 1


def test_unparseable_filename_falls_back_to_the_ledger(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    """No timestamp in the name means the remote check cannot apply."""
    _env(monkeypatch, tmp_path, inbox)
    _file(inbox, "mystery.tcx")
    client = _StubMainClient(Result(Outcome.OK, 1, "ok"), remote=[_run_start()])
    _patch_client(monkeypatch, client)
    assert main() == 0
    assert client.uploads == 1


def test_user_id_is_configurable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, inbox: Path
) -> None:
    _env(monkeypatch, tmp_path, inbox, ENDURAIN_USER_ID="7")
    _file(inbox, _RUN_NAME)
    seen: list[int] = []

    class _Recording(_StubMainClient):
        def recent_start_times(self, user_id: int) -> list[datetime] | None:
            seen.append(user_id)
            return []

    _patch_client(monkeypatch, _Recording(Result(Outcome.OK, 1, "ok")))
    assert main() == 0
    assert seen == [7]
