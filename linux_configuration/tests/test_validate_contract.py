"""Tests for meta/scripts/validate_contract.py (workflow-contract schema checker)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import validate_contract
from validate_contract import main, validate

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _valid() -> dict[str, Any]:
    """Return a minimal contract artifact that satisfies every rule."""
    return {
        "title": "t",
        "objective": "o",
        "acceptance_criteria": ["a"],
        "out_of_scope": ["b"],
        "verifier": "v",
    }


def _write(tmp_path: Path, obj: object) -> Path:
    """Write ``obj`` as JSON to a temp file and return its path."""
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


class TestValidate:
    """The ``validate`` function returns a list of problems."""

    def test_valid_has_no_errors(self, tmp_path: Path) -> None:
        """A fully-populated contract produces no errors."""
        assert validate(_write(tmp_path, _valid())) == []

    def test_missing_fields(self, tmp_path: Path) -> None:
        """Absent top-level fields are reported in one message."""
        errors = validate(_write(tmp_path, {"title": "t"}))
        expected = (
            "missing required fields: objective, acceptance_criteria, "
            "out_of_scope, verifier"
        )
        assert errors == [expected]

    def test_blank_string_field(self, tmp_path: Path) -> None:
        """A blank scalar field is rejected."""
        data = _valid()
        data["objective"] = "  "
        assert "objective must be non-empty string" in validate(_write(tmp_path, data))

    def test_list_field_not_a_list(self, tmp_path: Path) -> None:
        """A list field that is not a list is rejected."""
        data = _valid()
        data["acceptance_criteria"] = "nope"
        assert "acceptance_criteria must be a non-empty list" in validate(
            _write(tmp_path, data),
        )

    def test_list_field_blank_entry(self, tmp_path: Path) -> None:
        """A blank entry inside a list field is rejected."""
        data = _valid()
        data["out_of_scope"] = [""]
        assert "out_of_scope items must be non-empty strings" in validate(
            _write(tmp_path, data),
        )

    def test_non_object_top_level(self, tmp_path: Path) -> None:
        """A non-object top-level JSON value is rejected."""
        assert validate(_write(tmp_path, 5)) == [
            "top-level JSON value must be an object"
        ]

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Malformed JSON is reported, not raised."""
        path = tmp_path / "bad.json"
        path.write_text("{", encoding="utf-8")
        errors = validate(path)
        assert len(errors) == 1
        assert errors[0].startswith("invalid JSON")

    def test_unreadable_path(self, tmp_path: Path) -> None:
        """An unreadable path (a directory) is reported, not raised."""
        errors = validate(tmp_path)
        assert len(errors) == 1
        assert errors[0].startswith("cannot read file")


class TestMain:
    """The CLI entry point maps validation to an exit code."""

    def test_no_argument_returns_2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing the path argument is a usage error (rc 2)."""
        monkeypatch.setattr(validate_contract.sys, "argv", ["validate_contract"])
        assert main() == 2

    def test_valid_returns_0(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A valid contract prints OK and returns 0."""
        path = _write(tmp_path, _valid())
        monkeypatch.setattr(
            validate_contract.sys,
            "argv",
            ["validate_contract", str(path)],
        )
        assert main() == 0
        assert "contract schema OK" in capsys.readouterr().out

    def test_invalid_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """An invalid contract writes the problem to stderr and returns 1."""
        path = _write(tmp_path, {"title": "t"})
        monkeypatch.setattr(
            validate_contract.sys,
            "argv",
            ["validate_contract", str(path)],
        )
        assert main() == 1
        assert "missing required fields" in capsys.readouterr().err
