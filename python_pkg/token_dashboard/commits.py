"""Find the commits each session made, from git rather than from tool output.

Measured 2026-10-17: of 601 recent commit commands only 35 printed a parseable
``[branch sha]`` line -- most run through ``finish_auto.sh`` with a tailed or
backgrounded output. So every commit command is stored with its time window
and repository, and the hashes come from ``git log`` instead:

* a commit whose hash a command printed belongs to that command's session;
* otherwise a commit carrying a ``Co-Authored-By: Claude`` trailer belongs to
  the commit command in the same repository whose window covers its commit
  time (from :data:`LEAD_S` before the call to :data:`TAIL_S` after its
  result -- a backgrounded finish_auto.sh commits after the call returns),
  the nearest one when several do.

Rows are only ever added, so a repository deleted later keeps its history.
"""

from __future__ import annotations

from collections import defaultdict
import re
from typing import TYPE_CHECKING

from python_pkg.token_dashboard import gitcmd

if TYPE_CHECKING:
    import sqlite3

LEAD_S = 60.0
TAIL_S = 1800.0
TRAILER = re.compile(r"^Co-Authored-By:\s*Claude", re.IGNORECASE | re.MULTILINE)
_FIELD, _RECORD = "\x1f", "\x1e"
_LOG_FIELDS = 3


def _git(repo: str, *args: str) -> str | None:
    """Run git in ``repo``; ``None`` on any failure."""
    return gitcmd.run(repo, *args)


def _toplevel(hint: str, cache: dict[str, str | None]) -> str | None:
    """The work tree containing ``hint``, cached per hint."""
    if hint not in cache:
        out = _git(hint, "rev-parse", "--show-toplevel") if hint else None
        cache[hint] = out.strip() if out else None
    return cache[hint]


def _log(repo: str, since: float) -> list[tuple[str, float, bool]]:
    """``(sha, commit time, has Claude trailer)`` on HEAD since ``since``."""
    out = _git(
        repo,
        "log",
        "HEAD",
        f"--since=@{int(since)}",
        f"--format=%H{_FIELD}%ct{_FIELD}%B{_RECORD}",
    )
    rows = []
    for record in (out or "").split(_RECORD):
        parts = record.strip("\n").split(_FIELD, 2)
        if len(parts) == _LOG_FIELDS:
            rows.append((parts[0], float(parts[1]), bool(TRAILER.search(parts[2]))))
    return rows


Command = tuple[str, int, float, float, str]  # key, prompt, start, end, sha


def _match(
    sha: str, ts: float, cmds: list[Command], *, trailer: bool
) -> Command | None:
    """The command that made this commit, if any."""
    for cmd in cmds:
        if cmd[4] and sha.startswith(cmd[4]):
            return cmd
    if not trailer:
        return None
    covering = [c for c in cmds if c[2] - LEAD_S <= ts <= max(c[2], c[3]) + TAIL_S]
    if not covering:
        return None
    return min(covering, key=lambda c: abs(ts - c[2]))


def discover(conn: sqlite3.Connection) -> int:
    """Attribute git commits to sessions; returns how many rows were added."""
    cache: dict[str, str | None] = {}
    by_repo: dict[str, list[Command]] = defaultdict(list)
    for key, prompt, start, end, sha, hint in conn.execute(
        "SELECT key, prompt_idx, ts, end_ts, sha, repo FROM commits"
    ):
        top = _toplevel(hint, cache)
        if top is not None:
            by_repo[top].append((key, prompt, start, end, sha))
    added = 0
    for repo, cmds in by_repo.items():
        since = min(c[2] for c in cmds) - LEAD_S
        for sha, ts, trailer in _log(repo, since):
            cmd = _match(sha, ts, cmds, trailer=trailer)
            if cmd is None:
                continue
            added += conn.execute(
                "INSERT OR IGNORE INTO session_commits VALUES (?,?,?,?,?)",
                (sha, repo, ts, cmd[0], cmd[1]),
            ).rowcount
    return added
