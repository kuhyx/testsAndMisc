"""The phone fallback skips what the importer already has, and says so.

RunnerUp never deletes its exports, so the phone lists every run ever
recorded. Each one is either waiting in the inbox, already imported into
``processed/``, or genuinely new; only the last kind may be pulled.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from python_pkg.endurain_import import sources


def test_processed_dir_for_is_the_inbox_processed_subdir(tmp_path: Path) -> None:
    """Importer and phone fallback agree on one location for imported files."""
    assert sources.processed_dir_for(tmp_path) == tmp_path / "processed"
    assert sources.processed_dir_for(tmp_path).name == sources.PROCESSED_DIRNAME


def _phone_listing(
    names: list[str], *, failing: frozenset[str] = frozenset()
) -> tuple[list[str], object]:
    """Fake ``_adb`` serving ``names`` and recording every pull it is asked for.

    Pulls of a name in ``failing`` report an adb error; the rest succeed.
    """
    pulls: list[str] = []

    def _adb(args: list[str], _serial: str | None = None) -> tuple[bool, str]:
        if args[0] == "shell":
            return True, "".join(f"{n}\n" for n in names)
        name = args[1].rsplit("/", 1)[-1]
        pulls.append(name)
        if name in failing:
            return False, "remote object does not exist"
        Path(args[2]).write_text("pulled")
        return True, ""

    return pulls, _adb


def test_pull_skips_files_already_imported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The phone keeps every export; imported ones must not be pulled back."""
    monkeypatch.setattr(sources, "resolve_serial", lambda: "ABC123")
    pulls, fake = _phone_listing(["old.tcx", "new.tcx"])
    monkeypatch.setattr(sources, "_adb", fake)
    processed = sources.processed_dir_for(tmp_path)
    processed.mkdir()
    (processed / "old.tcx").write_text("imported last week")

    pulled = sources.pull_from_phone(tmp_path)

    assert [p.name for p in pulled] == ["new.tcx"]
    assert pulls == ["new.tcx"]
    assert not (tmp_path / "old.tcx").exists()
    assert (processed / "old.tcx").read_text() == "imported last week"


def test_pull_does_not_re_pull_a_file_waiting_in_the_inbox(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sources, "resolve_serial", lambda: "ABC123")
    pulls, fake = _phone_listing(["waiting.tcx"])
    monkeypatch.setattr(sources, "_adb", fake)
    (tmp_path / "waiting.tcx").write_text("local copy")

    assert sources.pull_from_phone(tmp_path) == []
    assert pulls == []
    assert (tmp_path / "waiting.tcx").read_text() == "local copy"


def test_pull_summary_counts_every_outcome_at_info(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(sources, "resolve_serial", lambda: "ABC123")
    _, fake = _phone_listing(["a.tcx", "b.tcx", "c.tcx", "notes.txt"])
    monkeypatch.setattr(sources, "_adb", fake)
    processed = sources.processed_dir_for(tmp_path)
    processed.mkdir()
    (processed / "a.tcx").write_text("x")
    (tmp_path / "b.tcx").write_text("x")

    with caplog.at_level("INFO", logger=sources.__name__):
        sources.pull_from_phone(tmp_path)

    summaries = [r for r in caplog.records if "phone fallback" in r.getMessage()]
    assert len(summaries) == 1
    assert summaries[0].levelname == "INFO"
    assert summaries[0].getMessage() == (
        "phone fallback: 3 on phone, 1 pulled, 1 skipped as already imported, "
        "1 skipped as already in the inbox, 0 failed"
    )


def test_pull_summary_escalates_to_warning_on_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A partially broken fallback must be visible in the one summary line."""
    monkeypatch.setattr(sources, "resolve_serial", lambda: "ABC123")
    _, fake = _phone_listing(["ok.tcx", "bad.tcx"], failing=frozenset({"bad.tcx"}))
    monkeypatch.setattr(sources, "_adb", fake)

    with caplog.at_level("INFO", logger=sources.__name__):
        pulled = sources.pull_from_phone(tmp_path)

    assert [p.name for p in pulled] == ["ok.tcx"]
    summaries = [r for r in caplog.records if "phone fallback" in r.getMessage()]
    assert len(summaries) == 1
    assert summaries[0].levelname == "WARNING"
    assert (
        summaries[0]
        .getMessage()
        .endswith(
            "1 pulled, 0 skipped as already imported, "
            "0 skipped as already in the inbox, 1 failed"
        )
    )
