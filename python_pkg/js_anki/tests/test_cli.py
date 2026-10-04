"""Tests for python_pkg.js_anki.cli."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from python_pkg.js_anki.cli import main
from python_pkg.js_anki.verify import VerificationError


def test_build_writes_apkg(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "sub" / "deck.apkg"
    assert main(["build", "--out", str(out)]) == 0
    assert out.stat().st_size > 0
    assert "cards to" in capsys.readouterr().out


def test_build_fails_on_verification_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "deck.apkg"
    with mock.patch(
        "python_pkg.js_anki.cli.verify", side_effect=VerificationError("bad")
    ):
        assert main(["build", "--out", str(out)]) == 1
    assert not out.exists()
    assert "verification FAILED" in capsys.readouterr().err
