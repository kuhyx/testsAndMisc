"""Tests for python_pkg.code_tutor._verifier."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._analyzer import CodeItem
from python_pkg.code_tutor._verifier import (
    Verifier,
    _class_header,
    _parse_verdict,
    _read_snippet,
)

if TYPE_CHECKING:
    from pathlib import Path


def _make_item(
    file: str = "mod.py",
    name: str = "fn",
    start: int = 1,
    end: int = 3,
    class_name: str = "",
) -> CodeItem:
    return CodeItem(
        id=f"{file}.{name}",
        file=file,
        type="function",
        name=name,
        start_line=start,
        end_line=end,
        class_name=class_name,
    )


# ---------------------------------------------------------------------------
# _class_header
# ---------------------------------------------------------------------------


def test_class_header_found() -> None:
    lines = [
        "class Foo:",
        '    """Docstring."""',
        "    x: int",
        "",
        "    def bar(self):",
        "        pass",
    ]
    result = _class_header(lines, "Foo", 5)
    assert "class Foo:" in result


def test_class_header_not_found() -> None:
    lines = ["def bar():", "    pass"]
    result = _class_header(lines, "Missing", 2)
    assert result == ""


def test_class_header_snippet_end_clamped() -> None:
    # Only 3 lines before the method, so snippet_end is clamped to before_line - 1
    lines = ["class A:", "    x = 1", "    def m(self):"]
    result = _class_header(lines, "A", 3)
    assert "class A:" in result


# ---------------------------------------------------------------------------
# _read_snippet
# ---------------------------------------------------------------------------


def test_read_snippet_oserror(tmp_path: Path) -> None:
    item = _make_item(file="missing.py")
    result = _read_snippet(item, str(tmp_path))
    assert "source unavailable" in result


def test_read_snippet_no_class(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text(
        "def fn():\n    pass\n    return 1\n", encoding="utf-8"
    )
    item = _make_item(file="mod.py", start=1, end=3)
    result = _read_snippet(item, str(tmp_path))
    assert "def fn():" in result


def test_read_snippet_with_class_header_found(tmp_path: Path) -> None:
    source = "class Foo:\n    def fn(self):\n        pass\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    item = _make_item(file="mod.py", start=2, end=3, class_name="Foo")
    result = _read_snippet(item, str(tmp_path))
    assert "class Foo" in result
    assert "method" in result


def test_read_snippet_with_class_header_not_found(tmp_path: Path) -> None:
    source = "def fn():\n    pass\n"
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    # class_name is set but not present in file => no header
    item = _make_item(file="mod.py", start=1, end=2, class_name="NoSuchClass")
    result = _read_snippet(item, str(tmp_path))
    assert "def fn():" in result


# ---------------------------------------------------------------------------
# _parse_verdict
# ---------------------------------------------------------------------------


def test_parse_verdict_pass() -> None:
    raw = '{"verdict": "PASS", "gap": ""}'
    verdict, gap = _parse_verdict(raw)
    assert verdict == "PASS"
    assert gap == ""


def test_parse_verdict_fail_with_gap() -> None:
    raw = '{"verdict": "FAIL", "gap": "Missing edge case."}'
    verdict, gap = _parse_verdict(raw)
    assert verdict == "FAIL"
    assert gap == "Missing edge case."


def test_parse_verdict_no_braces() -> None:
    verdict, gap = _parse_verdict("no json here at all")
    assert verdict == "FAIL"
    assert "parse" in gap.lower()


def test_parse_verdict_json_decode_error() -> None:
    verdict, gap = _parse_verdict("{bad json}")
    assert verdict == "FAIL"
    assert "parse" in gap.lower()


def test_parse_verdict_invalid_verdict() -> None:
    raw = '{"verdict": "MAYBE", "gap": "unclear"}'
    verdict, _gap = _parse_verdict(raw)
    assert verdict == "FAIL"


def test_parse_verdict_strips_markdown_fence() -> None:
    raw = '```json\n{"verdict": "PASS", "gap": ""}\n```'
    verdict, _gap = _parse_verdict(raw)
    assert verdict == "PASS"


# ---------------------------------------------------------------------------
# Verifier._judge (via run_lesson)
# ---------------------------------------------------------------------------


def _make_live_mock() -> MagicMock:
    live = MagicMock()
    live.__enter__ = MagicMock(return_value=live)
    live.__exit__ = MagicMock(return_value=False)
    return live


def _make_verifier() -> tuple[Verifier, MagicMock, MagicMock]:
    mock_backend = MagicMock()
    mock_console = MagicMock()
    verifier = Verifier(mock_backend, mock_console)
    return verifier, mock_backend, mock_console


def test_judge_calls_stream_and_parses(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn():\n    pass\n", encoding="utf-8")
    verifier, mock_backend, _ = _make_verifier()

    def fake_stream(system: str, user: str, on_token: object) -> str:
        assert callable(on_token)
        on_token('{"verdict": "PASS", "gap": ""}')
        return ""

    mock_backend.stream.side_effect = fake_stream
    live_mock = _make_live_mock()

    with patch("python_pkg.code_tutor._verifier.Live", return_value=live_mock):
        verdict, _gap = verifier._judge("code snippet", "my explanation")

    assert verdict == "PASS"


# ---------------------------------------------------------------------------
# Verifier._collect_answers
# ---------------------------------------------------------------------------


def test_collect_answers_all_answered() -> None:
    verifier, _, _ = _make_verifier()
    responses = iter(
        ["purpose answer", "inputs answer", "outputs answer", "why answer"]
    )
    answers, skipped = verifier._collect_answers(lambda _: next(responses))
    assert not skipped
    assert len(answers) == 4


def test_collect_answers_skip_on_first() -> None:
    verifier, _, _ = _make_verifier()
    answers, skipped = verifier._collect_answers(lambda _: "skip")
    assert skipped
    assert answers == {}


def test_collect_answers_skip_on_second() -> None:
    verifier, _, _ = _make_verifier()
    call_count = [0]

    def input_fn(_: str) -> str:
        call_count[0] += 1
        if call_count[0] == 2:
            return "skip"
        return "answer"

    _answers, skipped = verifier._collect_answers(input_fn)
    assert skipped


# ---------------------------------------------------------------------------
# Verifier._ask_improvement
# ---------------------------------------------------------------------------


def test_ask_improvement_returns_input() -> None:
    verifier, _, _ = _make_verifier()
    result = verifier._ask_improvement(lambda _: "  make it faster  ")
    assert result == "make it faster"


def test_ask_improvement_empty() -> None:
    verifier, _, _ = _make_verifier()
    result = verifier._ask_improvement(lambda _: "")
    assert result == ""


# ---------------------------------------------------------------------------
# Verifier.run_lesson
# ---------------------------------------------------------------------------


def _four_answers() -> list[str]:
    return ["purpose", "inputs", "outputs", "why"]


def test_run_lesson_pass_first_attempt(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn():\n    pass\n", encoding="utf-8")
    verifier, mock_backend, _ = _make_verifier()

    def fake_stream(system: str, user: str, on_token: object) -> str:
        assert callable(on_token)
        on_token('{"verdict": "PASS", "gap": ""}')
        return ""

    mock_backend.stream.side_effect = fake_stream
    answers_iter = iter(_four_answers())
    live_mock = _make_live_mock()

    with (
        patch("python_pkg.code_tutor._verifier.Live", return_value=live_mock),
        patch(
            "python_pkg.code_tutor._verifier.run_coding_challenge",
            return_value="skipped",
        ),
    ):
        record = verifier.run_lesson(
            _make_item(file="mod.py"),
            str(tmp_path),
            input_fn=lambda _: next(answers_iter, ""),
        )

    assert record.outcome == "learned"
    assert record.verdict == "PASS"
    assert record.attempt == 1


def test_run_lesson_skip_on_first_question(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn():\n    pass\n", encoding="utf-8")
    verifier, _, _ = _make_verifier()
    live_mock = _make_live_mock()

    with patch("python_pkg.code_tutor._verifier.Live", return_value=live_mock):
        record = verifier.run_lesson(
            _make_item(file="mod.py"),
            str(tmp_path),
            input_fn=lambda _: "skip",
        )

    assert record.outcome == "skipped"
    assert record.verdict == "skipped"


def test_run_lesson_all_attempts_fail(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn():\n    pass\n", encoding="utf-8")
    verifier, mock_backend, _ = _make_verifier()
    call_count = [0]

    def fail_stream(system: str, user: str, on_token: object) -> str:
        assert callable(on_token)
        on_token('{"verdict": "FAIL", "gap": "Missing detail."}')
        return ""

    mock_backend.stream.side_effect = fail_stream

    def input_fn(_: str) -> str:
        call_count[0] += 1
        # Each "round" of 4 questions: return an answer
        return "my answer"

    live_mock = _make_live_mock()

    with patch("python_pkg.code_tutor._verifier.Live", return_value=live_mock):
        record = verifier.run_lesson(
            _make_item(file="mod.py"),
            str(tmp_path),
            input_fn=input_fn,
        )

    assert record.outcome == "struggled"
    assert record.verdict == "FAIL"
    assert record.attempt == 3


def test_run_lesson_pass_on_second_attempt(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def fn():\n    pass\n", encoding="utf-8")
    verifier, mock_backend, _ = _make_verifier()

    stream_calls = [0]

    def fake_stream(system: str, user: str, on_token: object) -> str:
        assert callable(on_token)
        stream_calls[0] += 1
        verdict = (
            '{"verdict": "FAIL", "gap": "gap"}'
            if stream_calls[0] == 1
            else '{"verdict": "PASS", "gap": ""}'
        )
        on_token(verdict)
        return ""

    mock_backend.stream.side_effect = fake_stream
    live_mock = _make_live_mock()

    with (
        patch("python_pkg.code_tutor._verifier.Live", return_value=live_mock),
        patch(
            "python_pkg.code_tutor._verifier.run_coding_challenge",
            return_value="passed",
        ),
    ):
        record = verifier.run_lesson(
            _make_item(file="mod.py"),
            str(tmp_path),
            input_fn=lambda _: "my answer",
        )

    assert record.outcome == "learned"
    assert record.attempt == 2
