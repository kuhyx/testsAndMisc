"""Tests for meta/scripts/validate_evidence.py (AI-evidence schema checker)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import validate_evidence
from validate_evidence import main, validate

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _valid() -> dict[str, Any]:
    """Return a minimal evidence artifact that satisfies every rule."""
    return {
        "intent": "do the thing",
        "scope": ["a"],
        "changes": ["a"],
        "risks": ["a"],
        "rollback": ["a"],
        "verification": [{"command": "c", "result": "passed", "evidence": "e"}],
    }


def _write(tmp_path: Path, obj: object) -> Path:
    """Write ``obj`` as JSON to a temp file and return its path."""
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


class TestValidate:
    """The ``validate`` function returns a list of problems."""

    def test_valid_has_no_errors(self, tmp_path: Path) -> None:
        """A fully-populated artifact produces no errors."""
        assert validate(_write(tmp_path, _valid())) == []

    def test_missing_keys(self, tmp_path: Path) -> None:
        """Absent top-level keys are reported in one message."""
        errors = validate(_write(tmp_path, {"intent": "x"}))
        assert errors == [
            "missing required keys: scope, changes, verification, risks, rollback",
        ]

    def test_intent_must_be_nonempty_string(self, tmp_path: Path) -> None:
        """A blank intent is rejected."""
        data = _valid()
        data["intent"] = "   "
        assert "intent must be a non-empty string" in validate(_write(tmp_path, data))

    def test_string_list_not_a_list(self, tmp_path: Path) -> None:
        """A string-list field that is not a list is rejected."""
        data = _valid()
        data["scope"] = "nope"
        assert "scope must be a non-empty list" in validate(_write(tmp_path, data))

    def test_string_list_with_blank_entry(self, tmp_path: Path) -> None:
        """A blank entry inside a string-list field is rejected."""
        data = _valid()
        data["changes"] = ["ok", "  "]
        assert "changes entries must be non-empty strings" in validate(
            _write(tmp_path, data),
        )

    def test_verification_not_a_list(self, tmp_path: Path) -> None:
        """A non-list verification field is rejected."""
        data = _valid()
        data["verification"] = {}
        assert "verification must be a non-empty list" in validate(
            _write(tmp_path, data),
        )

    def test_verification_item_not_object(self, tmp_path: Path) -> None:
        """A non-object verification entry is rejected."""
        data = _valid()
        data["verification"] = ["nope"]
        assert "verification[0] must be an object" in validate(_write(tmp_path, data))

    def test_verification_missing_fields(self, tmp_path: Path) -> None:
        """Missing per-entry fields are reported."""
        data = _valid()
        data["verification"] = [{"command": "c"}]
        errors = validate(_write(tmp_path, data))
        assert "verification[0] missing fields: result, evidence" in errors

    def test_verification_blank_field(self, tmp_path: Path) -> None:
        """A blank per-entry field is rejected."""
        data = _valid()
        data["verification"] = [{"command": "c", "result": " ", "evidence": "e"}]
        errors = validate(_write(tmp_path, data))
        assert "verification[0].result must be a non-empty string" in errors

    def test_banned_phrase(self, tmp_path: Path) -> None:
        """A rationalization phrase anywhere in the file is rejected."""
        data = _valid()
        data["verification"] = [
            {"command": "c", "result": "should work", "evidence": "e"},
        ]
        errors = validate(_write(tmp_path, data))
        assert any("rationalization phrase 'should work'" in e for e in errors)

    def test_non_object_top_level(self, tmp_path: Path) -> None:
        """A non-object top-level JSON value is rejected."""
        assert validate(_write(tmp_path, [1, 2])) == [
            "top-level JSON value must be an object",
        ]

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Malformed JSON is reported, not raised."""
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
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
        monkeypatch.setattr(validate_evidence.sys, "argv", ["validate_evidence"])
        assert main() == 2

    def test_valid_returns_0(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A valid artifact prints OK and returns 0."""
        path = _write(tmp_path, _valid())
        monkeypatch.setattr(
            validate_evidence.sys,
            "argv",
            ["validate_evidence", str(path)],
        )
        assert main() == 0
        assert "schema OK" in capsys.readouterr().out

    def test_invalid_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """An invalid artifact writes the problem to stderr and returns 1."""
        path = _write(tmp_path, {"intent": "x"})
        monkeypatch.setattr(
            validate_evidence.sys,
            "argv",
            ["validate_evidence", str(path)],
        )
        assert main() == 1
        assert "missing required keys" in capsys.readouterr().err
