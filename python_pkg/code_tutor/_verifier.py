"""Socratic lesson loop: ask-first, then judge, then explain.

The LLM explanation is NEVER shown before the user attempts to explain.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from typing import TYPE_CHECKING

from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from python_pkg.code_tutor._challenge import run_coding_challenge
from python_pkg.code_tutor._progress import LessonRecord

if TYPE_CHECKING:
    from collections.abc import Callable

    from rich.console import Console

    from python_pkg.code_tutor._analyzer import CodeItem
    from python_pkg.code_tutor._llm import Backend

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


class Verifier:
    """Runs Socratic lessons: user explains first, then the LLM judges.

    Args:
        backend: LLM backend used for both judging and generating explanations.
        console: Rich console for all output.
    """

    def __init__(self, backend: Backend, console: Console) -> None:
        """Store backend and console."""
        self._backend = backend
        self._console = console

    def _judge(self, snippet: str, explanation: str) -> tuple[str, str]:
        """Stream the judge call, show elapsed time, accumulate and parse.

        The raw JSON is streamed silently; a live elapsed-time counter shows
        the user that inference is progressing.

        Args:
            snippet: Source code the user was shown.
            explanation: The user's explanation text.

        Returns:
            Tuple ``(verdict, gap)`` from ``_parse_verdict``.
        """
        user_msg = f"Code:\n{snippet}\n\nUser's explanation:\n{explanation}"
        start = time.monotonic()
        parts: list[str] = []

        def _on_token(token: str) -> None:
            parts.append(token)
            elapsed = int(time.monotonic() - start)
            live.update(Text(f"Judging... {elapsed}s", style="yellow"))

        with Live(
            Text("Judging... 0s", style="yellow"),
            console=self._console,
            refresh_per_second=4,
            transient=True,
        ) as live:
            self._backend.stream(_SYSTEM_PROMPT, user_msg, _on_token)

        return _parse_verdict("".join(parts))

    def _collect_answers(
        self, input_fn: Callable[[str], str]
    ) -> tuple[dict[str, str], bool]:
        """Ask the four core questions and collect answers.

        Args:
            input_fn: Callable used for reading user input.

        Returns:
            Tuple of ``(answers, skipped)`` where *answers* maps question
            labels to the user's text.  *skipped* is ``True`` when the user
            typed ``skip`` on any question.
        """
        answers: dict[str, str] = {}
        for label, question in _QUESTIONS:
            self._console.print(f"[bold]{question}[/bold]")
            answer = input_fn("> ").strip()
            if answer.lower() == "skip":
                self._console.print("[yellow]Skipped.[/yellow]\n")
                return {}, True
            answers[label] = answer
        return answers, False

    def _ask_improvement(self, input_fn: Callable[[str], str]) -> str:
        """Prompt for an optional code-improvement note.

        Args:
            input_fn: Callable used for reading user input.

        Returns:
            The user's improvement idea, or ``""`` if they pressed Enter.
        """
        self._console.print(f"\n[dim]{_IMPROVEMENT_Q}[/dim]")
        return input_fn("> ").strip()

    def run_lesson(
        self,
        item: CodeItem,
        codebase_path: str,
        *,
        input_fn: Callable[[str], str] = input,
    ) -> LessonRecord:
        """Run one Socratic lesson for *item* and return a full transcript.

        Shows the code, asks four sequential questions, judges the answer, and
        repeats up to ``_MAX_ATTEMPTS`` times.  On PASS, offers an optional
        coding challenge (rewrite from scratch, validated by tests) then asks
        the improvement question.  Never reveals the correct explanation before
        the user has tried.

        Args:
            item: The code item to study.
            codebase_path: Absolute path of the codebase root.
            input_fn: Callable used for reading user input.

        Returns:
            ``LessonRecord`` with ``outcome`` of ``"learned"``,
            ``"struggled"``, or ``"skipped"``.
        """
        snippet = _read_snippet(item, codebase_path)
        timestamp = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
        lines_str = f"{item.start_line}-{item.end_line}"
        title = f"{item.file}  lines {lines_str}"

        self._console.print(Panel(snippet, title=title, border_style="blue"))
        self._console.print(
            "\nAnswer each question before I say anything. "
            "Type [dim]skip[/dim] on any question to skip this item.\n"
        )

        answers: dict[str, str] = {}

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            collected, skipped = self._collect_answers(input_fn)
            if skipped:
                return LessonRecord(
                    timestamp=timestamp,
                    item_id=item.id,
                    file=item.file,
                    lines=lines_str,
                    snippet=snippet,
                    outcome="skipped",
                    answers={},
                    improvement="",
                    verdict="skipped",
                    attempt=attempt,
                )
            answers = collected
            explanation = "\n".join(f"{k}: {v}" for k, v in answers.items())
            verdict, gap = self._judge(snippet, explanation)

            if verdict == "PASS":
                self._console.print(
                    f"[green]✓ PASS[/green] (attempt {attempt}/{_MAX_ATTEMPTS})\n"
                )
                challenge_result = run_coding_challenge(
                    item,
                    codebase_path,
                    explanation,
                    self._backend,
                    self._console,
                    input_fn,
                )
                improvement = self._ask_improvement(input_fn)
                return LessonRecord(
                    timestamp=timestamp,
                    item_id=item.id,
                    file=item.file,
                    lines=lines_str,
                    snippet=snippet,
                    outcome="learned",
                    answers=answers,
                    improvement=improvement,
                    verdict="PASS",
                    attempt=attempt,
                    challenge_result=challenge_result,
                )

            if attempt < _MAX_ATTEMPTS:
                self._console.print(f"[red]✗ FAIL[/red] -- {gap}")
                self._console.print(f"Try again ({attempt}/{_MAX_ATTEMPTS}):\n")

        self._console.print(
            f"[red]After {_MAX_ATTEMPTS} attempts -- correct explanation:[/red]\n"
        )
        self._backend.stream(
            _EXPLAIN_SYSTEM,
            f"Explain:\n{snippet}",
            lambda token: self._console.print(
                token, end="", markup=False, highlight=False
            ),
        )
        self._console.print("\n")

        improvement = self._ask_improvement(input_fn)
        return LessonRecord(
            timestamp=timestamp,
            item_id=item.id,
            file=item.file,
            lines=lines_str,
            snippet=snippet,
            outcome="struggled",
            answers=answers,
            improvement=improvement,
            verdict="FAIL",
            attempt=_MAX_ATTEMPTS,
        )
