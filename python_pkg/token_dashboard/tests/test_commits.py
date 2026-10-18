from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.token_dashboard import commits, schema
from python_pkg.token_dashboard.tests.test_efficiency import MONDAY, _commit, _git

if TYPE_CHECKING:
    from pathlib import Path

TRAILER = "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"


def test_git_log_attributes_trailer_commits_to_the_commit_command(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", when=MONDAY)
    (repo / "a").write_text("1")
    _git(repo, "add", "a", when=MONDAY)
    _git(repo, "commit", "-qm", "ours" + TRAILER, when=MONDAY + 30)
    ours = _git(repo, "rev-parse", "HEAD", when=MONDAY)
    _commit(repo, "b", "2", MONDAY + 40)  # no trailer: a human commit
    _git(
        repo,
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "late" + TRAILER,
        when=MONDAY + 9000,
    )
    conn = schema.connect(tmp_path / "t.sqlite")
    rows = [
        ("s1", 0, MONDAY, MONDAY + 60, "", str(repo)),
        ("s2", 3, MONDAY - 5000, MONDAY - 4000, "", str(repo / "sub")),
        ("s3", 1, MONDAY, MONDAY + 1, "", str(tmp_path / "missing")),
    ]
    conn.executemany("INSERT INTO commits VALUES (?,?,?,?,?,?)", rows)
    commits.discover(conn)
    found = conn.execute("SELECT sha, key, prompt_idx FROM session_commits").fetchall()
    conn.close()
    assert found == [(ours, "s1", 0)]


def test_a_printed_hash_is_attributed_even_without_trailer(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", when=MONDAY)
    sha = _commit(repo, "a", "1", MONDAY + 5)
    conn = schema.connect(tmp_path / "t.sqlite")
    conn.execute(
        "INSERT INTO commits VALUES (?,?,?,?,?,?)",
        ("s1", 2, MONDAY, MONDAY + 9, sha[:7], str(repo)),
    )
    commits.discover(conn)
    commits.discover(conn)  # idempotent
    found = conn.execute("SELECT sha, key FROM session_commits").fetchall()
    conn.close()
    assert found == [(sha, "s1")]
