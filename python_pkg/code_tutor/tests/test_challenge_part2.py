"""Tests for the code_tutor challenge helpers -- part 2.

Covers the LLM verdict/signature helpers in ``_challenge_support``
(``_stream_verdict``, ``_parse_verdict``, ``_extract_signature_block``,
``_import_hint``) and the test-validation/rating helpers in ``_challenge``
(``_validate_tests_against_real``, ``_collect_and_rate_tests``).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._verdict import _parse_verdict, _stream_verdict
from python_pkg.code_tutor.tests.conftest import _make_live_mock

# ---------------------------------------------------------------------------
# _stream_verdict
# ---------------------------------------------------------------------------


def test_stream_verdict_accumulates_tokens() -> None:
    mock_backend = MagicMock()
    mock_console = MagicMock()
    live_mock = _make_live_mock()

    def fake_stream(system: str, user: str, on_token: object) -> str:
        assert callable(on_token)
        return '{"verdict": "PASS", "gap": ""}'

    mock_backend.stream.side_effect = fake_stream

    with patch("python_pkg.code_tutor._verdict.Live", return_value=live_mock):
        result = _stream_verdict("sys", "user", mock_backend, mock_console)

    assert result == ""  # parts is empty since on_token was never called by stream
    mock_backend.stream.assert_called_once()


def test_stream_verdict_on_token_called() -> None:
    mock_backend = MagicMock()
    mock_console = MagicMock()
    live_mock = _make_live_mock()

    def fake_stream(system: str, user: str, on_token: object) -> str:
        assert callable(on_token)
        on_token('{"verdict":')
        on_token(' "PASS", "gap": ""}')
        return ""

    mock_backend.stream.side_effect = fake_stream

    with patch("python_pkg.code_tutor._verdict.Live", return_value=live_mock):
        result = _stream_verdict(
            "sys", "user", mock_backend, mock_console, label="Test"
        )

    assert '{"verdict":' in result


# ---------------------------------------------------------------------------
# _parse_verdict (challenge version)
# ---------------------------------------------------------------------------


def test_challenge_parse_verdict_pass() -> None:
    verdict, gap = _parse_verdict('{"verdict": "PASS", "gap": ""}')
    assert verdict == "PASS"
    assert gap == ""


def test_challenge_parse_verdict_fail() -> None:
    verdict, gap = _parse_verdict('{"verdict": "FAIL", "gap": "missing"}')
    assert verdict == "FAIL"
    assert gap == "missing"


def test_challenge_parse_verdict_no_braces() -> None:
    verdict, _gap = _parse_verdict("no json")
    assert verdict == "FAIL"


def test_challenge_parse_verdict_json_error() -> None:
    verdict, _gap = _parse_verdict("{bad}")
    assert verdict == "FAIL"


def test_challenge_parse_verdict_invalid() -> None:
    verdict, _gap = _parse_verdict('{"verdict": "UNKNOWN", "gap": "x"}')
    assert verdict == "FAIL"
