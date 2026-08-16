"""Tests for Verifier.run_lesson."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from python_pkg.code_tutor._analyzer import CodeItem
from python_pkg.code_tutor.tests.conftest import _make_live_mock, _make_verifier

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
