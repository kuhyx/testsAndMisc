"""Output normalisation and diffing, mirroring an exact-match judge.

The engine prints ``mysql -B -N`` output (no header, tab-separated, ``NULL``
literal). Before comparing we turn each tab into one space and strip trailing
whitespace per line -- nothing else. Case, decimals and row order stay strict.
"""

from __future__ import annotations

from itertools import zip_longest

_ABSENT = "<no line>"


def normalize(text: str) -> list[str]:
    """Return judge-style lines: tabs to single spaces, right-stripped."""
    return [line.replace("\t", " ").rstrip() for line in text.splitlines()]


def matches(expected: str, actual: str) -> bool:
    """True when both outputs normalise to identical line lists."""
    return normalize(expected) == normalize(actual)


def _show(line: str | None) -> str:
    """Render a line for the diff, making odd spacing visible via repr."""
    if line is None:
        return _ABSENT
    if line.startswith(" ") or "  " in line:
        return repr(line)
    return line


def diff(expected: list[str], actual: list[str]) -> str:
    """Line-by-line expected/actual report for differing lines only."""
    blocks = [
        f"line {no}:\n  expected: {_show(exp)}\n  actual  : {_show(act)}"
        for no, (exp, act) in enumerate(zip_longest(expected, actual), start=1)
        if exp != act
    ]
    return "\n".join(blocks)
