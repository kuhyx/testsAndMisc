"""Tests for python_pkg.code_tutor._claude_backend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._claude_backend import ClaudeBackend

# ---------------------------------------------------------------------------
# ClaudeBackend.complete
# ---------------------------------------------------------------------------


def test_claude_complete_with_text_block() -> None:
    mock_block = MagicMock()
    mock_block.text = "answer"
    mock_message = MagicMock()
    mock_message.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch(
        "python_pkg.code_tutor._claude_backend.anthropic.Anthropic",
        return_value=mock_client,
    ):
        backend = ClaudeBackend()
        result = backend.complete("sys", "user")

    assert result == "answer"


def test_claude_complete_no_text_attr() -> None:
    mock_block = MagicMock(spec=[])  # no .text attribute
    mock_message = MagicMock()
    mock_message.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch(
        "python_pkg.code_tutor._claude_backend.anthropic.Anthropic",
        return_value=mock_client,
    ):
        backend = ClaudeBackend()
        result = backend.complete("sys", "user")

    assert result == ""


# ---------------------------------------------------------------------------
# ClaudeBackend.stream
# ---------------------------------------------------------------------------


def test_claude_stream_success() -> None:
    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_stream_ctx.text_stream = iter(["hello", " world"])

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream_ctx

    tokens: list[str] = []
    with patch(
        "python_pkg.code_tutor._claude_backend.anthropic.Anthropic",
        return_value=mock_client,
    ):
        backend = ClaudeBackend()
        result = backend.stream("sys", "user", tokens.append)

    assert result == "hello world"
    assert tokens == ["hello", " world"]


def test_claude_stream_api_error_fallback() -> None:
    import anthropic as anthropic_lib

    mock_client = MagicMock()
    mock_client.messages.stream.side_effect = anthropic_lib.APIError(
        message="fail",
        request=MagicMock(),
        body=None,
    )
    mock_block = MagicMock()
    mock_block.text = "fallback"
    mock_message = MagicMock()
    mock_message.content = [mock_block]
    mock_client.messages.create.return_value = mock_message

    tokens: list[str] = []
    with patch(
        "python_pkg.code_tutor._claude_backend.anthropic.Anthropic",
        return_value=mock_client,
    ):
        backend = ClaudeBackend()
        result = backend.stream("sys", "user", tokens.append)

    assert result == "fallback"
