"""Tests for linux_configuration/.../utils/fast_count.py (stdin word counter)."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import fast_count
from fast_count import main

if TYPE_CHECKING:
    import pytest


def _run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stdin_text: str,
    argv: list[str],
) -> str:
    """Run ``main`` with a fake stdin and argv; return captured stdout."""
    monkeypatch.setattr(fast_count.sys, "stdin", io.StringIO(stdin_text))
    monkeypatch.setattr(fast_count.sys, "argv", argv)
    assert main() == 0
    return capsys.readouterr().out


class TestMain:
    """``fast_count`` prints ``<count> <line>`` for the top-N frequent lines."""

    def test_top_n_ordering(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """The N most common lines are printed most-frequent first."""
        out = _run(
            monkeypatch, capsys, "if\nif\nfor\nif\nfor\nreturn\n", ["fast_count", "2"]
        )
        assert out == "3 if\n2 for\n"

    def test_strips_trailing_whitespace(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Lines differing only by trailing whitespace are counted together."""
        out = _run(monkeypatch, capsys, "x  \nx\n", ["fast_count", "1"])
        assert out == "2 x\n"

    def test_default_top_n_without_arg(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """With no argument the default top-N applies."""
        out = _run(monkeypatch, capsys, "a\na\nb\n", ["fast_count"])
        assert out == "2 a\n1 b\n"
