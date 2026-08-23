"""Orchestration: routing, fail-closed behaviour and exit status."""

from __future__ import annotations

from pathlib import Path

import pytest

from python_pkg.endurain_import.__main__ import _process, _route_rejected, main
from python_pkg.endurain_import.ledger import Entry, Ledger, now_iso
from python_pkg.endurain_import.upload import Outcome, Result


class _StubClient:
    def __init__(self, result: Result) -> None:
        self._result = result
        self.uploads: list[Path] = []

    def upload(self, path: Path) -> Result:
        self.uploads.append(path)
        return self._result


@pytest.fixture
def inbox(tmp_path: Path) -> Path:
    path = tmp_path / "inbox"
    path.mkdir()
    return path


def _file(inbox: Path, name: str = "RunnerUp_ts_Running.tcx") -> Path:
    path = inbox / name
    path.write_text("<xml/>")
    return path


def test_success_moves_to_processed_and_records(tmp_path: Path, inbox: Path) -> None:
    path = _file(inbox)
    ledger = Ledger(tmp_path / "l.json")
    client = _StubClient(Result(Outcome.OK, 5, "ok"))
    processed = inbox / "processed"

    assert _process(path, client, ledger, processed, None) == "imported"
    assert (processed / path.name).exists()
    assert not path.exists()
    assert len(ledger) == 1


def test_known_digest_is_skipped_without_uploading(tmp_path: Path, inbox: Path) -> None:
    path = _file(inbox)
    ledger = Ledger(tmp_path / "l.json")
    from python_pkg.endurain_import.ledger import activity_key, file_digest

    ledger.record(Entry(file_digest(path), activity_key(path), path.name, 1, now_iso()))
    client = _StubClient(Result(Outcome.OK, 9, "ok"))

    assert _process(path, client, ledger, inbox / "processed", None) == "skipped"
    assert client.uploads == []


def test_same_run_other_format_is_skipped(tmp_path: Path, inbox: Path) -> None:
    """The .gpx twin of an imported .tcx must not create a second activity."""
    tcx = _file(inbox, "RunnerUp_2026-08-22-23-51-04_Running.tcx")
    ledger = Ledger(tmp_path / "l.json")
    from python_pkg.endurain_import.ledger import activity_key, file_digest

    ledger.record(Entry(file_digest(tcx), activity_key(tcx), tcx.name, 1, now_iso()))

    gpx = inbox / "RunnerUp_2026-08-22-23-51-04_Running.gpx"
    gpx.write_text("<gpx/>")  # different bytes, same run
    client = _StubClient(Result(Outcome.OK, 9, "ok"))

    assert _process(gpx, client, ledger, inbox / "processed", None) == "skipped"
    assert client.uploads == []


def test_rejected_file_is_staged_and_left_in_place(tmp_path: Path, inbox: Path) -> None:
    path = _file(inbox)
    bulk = tmp_path / "bulk"
    ledger = Ledger(tmp_path / "l.json")
    client = _StubClient(Result(Outcome.REJECTED, None, "400"))

    assert _process(path, client, ledger, inbox / "processed", bulk) == "rejected"
    assert (bulk / path.name).exists()
    assert path.exists(), "a rejected file must stay for inspection"
    assert len(ledger) == 0


def test_ambiguous_never_stages_to_bulk_import(tmp_path: Path, inbox: Path) -> None:
    """The whole point of the ambiguous class: do not risk a duplicate."""
    path = _file(inbox)
    bulk = tmp_path / "bulk"
    ledger = Ledger(tmp_path / "l.json")
    client = _StubClient(Result(Outcome.AMBIGUOUS, None, "timeout"))

    assert _process(path, client, ledger, inbox / "processed", bulk) == "ambiguous"
    assert not bulk.exists(), "ambiguous uploads must not be re-queued"
    assert path.exists()
    assert len(ledger) == 0


def test_route_rejected_without_bulk_dir_is_safe(tmp_path: Path) -> None:
    path = tmp_path / "f.tcx"
    path.write_text("x")
    _route_rejected(path, None)
    assert path.exists()


def test_missing_api_key_exits_two(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENDURAIN_API_KEY", raising=False)
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
