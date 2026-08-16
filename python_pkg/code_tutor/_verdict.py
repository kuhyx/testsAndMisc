"""Streaming an LLM verdict behind an elapsed-time display, and parsing it.

Split out of :mod:`python_pkg.code_tutor._challenge_support` to keep it under
the 250-line cap. ``Live`` is imported here rather than there because this is
the only code that used it, and the tests patch it on whichever module the
call resolves through.
"""

from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING

from rich.live import Live
from rich.text import Text

if TYPE_CHECKING:
    from rich.console import Console

    from python_pkg.code_tutor._llm import Backend


def _stream_verdict(
    system: str,
    user_msg: str,
    backend: Backend,
    console: Console,
    label: str = "Rating",
) -> str:
    """Stream an LLM call silently while showing an elapsed timer.

    Args:
        system: System prompt for the judge.
        user_msg: User message to judge.
        backend: LLM backend with a ``stream(system, user, callback)`` method.
        console: Rich console for the live timer.
        label: Label prefix shown in the timer (e.g. ``"Rating"``).

    Returns:
        Accumulated response text.
    """
    parts: list[str] = []
    start = time.monotonic()

    def _on_token(token: str) -> None:
        parts.append(token)
        elapsed = int(time.monotonic() - start)
        live.update(Text(f"{label}... {elapsed}s", style="yellow"))

    with Live(
        Text(f"{label}... 0s", style="yellow"),
        console=console,
        refresh_per_second=4,
        transient=True,
    ) as live:
        backend.stream(system, user_msg, _on_token)

    return "".join(parts)


def _parse_verdict(raw: str) -> tuple[str, str]:
    """Parse ``{"verdict": ..., "gap": ...}`` JSON from *raw*, tolerating fences.

    Args:
        raw: Raw LLM response text.

    Returns:
        ``(verdict, gap)`` where verdict is ``"PASS"`` or ``"FAIL"``.
    """
    clean = re.sub(r"```(?:json)?\s*", "", raw, flags=re.DOTALL).strip()
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start == -1 or end == 0:
        return "FAIL", "Could not parse judge response."
    try:
        data = json.loads(clean[start:end])
    except json.JSONDecodeError:
        return "FAIL", "Could not parse judge response."
    verdict = str(data.get("verdict", "FAIL")).upper()
    if verdict not in {"PASS", "FAIL"}:
        verdict = "FAIL"
    return verdict, str(data.get("gap", ""))


# ---------------------------------------------------------------------------
# "Write tests first" flow -- helpers
# ---------------------------------------------------------------------------
