"""Which files enter Claude's context, and how big each has been over time.

:func:`find` lists them per file (token_audit's :mod:`surfaces` sums them per
surface, which cannot say which rule grew). Only the list and the size history
are stored -- the dashboard reads each file live when asked, so it never shows
a stale copy.

Size history comes from two places, both cheap: ``~/.claude``'s own git
history (one ``git log --raw`` plus one ``git cat-file --batch-check`` for
every blob, incremental from the last commit seen) and the weekly prune's
``prune/<date>/sizes*.json`` snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING

from python_pkg.token_audit import pricing
from python_pkg.token_audit.surfaces import CLAUDE_DIR
from python_pkg.token_dashboard import gitcmd

if TYPE_CHECKING:
    import sqlite3

SRC_DIR = Path.home() / "src"
MEMORY_LIMIT = 24_400  # MEMORY.md is only read up to ~24.4 KB
CLAUDE_MD_LIMIT = 40_000  # Claude Code warns about a CLAUDE.md over 40k chars
DESCRIPTION_LIMIT = 1024  # a skill description's maximum length
_BATCH_FIELDS = 3  # cat-file --batch-check: <sha> <type> <size>


@dataclass(frozen=True)
class ContextFile:
    """One file and how it reaches the context."""

    path: str
    kind: str
    standing: str  # always | in repo | description
    limit: int | None


def find(claude: Path | None = None, src: Path | None = None) -> list[ContextFile]:
    """Every context file on disk (on-demand backups excluded)."""
    claude = claude or CLAUDE_DIR
    src = src or SRC_DIR
    out = [
        ContextFile(
            str(claude / "CLAUDE.md"), "global CLAUDE.md", "always", CLAUDE_MD_LIMIT
        )
    ]
    groups = (
        ("memories", "*.md", "memories (@-imported)", "always", None),
        ("rules", "**/*.md", "rules (loaded recursively)", "always", None),
        ("skills", "*/SKILL.md", "skill", "description", DESCRIPTION_LIMIT),
        ("agents", "*.md", "agent definition", "description", DESCRIPTION_LIMIT),
        ("output-styles", "*.md", "output style", "always", None),
    )
    for folder, pattern, kind, standing, limit in groups:
        out += [
            ContextFile(str(p), kind, standing, limit)
            for p in sorted((claude / folder).glob(pattern))
            if p.is_file()
        ]
    memory = claude / "projects" / "-home-kuhy" / "memory" / "MEMORY.md"
    out.append(ContextFile(str(memory), "auto-memory index", "always", MEMORY_LIMIT))
    for name in ("CLAUDE.md", "AGENTS.md"):
        out += [
            ContextFile(str(p), f"repo {name}", "in repo", CLAUDE_MD_LIMIT)
            for p in sorted(src.glob(f"*/{name}"))
        ]
    return [f for f in out if Path(f.path).is_file()]


def _git(repo: Path, *args: str, stdin: str | None = None) -> str:
    """Run git, returning stdout ('' on failure)."""
    return gitcmd.run(repo, *args, stdin=stdin) or ""


def _git_sizes(claude: Path, since: str) -> tuple[list[tuple[str, float, str]], str]:
    """``(relpath, commit time, blob)`` for commits after ``since``; new head."""
    head = _git(claude, "rev-parse", "HEAD").strip()
    if not head or head == since:
        return [], since
    span = f"{since}..HEAD" if since else "HEAD"
    out = _git(claude, "log", "--raw", "--no-abbrev", "--format=@%ct", span)
    rows: list[tuple[str, float, str]] = []
    stamp = 0.0
    for line in out.splitlines():
        if line.startswith("@"):
            stamp = float(line[1:])
        elif line.startswith(":") and line.endswith(".md"):
            meta, _, rel = line.partition("\t")
            blob = meta.split()[3]
            rows.append((rel, stamp, blob))
    return rows, head


def refresh(
    conn: sqlite3.Connection, claude: Path | None = None, src: Path | None = None
) -> None:
    """Re-list context files and append any new size-history points."""
    claude = claude or CLAUDE_DIR
    files = find(claude, src)
    conn.execute("DELETE FROM context_files")
    conn.executemany(
        "INSERT INTO context_files VALUES (?,?,?,?)",
        [(f.path, f.kind, f.standing, f.limit) for f in files],
    )
    row = conn.execute("SELECT value FROM meta WHERE key='context_git_head'").fetchone()
    rows, head = _git_sizes(claude, row[0] if row else "")
    zero = "0" * 40
    blobs = sorted({b for _, _, b in rows if b != zero})
    sizes: dict[str, int] = {}
    batch = _git(claude, "cat-file", "--batch-check", stdin="\n".join(blobs) + "\n")
    for line in batch.splitlines():
        parts = line.split()
        if len(parts) == _BATCH_FIELDS and parts[2].isdigit():
            sizes[parts[0]] = int(parts[2])
    conn.executemany(
        "INSERT OR IGNORE INTO context_sizes VALUES (?,?,?,?)",
        [(str(claude / rel), ts, sizes.get(b, 0), "git") for rel, ts, b in rows],
    )
    conn.execute("INSERT OR REPLACE INTO meta VALUES ('context_git_head', ?)", (head,))
    for path in sorted((claude / "token-report" / "prune").glob("*/sizes*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8")).get("file_bytes", {})
        except ValueError, OSError, AttributeError:
            continue
        stamp = path.stat().st_mtime
        conn.executemany(
            "INSERT OR IGNORE INTO context_sizes VALUES (?,?,?,?)",
            [
                (str(claude / rel), stamp, size, f"prune {path.parent.name}")
                for rel, size in data.items()
                if isinstance(size, int)
            ],
        )


def price_mix(conn: sqlite3.Connection, now: float, days: float = 7.0) -> float:
    """Call-weighted cache-read USD/MTok over the last ``days``, into ``meta``.

    A standing file costs its tokens x calls/day x this price: every call
    re-reads the whole prefix from cache.
    """
    book = pricing.load()
    rows = conn.execute(
        "SELECT model, COUNT(*) FROM turns WHERE ts > ? GROUP BY model",
        (now - days * 86400,),
    ).fetchall()
    calls = sum(n for _, n in rows)
    price = (
        sum(book.for_model(m).cache_read * n for m, n in rows) / calls if calls else 0.0
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta VALUES ('cache_read_usd_per_mtok', ?)",
        (str(price),),
    )
    return price
