"""Find VS Code installations and read and write their configuration.

Settings are JSON with Comments, which the stdlib cannot parse, so this
module carries a small JSONC reader. Every write is preceded by a backup.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
import shutil

from python_pkg.vscode_optimizer._types import _Opt, _Variant


def _discover_variants() -> list[_Variant]:
    """Find all installed VS Code variants."""
    cfg = Path.home() / ".config"
    cands = [
        ("VS Code (stable)", "Code", "code-flags.conf", "code"),
        (
            "VS Code Insiders",
            "Code - Insiders",
            "code-insiders-flags.conf",
            "code-insiders",
        ),
        ("VSCodium", "VSCodium", "vscodium-flags.conf", "codium"),
    ]
    found: list[_Variant] = []
    for name, dir_name, flags_name, binary in cands:
        sp = cfg / dir_name / "User" / "settings.json"
        fp = cfg / flags_name
        if sp.exists() or shutil.which(binary):
            found.append(_Variant(name, sp, fp, binary))
    return found


def _parse_jsonc(text: str) -> dict[str, object]:
    """Parse JSON with Comments (JSONC) used by VS Code."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            out.append(text[i:j])
            i = j
        elif ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif ch == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            i = end + 2 if end != -1 else n
        else:
            out.append(ch)
            i += 1
    cleaned = re.sub(r",(\s*[}\]])", r"\1", "".join(out))
    if not cleaned.strip():
        return {}
    parsed: dict[str, object] = json.loads(cleaned)
    return parsed


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    ts = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    dst = path.with_suffix(f".{ts}.bak")
    shutil.copy2(path, dst)
    return dst


def _read_settings(path: Path) -> dict[str, object]:
    return _parse_jsonc(path.read_text()) if path.exists() else {}


def _write_settings(path: Path, current: dict[str, object], opts: list[_Opt]) -> None:
    merged = {**current, **{o.key: o.value for o in opts}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=4, ensure_ascii=False) + "\n")


def _read_flags(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        ln.strip()
        for ln in path.read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]


def _write_flags(path: Path, flags: list[str]) -> None:
    path.write_text("\n".join(flags) + "\n")
