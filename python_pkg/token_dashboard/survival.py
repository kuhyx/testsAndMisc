"""Did a commit made in a session survive? Decided by git, never by a model.

Rule (fixed here, shown in the dashboard caption): a commit is judged once it
is :data:`WINDOW_DAYS` old, at the last commit of its repository's ``HEAD``
history that is no more than that old relative to it.

* ``reverted`` -- a commit inside the window says ``This reverts commit <sha>``.
* ``churned``  -- under :data:`KEEP_SHARE` of the lines it added (counted over
  its :data:`MAX_FILES` largest files) still blame to it.
* ``survived`` -- otherwise, including a commit that added no lines.
* ``pending``  -- younger than the window.
* ``unknown``  -- the repo or hash is gone, or the commit is not on ``HEAD``
  (rebased, squashed or on another branch): excluded from the ratio.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from python_pkg.token_dashboard import gitcmd

if TYPE_CHECKING:
    from collections.abc import Callable
    import sqlite3

WINDOW_DAYS = 14
WINDOW_S = WINDOW_DAYS * 86400
KEEP_SHARE = 0.5
MAX_FILES = 10
_NUMSTAT_FIELDS = 3
FINAL = frozenset({"survived", "churned", "reverted"})


@dataclass(frozen=True)
class Verdict:
    """The outcome for one commit."""

    verdict: str
    sha: str = ""
    ts: float = 0.0
    added: int = 0
    kept: int = 0


def judge(added: int, kept: int, *, reverted: bool) -> str:
    """Apply the survival rule to measured numbers."""
    if reverted:
        return "reverted"
    if added and kept < KEEP_SHARE * added:
        return "churned"
    return "survived"


def _git(repo: str, *args: str) -> str | None:
    """Run git in ``repo``; ``None`` on any failure."""
    return gitcmd.run(repo, *args)


def _added(repo: str, sha: str) -> list[tuple[int, str]]:
    """``(added lines, path)`` for the commit's largest text files."""
    out = _git(repo, "show", "--numstat", "--format=", sha) or ""
    rows = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == _NUMSTAT_FIELDS and parts[0].isdigit() and int(parts[0]):
            rows.append((int(parts[0]), parts[2]))
    return sorted(rows, reverse=True)[:MAX_FILES]


def _kept(repo: str, rev: str, sha: str, path: str) -> int:
    """Lines of ``path`` at ``rev`` that still blame to ``sha``."""
    out = _git(repo, "blame", "--porcelain", rev, "--", path) or ""
    prefix = sha + " "
    return sum(1 for line in out.splitlines() if line.startswith(prefix))


def evaluate(repo: str, sha: str, now: float) -> Verdict:
    """Judge one commit in one repository."""
    if not Path(repo).is_dir():
        return Verdict("unknown")
    full = (
        _git(repo, "rev-parse", "--verify", "-q", f"{sha}^{{commit}}") or ""
    ).strip()
    if not full:
        return Verdict("unknown")
    ts = float((_git(repo, "show", "-s", "--format=%ct", full) or "0").strip() or 0)
    if now - ts < WINDOW_S:
        return Verdict("pending", full, ts)
    if _git(repo, "merge-base", "--is-ancestor", full, "HEAD") is None:
        return Verdict("unknown", full, ts)
    until = f"@{int(ts + WINDOW_S)}"
    end = (_git(repo, "rev-list", "-1", f"--before={until}", "HEAD") or "").strip()
    log = _git(repo, "log", "--format=%B", f"--since=@{int(ts)}", f"--until={until}")
    reverted = f"This reverts commit {full}" in (log or "")
    files = _added(repo, full)
    added = sum(n for n, _ in files)
    kept = sum(_kept(repo, end or full, full, path) for _, path in files)
    return Verdict(judge(added, kept, reverted=reverted), full, ts, added, kept)


def update(
    conn: sqlite3.Connection, now: float, deadline: float, clock: Callable[[], float]
) -> bool:
    """Judge every session commit without a final verdict, within the deadline.

    Returns whether the backlog was cleared. A verdict once final is never
    recomputed, so the backlog is only commits that turned 14 days old.
    """
    rows = conn.execute(
        "SELECT c.sha, c.repo, c.ts FROM session_commits c LEFT JOIN"
        " commit_verdicts v ON v.sha = c.sha WHERE v.verdict IS NULL"
        " OR v.verdict = 'pending'"
    ).fetchall()
    for sha, repo, ts in rows:
        if now - ts < WINDOW_S:
            continue  # cannot be final yet; no git call needed
        if clock() > deadline:
            return False
        found = evaluate(repo, sha, now)
        conn.execute(
            "INSERT OR REPLACE INTO commit_verdicts VALUES (?,?,?,?,?,?)",
            (sha, repo, found.ts or ts, found.added, found.kept, found.verdict),
        )
    return True
