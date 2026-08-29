"""Socratic lesson loop: ask-first, then judge, then explain.

The LLM explanation is NEVER shown before the user attempts to explain.
"""

from __future__ import annotations

from datetime import UTC, datetime
import time
from typing import TYPE_CHECKING

from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from python_pkg.code_tutor._challenge_flows import run_coding_challenge
from python_pkg.code_tutor._progress import LessonRecord
from python_pkg.code_tutor._verifier_support import (
    _EXPLAIN_SYSTEM,
    _IMPROVEMENT_Q,
    _MAX_ATTEMPTS,
    _QUESTIONS,
    _SYSTEM_PROMPT,
    _parse_verdict,
    _read_snippet,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rich.console import Console

    from python_pkg.code_tutor._analyzer import CodeItem
    from python_pkg.code_tutor._llm import Backend


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
        timestamp = datetime.now(tz=UTC).isoformat(timespec="seconds")
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
