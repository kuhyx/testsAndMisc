"""Find registered surfaces that nothing has called, using two time windows.

A single seven-day window is not enough evidence to unregister anything: one
audit's seven-day "dead" list included six servers that had been used within
thirty days. A surface therefore qualifies as dead only when it is unused in
the short window *and* the long one.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
import time

TRANSCRIPT_ROOT = Path.home() / ".claude" / "projects"
SECONDS_PER_DAY = 86400
SHORT_WINDOW_DAYS = 7
LONG_WINDOW_DAYS = 30
_MCP_CALL = re.compile(r'"name":"mcp__([a-zA-Z0-9_-]+)__')
_SKILL_CALL = re.compile(r'"skill":"([^"]+)"')


@dataclass(frozen=True)
class Usage:
    """Call counts for one surface across both windows."""

    name: str
    short_calls: int
    long_calls: int

    @property
    def dead(self) -> bool:
        """True when unused in both windows, so it is safe to park."""
        return self.short_calls == 0 and self.long_calls == 0


def _scan(pattern: re.Pattern[str], since: float) -> Counter[str]:
    """Count regex matches across transcripts modified after *since*."""
    found: Counter[str] = Counter()
    for path in TRANSCRIPT_ROOT.glob("*/*.jsonl"):
        try:
            if path.stat().st_mtime < since:
                continue
            text = path.read_text(errors="replace")
        except OSError:
            continue
        found.update(pattern.findall(text))
    return found


def usage_for(
    names: list[str], pattern: re.Pattern[str], now: float | None = None
) -> list[Usage]:
    """Report short- and long-window call counts for each of *names*."""
    now = time.time() if now is None else now
    short = _scan(pattern, now - SHORT_WINDOW_DAYS * SECONDS_PER_DAY)
    long_ = _scan(pattern, now - LONG_WINDOW_DAYS * SECONDS_PER_DAY)
    return [Usage(n, short.get(n, 0), long_.get(n, 0)) for n in sorted(names)]


def mcp_usage(config: Path | None = None) -> list[Usage]:
    """Call counts for every globally registered MCP server."""
    config = config or Path.home() / ".claude.json"
    try:
        names = list(json.loads(config.read_text()).get("mcpServers", {}))
    except json.JSONDecodeError, OSError:
        return []
    return usage_for(names, _MCP_CALL)


def skill_usage() -> list[Usage]:
    """Invocation counts for every personal skill."""
    root = Path.home() / ".claude" / "skills"
    names = [p.parent.name for p in root.glob("*/SKILL.md")]
    return usage_for(names, _SKILL_CALL)
