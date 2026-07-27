"""Tests for verdict planning and the one module that moves files."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import files, verdict
from python_pkg.wsg_grabber.models import FileMove, ReviewItem, Verdict
from python_pkg.wsg_grabber.states import FileState

if TYPE_CHECKING:
    from pathlib import Path


def _item(path: Path) -> ReviewItem:
    """Build a ReviewItem pointing at *path*.

    Args:
        path: Location of the video.

    Returns:
        ReviewItem: Fixture value.
    """
    return ReviewItem(
        md5="md5",
        path=path,
        orig_name="clip.webm",
        fsize=10,
        width=4,
        height=3,
    )


def test_verdicts_map_to_terminal_states() -> None:
    assert verdict.target_state(Verdict.KEEP) is FileState.KEPT
    assert verdict.target_state(Verdict.SKIP) is FileState.PASSED


def test_verdicts_map_to_directories(tmp_path: Path) -> None:
    keep, trash = tmp_path / "keep", tmp_path / "trash"
    assert verdict.target_dir(Verdict.KEEP, keep, trash) == keep
    assert verdict.target_dir(Verdict.SKIP, keep, trash) == trash


def test_unique_destination_passes_through_when_free(tmp_path: Path) -> None:
    assert verdict.unique_destination(tmp_path, "a.webm", set()) == tmp_path / "a.webm"


def test_unique_destination_suffixes_a_collision(tmp_path: Path) -> None:
    result = verdict.unique_destination(tmp_path, "a.webm", {"a.webm"})
    assert result == tmp_path / "a-2.webm"


def test_unique_destination_keeps_counting(tmp_path: Path) -> None:
    taken = {"a.webm", "a-2.webm", "a-3.webm"}
    assert (
        verdict.unique_destination(tmp_path, "a.webm", taken) == tmp_path / "a-4.webm"
    )


def test_unique_destination_handles_a_name_without_an_extension(
    tmp_path: Path,
) -> None:
    assert verdict.unique_destination(tmp_path, "a", {"a"}) == tmp_path / "a-2"


def test_plan_move_sends_a_keep_to_the_keep_directory(tmp_path: Path) -> None:
    keep, trash = tmp_path / "keep", tmp_path / "trash"
    move = verdict.plan_move(
        _item(tmp_path / "in" / "x.webm"), Verdict.KEEP, keep, trash
    )
    assert move.dst == keep / "x.webm"
    assert move.src == tmp_path / "in" / "x.webm"
    assert move.md5 == "md5"


def test_plan_move_sends_a_pass_to_the_trash_directory(tmp_path: Path) -> None:
    keep, trash = tmp_path / "keep", tmp_path / "trash"
    move = verdict.plan_move(
        _item(tmp_path / "in" / "x.webm"), Verdict.SKIP, keep, trash
    )
    assert move.dst == trash / "x.webm"


def test_apply_move_relocates_rather_than_deleting(tmp_path: Path) -> None:
    """A pass must never destroy the file; trash is a destination, not a bin."""
    source = tmp_path / "in" / "x.webm"
    source.parent.mkdir()
    source.write_bytes(b"data")
    move = FileMove(md5="md5", src=source, dst=tmp_path / "trash" / "x.webm")

    assert files.apply_move(move)
    assert not source.exists()
    assert move.dst.read_bytes() == b"data"


def test_apply_move_reports_a_source_that_has_vanished(tmp_path: Path) -> None:
    move = FileMove(md5="md5", src=tmp_path / "gone.webm", dst=tmp_path / "t.webm")
    assert not files.apply_move(move)


def test_existing_names_lists_the_directory(tmp_path: Path) -> None:
    # a subdirectory, because the isolation fixture puts a fake home in tmp_path
    keep = tmp_path / "keep"
    keep.mkdir()
    (keep / "a.webm").write_bytes(b"")
    (keep / "b.webm").write_bytes(b"")
    assert files.existing_names(keep) == {"a.webm", "b.webm"}


def test_existing_names_of_a_missing_directory_is_empty(tmp_path: Path) -> None:
    assert files.existing_names(tmp_path / "nope") == set()


def test_apply_move_refuses_to_clobber_the_destination(tmp_path: Path) -> None:
    """The structural backstop: no move may ever destroy an existing file."""
    source = tmp_path / "in" / "x.webm"
    source.parent.mkdir()
    source.write_bytes(b"new")
    victim = tmp_path / "keep" / "x.webm"
    victim.parent.mkdir()
    victim.write_bytes(b"ALREADY HERE")

    assert not files.apply_move(FileMove(md5="m", src=source, dst=victim))
    assert victim.read_bytes() == b"ALREADY HERE"
    assert source.read_bytes() == b"new"
