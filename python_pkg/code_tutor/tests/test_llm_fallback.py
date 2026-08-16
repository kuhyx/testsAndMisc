"""Tests for weak-response detection and the Claude fallback."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.code_tutor._llm import (
    OllamaBackend,
    _is_weak,
    complete_with_fallback,
)

# ---------------------------------------------------------------------------
# _is_weak
# ---------------------------------------------------------------------------


def test_is_weak_short() -> None:
    assert _is_weak("ok") is True


def test_is_weak_phrase() -> None:
    assert _is_weak("I don't know what this code does at all honestly") is True


def test_is_weak_strong_response() -> None:
    long_response = (
        "This function reads the first 512 bytes of a file and checks for"
        " null bytes to determine if the file is binary."
    )
    assert _is_weak(long_response) is False


# ---------------------------------------------------------------------------
# complete_with_fallback
# ---------------------------------------------------------------------------


def test_complete_with_fallback_strong() -> None:
    mock_primary = MagicMock(spec=OllamaBackend)
    mock_primary.complete.return_value = (
        "This is a detailed response explaining the code in full."
    )
    mock_console = MagicMock()

    result = complete_with_fallback(
        mock_primary, "sys", "user", console=mock_console, input_fn=lambda _: ""
    )

    assert result == "This is a detailed response explaining the code in full."
    mock_primary.complete.assert_called_once()


def test_complete_with_fallback_weak_user_says_yes_claude_ok() -> None:

    mock_primary = MagicMock(spec=OllamaBackend)
    mock_primary.complete.return_value = "ok"  # short → weak

    mock_block = MagicMock()
    mock_block.text = "claude response is great"
    mock_message = MagicMock()
    mock_message.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    mock_console = MagicMock()

    with patch(
        "python_pkg.code_tutor._llm.anthropic.Anthropic", return_value=mock_client
    ):
        result = complete_with_fallback(
            mock_primary, "sys", "user", console=mock_console, input_fn=lambda _: "y"
        )

    assert result == "claude response is great"


def test_complete_with_fallback_weak_user_says_yes_claude_fails() -> None:
    import anthropic as anthropic_lib

    mock_primary = MagicMock(spec=OllamaBackend)
    mock_primary.complete.side_effect = [
        "ok",  # first call → weak
        "retry response from ollama",  # retry after claude failure
    ]

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = anthropic_lib.APIError(
        message="fail",
        request=MagicMock(),
        body=None,
    )

    mock_console = MagicMock()

    with patch(
        "python_pkg.code_tutor._llm.anthropic.Anthropic", return_value=mock_client
    ):
        result = complete_with_fallback(
            mock_primary, "sys", "user", console=mock_console, input_fn=lambda _: "y"
        )

    assert result == "retry response from ollama"
    assert mock_primary.complete.call_count == 2


def test_complete_with_fallback_weak_user_says_no() -> None:
    mock_primary = MagicMock(spec=OllamaBackend)
    mock_primary.complete.side_effect = [
        "ok",  # first call → weak
        "second ollama response here too",  # retry
    ]
    mock_console = MagicMock()

    result = complete_with_fallback(
        mock_primary, "sys", "user", console=mock_console, input_fn=lambda _: "n"
    )

    assert result == "second ollama response here too"
    assert mock_primary.complete.call_count == 2


def test_ollama_backend_defaults() -> None:
    backend = OllamaBackend()
    assert "11434" in backend._url
    assert backend._timeout > 0


@pytest.mark.parametrize(
    "phrase",
    [
        "i cannot help with that request really",
        "it is unclear what you mean by that",
        "i'm not sure about this code",
    ],
)
def test_is_weak_various_phrases(phrase: str) -> None:
    assert _is_weak(phrase) is True


def test_ollama_stream_no_done_marker() -> None:
    """Exhaust the stream loop without a ``done`` marker (no ``break``).

    When no line carries ``done: true`` the loop runs to exhaustion and
    falls through to ``return "".join(parts)`` rather than breaking early.
    """
    lines = [
        json.dumps({"response": "foo", "done": False}).encode(),
        json.dumps({"response": "bar", "done": False}).encode(),
    ]
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter(lines)

    tokens: list[str] = []
    with patch("python_pkg.code_tutor._llm.requests.post", return_value=mock_resp):
        backend = OllamaBackend()
        result = backend.stream("sys", "user", tokens.append)

    assert result == "foobar"
    assert tokens == ["foo", "bar"]
