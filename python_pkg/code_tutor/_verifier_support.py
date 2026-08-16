"""Prompts and source-snippet helpers for the lesson verifier.

Split out of :mod:`python_pkg.code_tutor._verifier` to keep it under the
250-line cap. ``Verifier`` itself stays there, because that is the name
``cli`` and ``_session`` construct and the tests patch.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python_pkg.code_tutor._analyzer import CodeItem


_MAX_ATTEMPTS = 3

_SYSTEM_PROMPT = (
    "You are a fair but rigorous code tutor assessing whether a student"
    " genuinely understands a piece of code.\n\n"
    "Grade their explanation PASS or FAIL.\n\n"
    "PASS when the student demonstrates understanding of:\n"
    "  - what problem the code solves (purpose)\n"
    "  - what goes in (inputs/parameters and their roles)\n"
    "  - what comes out or happens (return value or side effect)\n"
    "  - any key behavior that would surprise a reader"
    " (edge cases, error handling, non-obvious constraints)\n\n"
    "You do NOT require verbatim phrasing from the code or docstring.\n"
    "Correct paraphrasing counts as understanding.\n"
    "ONLY cite a gap if it is genuinely absent from the student's answer"
    " -- do NOT cite a gap the student already covered in different words.\n\n"
    "FAIL only if the student is vague, factually wrong, or missed a key"
    " behavioral detail that materially changes how the code is used.\n"
    '"It does some stuff" = FAIL. "It processes data" = FAIL.'
    ' But "it reads the first 512 bytes and checks for a null byte" = PASS'
    " on the behavior criterion, even if they didn't mention OSError.\n\n"
    "Respond with valid JSON only, no other text:\n"
    '{"verdict": "PASS" | "FAIL",'
    ' "gap": "<one sentence on the specific missing piece, or empty string on PASS>"}'
)

_EXPLAIN_SYSTEM = (
    "You are a code tutor."
    " Explain the following code clearly and concisely in 3-5 sentences."
)

_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("Purpose", "What does this code do?"),
    ("Inputs", "What are the inputs (parameters / arguments)?"),
    ("Outputs", "What does it output or do as a side effect?"),
    ("Why", "Why does it exist? What problem does it solve?"),
)

_IMPROVEMENT_Q = "What would you improve or simplify here? (Enter to skip)"


def _class_header(lines: list[str], class_name: str, before_line: int) -> str:
    """Find the class definition for *class_name* and return a short header.

    Searches backward from *before_line* for ``class <class_name>``.  Returns
    the class signature plus up to 4 following lines (docstring / key attrs).

    Args:
        lines: All source lines of the file (0-indexed).
        class_name: Name of the enclosing class.
        before_line: 1-based line number of the method; search stops here.

    Returns:
        A short string summary of the class, or ``""`` if not found.
    """
    pattern = re.compile(rf"^class\s+{re.escape(class_name)}\b")
    for i in range(min(before_line - 1, len(lines)) - 1, -1, -1):
        if pattern.match(lines[i]):
            snippet_end = min(i + 5, before_line - 1)
            return "\n".join(lines[i:snippet_end])
    return ""


def _read_snippet(item: CodeItem, codebase_path: str) -> str:
    """Read source lines for *item* from *codebase_path*.

    When the item belongs to a class, a short class header is prepended so
    the user has context about what ``self`` refers to.

    Args:
        item: Code item whose file and line range to read.
        codebase_path: Absolute path of the codebase root.

    Returns:
        The extracted source lines as a single string, or a placeholder
        message when the file cannot be read.
    """
    method_src = ""
    try:
        text = (Path(codebase_path) / item.file).read_text(
            encoding="utf-8", errors="replace"
        )
        lines = text.splitlines()
        start = max(0, item.start_line - 1)
        end = min(len(lines), item.end_line)
        method_src = "\n".join(lines[start:end])

        if item.class_name:
            header = _class_header(lines, item.class_name, item.start_line)
            if header:
                return (
                    f"# class {item.class_name} (context):\n{header}"
                    f"\n\n# method:\n{method_src}"
                )
    except OSError:
        return f"(source unavailable for {item.file})"
    return method_src


def _parse_verdict(raw: str) -> tuple[str, str]:
    """Parse the LLM's JSON verdict, tolerating markdown code fences.

    Args:
        raw: Raw text returned by the judge LLM.

    Returns:
        Tuple of ``(verdict, gap)`` where *verdict* is ``"PASS"`` or
        ``"FAIL"`` and *gap* is a one-sentence explanation of what was wrong.
        Returns ``("FAIL", ...)`` on any parse failure.
    """
    clean = re.sub(r"```(?:json)?\s*", "", raw, flags=re.DOTALL).strip()
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start == -1 or end == 0:
        return "FAIL", "Could not parse response from judge."
    try:
        data = json.loads(clean[start:end])
    except json.JSONDecodeError:
        return "FAIL", "Could not parse response from judge."
    verdict = str(data.get("verdict", "FAIL")).upper()
    if verdict not in {"PASS", "FAIL"}:
        verdict = "FAIL"
    gap = str(data.get("gap", "No specific gap identified."))
    return verdict, gap
