"""Tests for the code_tutor challenge helpers -- part 2.

Covers the LLM verdict/signature helpers in ``_challenge_support``
(``_stream_verdict``, ``_parse_verdict``, ``_extract_signature_block``,
``_import_hint``) and the test-validation/rating helpers in ``_challenge``
(``_validate_tests_against_real``, ``_collect_and_rate_tests``).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._challenge import (
    _collect_and_rate_tests,
    _validate_tests_against_real,
)
from python_pkg.code_tutor._challenge_support import (
    _extract_signature_block,
    _import_hint,
    _parse_verdict,
    _stream_verdict,
)
from python_pkg.code_tutor.tests.conftest import _item, _make_live_mock

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

    with patch("python_pkg.code_tutor._challenge_support.Live", return_value=live_mock):
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

    with patch("python_pkg.code_tutor._challenge_support.Live", return_value=live_mock):
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


# ---------------------------------------------------------------------------
# _extract_signature_block
# ---------------------------------------------------------------------------


def test_extract_signature_block_with_docstring(tmp_path: Path) -> None:
    source = 'def fn(x):\n    """Do thing."""\n    return x\n'
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    result = _extract_signature_block(_item(file="mod.py"), str(tmp_path))
    assert "def fn" in result
    assert '"""Do thing."""' in result


def test_extract_signature_block_without_docstring(tmp_path: Path) -> None:
    source = "def fn(x):\n    return x\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    result = _extract_signature_block(_item(file="mod.py"), str(tmp_path))
    assert "def fn" in result
    assert "return" not in result


def test_extract_signature_block_oserror(tmp_path: Path) -> None:
    result = _extract_signature_block(_item(file="missing.py"), str(tmp_path))
    assert "def fn(...):" in result


def test_extract_signature_block_no_match(tmp_path: Path) -> None:
    source = "def other(): pass\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    result = _extract_signature_block(_item(file="mod.py", name="fn"), str(tmp_path))
    assert "def fn(...):" in result


def test_extract_signature_block_syntax_error(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def (broken):\n", encoding="utf-8")
    result = _extract_signature_block(_item(file="mod.py"), str(tmp_path))
    assert "def fn(...):" in result


# ---------------------------------------------------------------------------
# Tests for _import_hint
# ---------------------------------------------------------------------------


def test_import_hint_relative_to_project(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    result = _import_hint(
        _item(file="src/mod.py", name="fn"),
        str(tmp_path),
        tmp_path,
    )
    assert result == "from src.mod import fn"


def test_import_hint_value_error(tmp_path: Path) -> None:
    # project_root is different from codebase_path
    other_root = tmp_path / "other"
    other_root.mkdir()
    result = _import_hint(
        _item(file="src/mod.py", name="fn"),
        str(tmp_path),
        other_root,
    )
    assert result == "from mod import fn"


# ---------------------------------------------------------------------------
# _validate_tests_against_real
# ---------------------------------------------------------------------------


def test_validate_tests_syntax_error() -> None:
    mock_console = MagicMock()
    result = _validate_tests_against_real(
        "def (broken):", "import fn", Path("/proj"), mock_console
    )
    assert result is False


def test_validate_tests_passes() -> None:
    mock_console = MagicMock()
    with patch("python_pkg.code_tutor._challenge._pytest_clean", return_value=True):
        result = _validate_tests_against_real(
            "def test_fn():\n    assert True\n",
            "# import",
            Path("/proj"),
            mock_console,
        )
    assert result is True


def test_validate_tests_fails() -> None:
    mock_console = MagicMock()
    with patch("python_pkg.code_tutor._challenge._pytest_clean", return_value=False):
        result = _validate_tests_against_real(
            "def test_fn():\n    assert False\n",
            "# import",
            Path("/proj"),
            mock_console,
        )
    assert result is False


# ---------------------------------------------------------------------------
# _collect_and_rate_tests
# ---------------------------------------------------------------------------


def test_collect_and_rate_tests_skip() -> None:
    mock_backend = MagicMock()
    mock_console = MagicMock()
    live_mock = _make_live_mock()

    with patch("python_pkg.code_tutor._challenge_support.Live", return_value=live_mock):
        result = _collect_and_rate_tests(
            "def fn():",
            "explanation",
            mock_backend,
            mock_console,
            lambda _: "skip",
        )
    assert result is None


def test_collect_and_rate_tests_pass_first() -> None:
    mock_backend = MagicMock()
    mock_console = MagicMock()
    live_mock = _make_live_mock()

    def fake_stream(system: str, user: str, on_token: object) -> str:
        assert callable(on_token)
        on_token('{"verdict": "PASS", "gap": ""}')
        return ""

    mock_backend.stream.side_effect = fake_stream
    lines_iter = iter(["test code line", "END"])

    with patch("python_pkg.code_tutor._challenge_support.Live", return_value=live_mock):
        result = _collect_and_rate_tests(
            "def fn():",
            "explanation",
            mock_backend,
            mock_console,
            lambda _: next(lines_iter),
        )
    assert result == "test code line"


def test_collect_and_rate_tests_fail_twice() -> None:
    mock_backend = MagicMock()
    mock_console = MagicMock()
    live_mock = _make_live_mock()

    mock_backend.stream.return_value = '{"verdict": "FAIL", "gap": "bad"}'

    attempt_inputs = [
        # attempt 1: provide code, then END
        "test code",
        "END",
        # attempt 2: provide code, then END
        "test code again",
        "END",
    ]
    inputs_iter = iter(attempt_inputs)

    with patch("python_pkg.code_tutor._challenge_support.Live", return_value=live_mock):
        result = _collect_and_rate_tests(
            "def fn():",
            "explanation",
            mock_backend,
            mock_console,
            lambda _: next(inputs_iter),
        )
    assert result is None


def test_collect_and_rate_tests_fail_then_pass() -> None:
    mock_backend = MagicMock()
    mock_console = MagicMock()
    live_mock = _make_live_mock()

    call_count = [0]

    def fake_stream(system: str, user: str, on_token: object) -> str:
        assert callable(on_token)
        call_count[0] += 1
        verdict = (
            '{"verdict": "FAIL", "gap": "not enough"}'
            if call_count[0] == 1
            else '{"verdict": "PASS", "gap": ""}'
        )
        on_token(verdict)
        return ""

    mock_backend.stream.side_effect = fake_stream

    inputs = iter(["bad test", "END", "good test", "END"])

    with patch("python_pkg.code_tutor._challenge_support.Live", return_value=live_mock):
        result = _collect_and_rate_tests(
            "def fn():",
            "explanation",
            mock_backend,
            mock_console,
            lambda _: next(inputs),
        )
    assert result == "good test"
