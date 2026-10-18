"""Git-backed edge cases: caching, binary files, commits outside HEAD."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.token_dashboard import commits, survival
from python_pkg.token_dashboard.tests.test_efficiency import DAY, MONDAY, _commit, _git

if TYPE_CHECKING:
    from pathlib import Path


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", when=MONDAY)
    return repo


def test_toplevel_is_resolved_once_per_hint(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, "a", "1", MONDAY)
    cache: dict[str, str | None] = {}
    first = commits._toplevel(str(repo), cache)
    assert first == str(repo.resolve())
    cache[str(repo)] = "cached"
    assert commits._toplevel(str(repo), cache) == "cached"
    assert commits._toplevel("", cache) is None


def test_binary_and_empty_files_do_not_count_as_added_lines(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    old = MONDAY - 40 * DAY
    (repo / "blob.bin").write_bytes(b"\x00\x01\x02")
    (repo / "empty.txt").write_text("", encoding="utf-8")
    (repo / "t.txt").write_text("1\n2\n", encoding="utf-8")
    _git(repo, "add", ".", when=old)
    _git(repo, "commit", "-qm", "mixed", when=old)
    sha = _git(repo, "rev-parse", "HEAD", when=old)
    found = survival.evaluate(str(repo), sha, MONDAY)
    assert (found.verdict, found.added, found.kept) == ("survived", 2, 2)


def test_a_commit_that_is_not_an_ancestor_of_head_is_unknown(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    old = MONDAY - 40 * DAY
    _commit(repo, "a", "1", old)
    trunk = _git(repo, "branch", "--show-current", when=old)
    _git(repo, "checkout", "-qb", "side", when=old)
    side = _commit(repo, "b", "2", old + 1)
    _git(repo, "checkout", "-q", trunk, when=old)
    found = survival.evaluate(str(repo), side, MONDAY)
    assert (found.verdict, found.sha) == ("unknown", side)
