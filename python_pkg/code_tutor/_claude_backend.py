"""The Anthropic-API backend used as a fallback when the local model is weak.

Split out of :mod:`python_pkg.code_tutor._llm` to keep it under the 250-line
cap. The ``anthropic`` import travels with the only class that uses it, so
``tests/test_llm.py`` patches it on this module and ``requests`` on ``_llm``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import anthropic

if TYPE_CHECKING:
    from collections.abc import Callable


class ClaudeBackend:
    """LLM backend that calls the Anthropic Claude API.

    Reads ``ANTHROPIC_API_KEY`` from the environment automatically.

    Args:
        model: Claude model identifier.
        max_tokens: Maximum tokens in the response.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1024,
    ) -> None:
        """Initialise Anthropic client."""
        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        """Call Claude and return the response text.

        Args:
            system: System prompt.
            user: User message.

        Returns:
            Response string from Claude.

        Raises:
            anthropic.APIError: On any Anthropic API failure.
        """
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        block = message.content[0]
        if hasattr(block, "text"):
            return str(block.text)
        return ""

    def stream(
        self,
        system: str,
        user: str,
        on_token: Callable[[str], None],
    ) -> str:
        """Call Claude with streaming, invoking *on_token* per text delta.

        Falls back to ``complete`` on ``APIError``.

        Args:
            system: System prompt.
            user: User message.
            on_token: Callback invoked with each text delta as it arrives.

        Returns:
            Full accumulated response text.
        """
        try:
            parts: list[str] = []
            with self._client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            ) as s:
                for text in s.text_stream:
                    on_token(text)
                    parts.append(text)
            return "".join(parts)
        except anthropic.APIError:
            return self.complete(system, user)
