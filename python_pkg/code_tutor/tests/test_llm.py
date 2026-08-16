"""Tests for python_pkg.code_tutor._llm."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._llm import (
    OllamaBackend,
)

# ---------------------------------------------------------------------------
# OllamaBackend.complete
# ---------------------------------------------------------------------------


def test_ollama_complete_success() -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "hello world"}
    with patch("python_pkg.code_tutor._llm.requests.post", return_value=mock_resp):
        backend = OllamaBackend()
        result = backend.complete("sys", "user")
    assert result == "hello world"
    mock_resp.raise_for_status.assert_called_once()


def test_ollama_complete_missing_key() -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {}
    with patch("python_pkg.code_tutor._llm.requests.post", return_value=mock_resp):
        backend = OllamaBackend()
        result = backend.complete("sys", "user")
    assert result == ""


# ---------------------------------------------------------------------------
# OllamaBackend.stream
# ---------------------------------------------------------------------------


def test_ollama_stream_basic() -> None:
    lines = [
        json.dumps({"response": "hello", "done": False}).encode(),
        b"",  # empty line -> skipped
        json.dumps({"response": " world", "done": False}).encode(),
        json.dumps({"response": "", "done": True}).encode(),
    ]
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter(lines)

    tokens: list[str] = []
    with patch("python_pkg.code_tutor._llm.requests.post", return_value=mock_resp):
        backend = OllamaBackend()
        result = backend.stream("sys", "user", tokens.append)

    assert result == "hello world"
    assert tokens == ["hello", " world"]


def test_ollama_stream_empty_token_not_appended() -> None:
    lines = [
        json.dumps({"response": "", "done": False}).encode(),
        json.dumps({"response": "ok", "done": True}).encode(),
    ]
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter(lines)

    tokens: list[str] = []
    with patch("python_pkg.code_tutor._llm.requests.post", return_value=mock_resp):
        backend = OllamaBackend()
        result = backend.stream("sys", "user", tokens.append)

    assert result == "ok"
    assert tokens == ["ok"]
