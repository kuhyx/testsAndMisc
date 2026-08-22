"""Enumerate every context surface that is billed on every turn.

The weekly audit kept missing surfaces — plugins and ``autoMode.environment``
were both found only because the user asked "nothing else?". The fix is that
the list of surfaces lives in code: a surface that is not measured shows up as
an explicit row with ``measured=False`` instead of silently not existing.

Sizes here are *estimates from disk*. Anything that can be A/B'd against a real
process start should be, via :mod:`python_pkg.token_audit.probe`; disk size and
measured prefix cost disagree (skill descriptions are summarised, MCP servers
contribute only tool names), and the measured number is the one to trust.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
GLOBAL_CONFIG = Path.home() / ".claude.json"
SETTINGS = CLAUDE_DIR / "settings.json"
# Anthropic's rough byte-to-token ratio for English prose.
BYTES_PER_TOKEN = 4


@dataclass(frozen=True)
class Surface:
    """One always-loaded context component."""

    name: str
    detail: str
    bytes_on_disk: int
    measurable: bool = False

    @property
    def est_tokens(self) -> int:
        """Disk size converted to an approximate token count."""
        return self.bytes_on_disk // BYTES_PER_TOKEN


def _tree_bytes(root: Path, pattern: str = "*.md") -> int:
    """Total size of every file under *root* matching *pattern*."""
    if not root.is_dir():
        return 0
    return sum(p.stat().st_size for p in root.rglob(pattern) if p.is_file())


def _json_field_bytes(path: Path, field: str) -> int:
    """Serialized size of one top-level field, or 0 when absent."""
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return 0
    if field not in data:
        return 0
    return len(json.dumps(data[field]))


def _skill_description_bytes() -> int:
    """Approximate the frontmatter that every skill contributes."""
    total = 0
    for skill in (CLAUDE_DIR / "skills").glob("*/SKILL.md"):
        head = skill.read_text(errors="replace")[:4000]
        _, _, rest = head.partition("description:")
        total += len(rest.split("\n---", 1)[0]) if rest else 0
    return total


def _mcp_names(path: Path, field: str = "mcpServers") -> list[str]:
    """Server names registered in a config file."""
    if not path.exists():
        return []
    try:
        return sorted(json.loads(path.read_text()).get(field, {}))
    except (json.JSONDecodeError, OSError):
        return []


def _enabled_plugins() -> list[str]:
    """Plugins switched on in settings.json."""
    if not SETTINGS.exists():
        return []
    try:
        plugins = json.loads(SETTINGS.read_text()).get("enabledPlugins", {})
    except (json.JSONDecodeError, OSError):
        return []
    return sorted(name for name, on in plugins.items() if on)


def _project_mcp_files() -> list[Path]:
    """Project-scoped .mcp.json files under the home directory.

    These are invisible to ``--strict-mcp-config``, which is exactly how an
    earlier audit under-measured the real baseline by ~2,000 tokens/turn.
    """
    return sorted(p for p in Path.home().glob("*/.mcp.json") if p.is_file())


def collect() -> list[Surface]:
    """Enumerate every known billed surface.

    Adding a surface here is what makes it appear in the report; the weekly
    check walks this list rather than a human's memory of it.
    """
    memory_dir = CLAUDE_DIR / "projects" / "-home-kuhy" / "memory"
    plugins = _enabled_plugins()
    project_mcp = _project_mcp_files()
    global_mcp = _mcp_names(GLOBAL_CONFIG)
    parked = _mcp_names(CLAUDE_DIR / "mcp-parked.json")
    return [
        Surface(
            "rules/",
            "always-on, loaded recursively",
            _tree_bytes(CLAUDE_DIR / "rules"),
        ),
        Surface("memories/", "always-on", _tree_bytes(CLAUDE_DIR / "memories")),
        Surface(
            "CLAUDE.md",
            "global instructions",
            (CLAUDE_DIR / "CLAUDE.md").stat().st_size
            if (CLAUDE_DIR / "CLAUDE.md").exists()
            else 0,
        ),
        Surface(
            "MEMORY.md",
            "auto-memory index",
            (memory_dir / "MEMORY.md").stat().st_size
            if (memory_dir / "MEMORY.md").exists()
            else 0,
        ),
        Surface(
            "skill descriptions",
            f"{len(list((CLAUDE_DIR / 'skills').glob('*/SKILL.md')))} personal skills",
            _skill_description_bytes(),
        ),
        Surface("plugins", ", ".join(plugins) or "none", 0, measurable=True),
        Surface(
            "global MCP",
            f"{len(global_mcp)} active, {len(parked)} parked",
            0,
            measurable=True,
        ),
        Surface(
            "project .mcp.json",
            f"{len(project_mcp)} repos (per-project only)",
            0,
            measurable=True,
        ),
        Surface(
            "autoMode.environment",
            "injected in auto mode",
            _json_field_bytes(SETTINGS, "autoMode"),
        ),
    ]
