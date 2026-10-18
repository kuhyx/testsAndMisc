"""Name what a tool call was, for the carry-cost and tool panels.

``family`` is the bucket a panel groups by (``git status``, ``mcp:<server>``,
``Read:memory``); ``target`` is the one thing it touched (the command, path,
host or query), capped so the store stays small; ``signature`` identifies
identical repeated calls (loops) without storing the full input.
"""

from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlsplit

from python_pkg.token_audit.model import IMAGE_SUFFIXES

TARGET_CHARS = 160
SIG_CHARS = 16
EMPTY = "(empty)"

# Words that only wrap the real command (and the flags/numbers they take).
_WRAPPERS = frozenset(
    {
        "sudo",
        "env",
        "nice",
        "ionice",
        "timeout",
        "time",
        "nohup",
        "exec",
        "command",
        "capped.sh",
        "stdbuf",
        "xargs",
    }
)
# Tools whose first non-flag argument is what the call really did.
_SUBCOMMANDS = frozenset(
    {
        "git",
        "pnpm",
        "npm",
        "npx",
        "flutter",
        "dart",
        "cargo",
        "go",
        "docker",
        "systemctl",
        "gh",
        "pre-commit",
        "uv",
        "pip",
        "yay",
        "pacman",
        "adb",
        "make",
        "fvm",
        "journalctl",
    }
)
_TAKES_VALUE = frozenset({"-C", "-c", "-n", "--dir", "--prefix"})
_SHELLS = frozenset({"bash", "sh", "zsh"})
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_SEGMENTS = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")
_NUMBERISH = re.compile(r"^\d+[smhd]?$")
_ERRORS = (
    ("Exit code", "exit_code"),
    ("<tool_use_error>", "tool_error"),
    ("doesn't want to proceed", "rejected"),
    ("Permission for this action was denied", "denied"),
    ("hook error", "hook"),
    ("TIME CAP", "time_cap"),
    ("[Request interrupted", "interrupted"),
)


def _base(word: str) -> str:
    """Last path component of a command word."""
    return word.rsplit("/", 1)[-1]


def _command_words(words: list[str]) -> list[str]:
    """Drop leading assignments, wrappers and the flags/values they take."""
    index = 0
    while index < len(words):
        word = words[index]
        if not (
            _ASSIGN.match(word)
            or _base(word) in _WRAPPERS
            or word.startswith("-")
            or _NUMBERISH.match(word)
        ):
            break
        index += 1
    return words[index:]


def _first_argument(words: list[str]) -> str:
    """The first non-flag word, skipping flags that take a value."""
    skip = False
    for word in words:
        if skip:
            skip = False
        elif word in _TAKES_VALUE:
            skip = True
        elif not word.startswith(("-", "<", ">", "2>")):
            return word
    return ""


def _name_command(words: list[str]) -> str:
    """``git status``, ``python3 -m pytest``, ``bash x.sh`` or the bare name."""
    head, rest = _base(words[0]), words[1:]
    if head.startswith("python"):
        if "-m" in rest:
            after = rest[rest.index("-m") + 1 :]
            return f"{head} -m {after[0]}" if after else f"{head} -m"
        script = _first_argument(rest)
        return f"{head} {_base(script)}" if script else head
    if head in _SHELLS and "-c" in rest:
        return f"{head} -c"
    if head in _SHELLS or head in _SUBCOMMANDS:
        arg = _first_argument(rest)
        return f"{head} {_base(arg) if head in _SHELLS else arg}".strip()
    return head


def bash_family(command: str) -> str:
    """The command a Bash call really ran, ignoring wrappers and ``cd``."""
    last = ""
    for segment in _SEGMENTS.split(command.strip()):
        words = _command_words(segment.split())
        if not words:
            continue
        last = _name_command(words)
        if last != "cd":
            return last
    return last or EMPTY


_PATH_KINDS = (
    ("memory", ("/.claude/", "/memory/"), ("/.claude/", "/memories/")),
    ("rules", ("/.claude/rules",), ("rules-ondemand",)),
    ("skill", ("/skills/",)),
    ("claude", ("/.claude/",)),
)


def _path_kind(path: str) -> str:
    """What a file path is, as far as standing context goes."""
    name = _base(path)
    if name.startswith("CLAUDE") and name.endswith(".md"):
        return "claude-md"
    for kind, *needle_sets in _PATH_KINDS:
        if any(all(n in path for n in needles) for needles in needle_sets):
            return kind
    lowered = path.lower()
    return "image" if lowered.endswith(tuple(IMAGE_SUFFIXES)) else "file"


def _text(tool_input: dict[str, object], key: str) -> str:
    """One string input field, empty when absent."""
    value = tool_input.get(key)
    return value if isinstance(value, str) else ""


def family(name: str, tool_input: dict[str, object]) -> str:
    """The bucket a call is grouped under."""
    if name == "Bash":
        return bash_family(_text(tool_input, "command"))
    if name.startswith("mcp__"):
        return f"mcp:{name.split('__')[1]}"
    if name == "Skill":
        return "skill"
    if name in {"Read", "Write", "Edit", "MultiEdit", "NotebookEdit"}:
        return f"{name}:{_path_kind(_text(tool_input, 'file_path'))}"
    return name


def target(name: str, tool_input: dict[str, object]) -> str:
    """The one thing a call touched, whitespace-collapsed and capped."""
    if name == "Bash":
        found = _text(tool_input, "command")
    elif name.startswith("mcp__"):
        found = name.split("__", 2)[-1]
    elif name == "Skill":
        found = _text(tool_input, "skill")
    elif name == "WebFetch":
        found = urlsplit(_text(tool_input, "url")).netloc
    elif name in {"WebSearch", "Grep", "Glob"}:
        found = _text(tool_input, "query") or _text(tool_input, "pattern")
    elif name in {"Agent", "Task"}:
        kind = _text(tool_input, "subagent_type") or "general-purpose"
        worktree = _text(tool_input, "isolation") == "worktree"
        found = f"{kind} [worktree]" if worktree else kind
    else:
        found = _text(tool_input, "file_path")
    return " ".join(found.split())[:TARGET_CHARS]


def signature(name: str, tool_input: dict[str, object]) -> str:
    """A short stable hash of the full call, for spotting identical repeats."""
    raw = json.dumps([name, tool_input], sort_keys=True, default=str)
    return hashlib.sha1(raw.encode(), usedforsecurity=False).hexdigest()[:SIG_CHARS]


def error_kind(text: str) -> str:
    """Why a tool call failed, from its result text."""
    head = text[:400]
    for needle, kind in _ERRORS:
        if needle in head:
            return kind
    return "error"
