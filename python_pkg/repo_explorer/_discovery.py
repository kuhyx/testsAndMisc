"""Project discovery helpers and shared constants for Repo Explorer."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
from typing import cast

# Strip ANSI/VT100 escape sequences so the Text widget shows plain text
_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


def _find_terminal() -> list[str]:
    """Return argv prefix for the first available terminal emulator."""
    candidates = [
        ("kitty", ["kitty", "--"]),
        ("alacritty", ["alacritty", "-e"]),
        ("konsole", ["konsole", "-e"]),
        ("gnome-terminal", ["gnome-terminal", "--"]),
        ("xfce4-terminal", ["xfce4-terminal", "-x"]),
        ("xterm", ["xterm", "-e"]),
    ]
    for exe, args in candidates:
        if shutil.which(exe):
            return args
    return []


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "build",
    "target",
    ".mypy_cache",
    ".ruff_cache",
}


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def find_projects(root: Path) -> list[dict[str, object]]:
    """Return every directory under *root* that contains a run.sh."""
    projects: list[dict[str, object]] = []
    for run_sh in sorted(root.rglob("run.sh")):
        if _is_ignored(run_sh):
            continue
        proj_dir = run_sh.parent
        rel = proj_dir.relative_to(root)
        projects.append({"path": proj_dir, "rel": rel, "name": proj_dir.name})
    return projects


def _desc_from_run_sh(run_sh: Path) -> str:
    """Extract leading comment block from run.sh as a description."""
    comments: list[str] = []
    for line in run_sh.read_text(errors="replace").splitlines():
        s = line.strip()
        if s.startswith("#!"):
            continue
        if s.startswith("#"):
            comments.append(s[1:].strip())
        elif comments:
            break
    return " ".join(comments)[:300] if comments else ""


def get_description(project_path: Path) -> str:
    """Return a short description from README.md or leading run.sh comments."""
    for readme_name in ("README.md", "README.txt", "readme.md"):
        readme = project_path / readme_name
        if readme.exists():
            text = readme.read_text(errors="replace")
            for line in text.splitlines():
                stripped = line.strip().lstrip("#").strip()
                if stripped:
                    return cast("str", stripped[:300])

    run_sh = project_path / "run.sh"
    if run_sh.exists():
        desc = _desc_from_run_sh(run_sh)
        if desc:
            return desc

    return "(no description)"
