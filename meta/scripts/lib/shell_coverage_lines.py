#!/usr/bin/env python3
"""Line classification for shell coverage: what is a statement, and what ran.

Split out of ``shell_coverage_report.py`` to keep both files under the repo's
250-line cap.

Two independent instruments feed the report, because neither is correct alone
(see ``docs/kcov-under-report.md``):

* kcov supplies the *line set* -- which lines are instrumentable at all. Its
  hit counts are unreliable: ordinary statements execute without being
  recorded (defect (b)).
* a PS4 xtrace supplies the *executed* set. A trace can only ever report lines
  that ran, so it cannot supply a denominator -- using it for both halves
  would make every subject 100% and gate on nothing.

So: denominator = kcov's line set minus non-statements; numerator =
(traced lines | kcov's hits) & denominator.
"""

from __future__ import annotations

from pathlib import Path
import re

# A PS4 trace line looks like: "+PS4:/abs/path/to/lib.sh:42 some command"
# The leading '+' repeats with nesting depth, so it is matched loosely.
_TRACE_RE = re.compile(r"\+*PS4:(?P<path>[^:]*):(?P<line>\d+)")


def traced_lines(trace_dir: Path, subject: str) -> set[int]:
    """Return the line numbers of *subject* seen executing in a PS4 trace."""
    seen: set[int] = set()
    if not trace_dir.is_dir():
        return seen
    for trace_file in sorted(trace_dir.iterdir()):
        if not trace_file.is_file():
            continue
        # errors="replace": a trace interleaves writes from concurrent
        # processes and can split a UTF-8 sequence. A decode error must not
        # discard the whole file, which would read as zero coverage.
        text = trace_file.read_text(encoding="utf-8", errors="replace")
        for match in _TRACE_RE.finditer(text):
            if Path(match.group("path")).name == subject:
                seen.add(int(match.group("line")))
    return seen


def traced_paths(trace_dir: Path, subject: str) -> list[Path]:
    """Return the distinct source paths a PS4 trace recorded for *subject*.

    kcov's XML carries only a basename, so the trace is the one place the
    subject's real location is written down.
    """
    found: list[Path] = []
    if not trace_dir.is_dir():
        return found
    for trace_file in sorted(trace_dir.iterdir()):
        if not trace_file.is_file():
            continue
        text = trace_file.read_text(encoding="utf-8", errors="replace")
        for match in _TRACE_RE.finditer(text):
            path = Path(match.group("path"))
            if path.name == subject and path not in found:
                found.append(path)
    return found


def continuation_lines(source: Path) -> set[int]:
    """Return lines that are *inside* a multi-line quoted argument.

    kcov counts these as instrumentable statements that never run, which
    inflates the denominator and caps a subject's coverage below 100% no
    matter what the tests do (defect (a)). A `bash -x` tracer never reports
    them as executable at all, which is the correct reading: they are data
    inside an argument, not statements.

    Detected by tracking quote state across the file: any line that *begins*
    while a quote opened on an earlier line is still open is a continuation.
    Only the opening line of such a construct is a statement.
    """
    inside: set[int] = set()
    quote: str | None = None
    for number, raw in enumerate(
        source.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        if quote is not None:
            inside.add(number)
        index = 0
        while index < len(raw):
            char = raw[index]
            if quote is None:
                if char == "#":
                    # A comment outside quotes ends the line's significance.
                    break
                if char == "\\":
                    index += 2
                    continue
                if char in ("'", '"'):
                    quote = char
            elif char == quote:
                quote = None
            elif quote == '"' and char == "\\":
                # Only double quotes honour backslash escapes; inside single
                # quotes a backslash is a literal character.
                index += 2
                continue
            index += 1
    return inside
