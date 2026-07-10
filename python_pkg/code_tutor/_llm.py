"""LLM backend abstraction: Ollama (primary) and Claude (fallback).

Backends implement the ``Backend`` protocol.  The ``complete_with_fallback``
helper calls Ollama, detects weak responses, and offers to switch to Claude.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Protocol

import anthropic
import requests

if TYPE_CHECKING:
    from collections.abc import Callable

    from rich.console import Console

_OLLAMA_URL = "http://localhost:11434/api/generate"
_OLLAMA_MODEL = "qwen3-32b-dev:latest"
_OLLAMA_TIMEOUT = 120

_WEAK_PHRASES: frozenset[str] = frozenset(
    {
        "i don't know",
        "i cannot",
        "unclear",
        "i'm not sure",
    }
)
_WEAK_MIN_LEN = 30


class Backend(Protocol):
    """Structural protocol for an LLM backend."""

    def complete(self, system: str, user: str) -> str:
        """Send *system* + *user* prompts and return the model's response.

        Args:
            system: System prompt (role / instructions).
            user: User message (the actual query).

        Returns:
            Raw response text from the model.
        """
        ...  # pragma: no cover

    def stream(
        self,
        system: str,
        user: str,
        on_token: Callable[[str], None],
    ) -> str:
        """Stream the response token-by-token via *on_token*, return full text.

        Args:
            system: System prompt.
            user: User message.
            on_token: Called with each text token as it arrives.

        Returns:
            Full accumulated response text.
        """
        ...  # pragma: no cover


class OllamaBackend:
    """LLM backend that calls the local Ollama HTTP API.

    Args:
        model: Ollama model tag to use.
        url: Base URL of the Ollama API.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        model: str = _OLLAMA_MODEL,
        url: str = _OLLAMA_URL,
        timeout: int = _OLLAMA_TIMEOUT,
    ) -> None:
        """Initialise with model/URL/timeout settings."""
        self._model = model
        self._url = url
        self._timeout = timeout

    def complete(self, system: str, user: str) -> str:
        """Call Ollama and return the response text (non-streaming).

        Args:
            system: System prompt.
            user: User message / prompt.

        Returns:
            Response string from the model.

        Raises:
            requests.exceptions.Timeout: When the request exceeds *timeout*.
            requests.exceptions.ConnectionError: When Ollama is unreachable.
            requests.exceptions.HTTPError: On non-2xx HTTP responses.
        """
        payload = {
            "model": self._model,
            "system": system,
            "prompt": user,
            "stream": False,
        }
        response = requests.post(self._url, json=payload, timeout=self._timeout)
        response.raise_for_status()
        data = response.json()
        return str(data.get("response", ""))

    def stream(
        self,
        system: str,
        user: str,
        on_token: Callable[[str], None],
    ) -> str:
        """Call Ollama with streaming enabled, invoking *on_token* per token.

        Args:
            system: System prompt.
            user: User message.
            on_token: Callback invoked with each response token as it arrives.

        Returns:
            Full accumulated response text.

        Raises:
            requests.exceptions.Timeout: When the request exceeds *timeout*.
            requests.exceptions.ConnectionError: When Ollama is unreachable.
            requests.exceptions.HTTPError: On non-2xx HTTP responses.
        """
        payload = {
            "model": self._model,
            "system": system,
            "prompt": user,
            "stream": True,
        }
        response = requests.post(
            self._url, json=payload, timeout=self._timeout, stream=True
        )
        response.raise_for_status()
        parts: list[str] = []
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            data = json.loads(raw_line)
            token = str(data.get("response", ""))
            if token:
                on_token(token)
                parts.append(token)
            if data.get("done"):
                break
        return "".join(parts)


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


def _is_weak(response: str) -> bool:
    """Return True if *response* looks too short or expresses uncertainty.

    Args:
        response: Raw text from the LLM.

    Returns:
        True when the response is shorter than ``_WEAK_MIN_LEN`` characters
        or contains one of the ``_WEAK_PHRASES`` (case-insensitive).
    """
    if len(response) < _WEAK_MIN_LEN:
        return True
    lower = response.lower()
    return any(phrase in lower for phrase in _WEAK_PHRASES)


def complete_with_fallback(
    primary: OllamaBackend,
    system: str,
    user: str,
    *,
    console: Console,
    input_fn: Callable[[str], str] = input,
) -> str:
    """Call *primary*, detect weakness, and offer a Claude fallback.

    If the primary's response is weak, the user is asked whether to switch
    to Claude for this item.  If they decline (or Claude fails), Ollama is
    retried once.

    Args:
        primary: The Ollama backend to call first.
        system: System prompt.
        user: User message.
        console: Rich console for status messages.
        input_fn: Callable used for user input (injectable for testing).

    Returns:
        Final response string.
    """
    response = primary.complete(system, user)
    if not _is_weak(response):
        return response

    console.print(
        "[yellow][!] Qwen3's response looks weak. Switch to Claude for this item?\n"
        "    (This will use your ANTHROPIC_API_KEY) [y/N]:[/yellow]"
    )
    choice = input_fn("").strip().lower()

    if choice == "y":
        try:
            claude = ClaudeBackend()
            return claude.complete(system, user)
        except anthropic.APIError:
            console.print("[yellow]Claude unavailable, retrying Qwen3...[/yellow]")

    return primary.complete(system, user)
