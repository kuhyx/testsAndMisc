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


# A line holding only a group's closing brace plus an operator: `} |`,
# `} >>file`, `} <in`, `} &>log`. kcov instruments these, but bash attributes
# no statement to them -- each command INSIDE the group is attributed to its
# own line, and a pipe's right-hand side to its own line, leaving the brace
# line with nothing. Anchoring on a leading `}` is what keeps this safe: a
# one-liner `{ echo a; } >file` begins with `{` and is a real statement, and a
# bare `}` closing a function carries no operator.
_CLOSING_BRACE_OP = re.compile(r"^\s*\}\s*(\||>>?|<|&>)")

# A loop terminator carrying a redirect: `done >file`, `done <file`,
# `done | cmd`. Same defect as _CLOSING_BRACE_OP and the same reasoning: bash
# attributes the redirected compound statement to the loop's OPENING line
# (the `for`/`while`), so the `done` line is instrumented but can never be
# hit. Measured on a three-line loop: the body reports hits=3 and the
# `done >"$1"` line reports hits=0 in the same run.
#
# The redirect is REQUIRED by the pattern. A bare `done` closing an ordinary
# loop is attributed normally and must stay in the denominator, so matching
# it here would hide real uncovered code.
_LOOP_END_OP = re.compile(r"^\s*done\s*(\||>>?|<|&>)")

# An assignment whose value opens a multi-line array literal, e.g.
# `local -a candidates=(` or `FILES=(`. bash reports the WHOLE assignment at
# this opening line and never emits the element lines or the closing paren, so
# those are data. Symmetric with the multi-line-quote case: the opening line
# is the statement, everything up to the closing paren is not.
_ARRAY_OPEN = re.compile(
    r"^\s*(?:local\s+|declare\s+|readonly\s+|export\s+)*"
    r"(?:-[a-zA-Z]+\s+)*"
    r"[A-Za-z_][A-Za-z0-9_]*\+?=\(\s*(?:#.*)?$"
)


def continuation_lines(source: Path) -> set[int]:
    """Return lines that are *inside* a multi-line quoted argument.

    kcov counts these as instrumentable statements that never run, which
    inflates the denominator and caps a subject's coverage below 100% no
    matter what the tests do (defect (a)). A `bash -x` tracer never reports
    them as executable at all, which is the correct reading: they are data
    inside an argument, not statements.

    Two shapes qualify:

    * a line that *begins* while a quote opened on an earlier line is still
      open -- the continuation of a multi-line quoted argument. Only the
      opening line of such a construct is a statement.
    * a line holding just a group's closing brace and an operator (``} |``,
      ``} >>file``). See ``_CLOSING_BRACE_OP``.
    * a loop terminator carrying a redirect (``done >file``, ``done <file``).
      See ``_LOOP_END_OP``.
    * the element lines and closing paren of a multi-line array literal.
      See ``_ARRAY_OPEN``.
    """
    inside: set[int] = set()
    quote: str | None = None
    in_array = False
    for number, raw in enumerate(
        source.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        if quote is not None or in_array:
            inside.add(number)
        starts_open = quote is None and not in_array and bool(_ARRAY_OPEN.match(raw))
        quote = _quote_after(raw, quote)
        if in_array and quote is None and _closes_array(raw):
            in_array = False
        elif starts_open:
            in_array = True
        if (
            quote is None
            and not in_array
            and (_CLOSING_BRACE_OP.match(raw) or _LOOP_END_OP.match(raw))
        ):
            inside.add(number)
    return inside


def _closes_array(raw: str) -> bool:
    """Return True when ``raw`` closes a multi-line array literal.

    Only a ``)`` that is not itself inside quotes counts, so an element like
    ``"a(b)"`` does not end the literal. Quote state is recomputed from the
    start of the line for each candidate rather than pattern-matched.
    """
    for index, char in enumerate(raw):
        if char == ")" and _quote_after(raw[:index], None) is None:
            return True
    return False


def _quote_after(raw: str, quote: str | None) -> str | None:
    """Return the open-quote state at the end of ``raw``, given its state at the start.

    ``None`` means no quote is open. Escapes are honoured outside quotes and
    inside double quotes, but not inside single quotes, which take a
    backslash literally.
    """
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
            index += 2
            continue
        index += 1
    return quote
