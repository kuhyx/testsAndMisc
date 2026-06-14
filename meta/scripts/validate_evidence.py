#!/usr/bin/env python3
"""Validate an AI-evidence artifact against the required schema.

Used by the ``check_ai_evidence.sh`` pre-commit hook: it is given one evidence
JSON path as ``argv[1]``, prints ``<path>: schema OK`` and exits 0 when the file
satisfies the schema, or writes each problem to stderr and exits 1 otherwise.

Kept as a standalone module (not inline ``python <<PY`` in the shell hook) so the
repository's Python tooling applies; see CLAUDE.md "Shell Style".
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from _schema_validation import (
    check_string_lists,
    is_nonempty_str,
    load_and_check_required,
    run_cli,
)

if TYPE_CHECKING:
    from pathlib import Path

# Top-level keys every evidence artifact must define.
_REQUIRED_KEYS = ("intent", "scope", "changes", "verification", "risks", "rollback")
# Keys whose value must be a non-empty list of non-empty strings.
_STRING_LIST_KEYS = ("scope", "changes", "risks", "rollback")
# Fields required on every entry of the "verification" list.
_VERIFICATION_FIELDS = ("command", "result", "evidence")
# Rationalization phrases that must be replaced with concrete evidence.
_BANNED_PHRASES = ("should work", "probably fine", "seems right")


def _check_required_keys(data: dict[str, object]) -> list[str]:
    """Report any required top-level keys that are absent."""
    missing = [key for key in _REQUIRED_KEYS if key not in data]
    if missing:
        return [f"missing required keys: {', '.join(missing)}"]
    return []


def _check_intent(data: dict[str, object]) -> list[str]:
    """The ``intent`` field must be a non-empty string."""
    if not is_nonempty_str(data.get("intent")):
        return ["intent must be a non-empty string"]
    return []


def _check_verification(data: dict[str, object]) -> list[str]:
    """``verification`` must be a non-empty list of fully-populated objects."""
    verification = data.get("verification")
    if not isinstance(verification, list) or not verification:
        return ["verification must be a non-empty list"]
    errors: list[str] = []
    for index, item in enumerate(verification):
        if not isinstance(item, dict):
            errors.append(f"verification[{index}] must be an object")
            continue
        missing = [field for field in _VERIFICATION_FIELDS if field not in item]
        if missing:
            errors.append(f"verification[{index}] missing fields: {', '.join(missing)}")
        bad = [
            field
            for field in _VERIFICATION_FIELDS
            if field in item and not is_nonempty_str(item[field])
        ]
        errors.extend(
            f"verification[{index}].{field} must be a non-empty string" for field in bad
        )
    return errors


def _check_phrases(text: str) -> list[str]:
    """Reject artifacts containing rationalization phrases instead of evidence."""
    lowered = text.lower()
    return [
        f"contains rationalization phrase '{phrase}', replace with evidence"
        for phrase in _BANNED_PHRASES
        if phrase in lowered
    ]


def validate(path: Path) -> list[str]:
    """Return a list of schema problems for ``path`` (empty when it is valid)."""
    data, text, errors = load_and_check_required(path, _check_required_keys)
    if data is None:
        return errors
    errors += _check_intent(data)
    errors += check_string_lists(data, _STRING_LIST_KEYS, "entries")
    errors += _check_verification(data)
    errors += _check_phrases(text)
    return errors


def main() -> int:
    """Validate the artifact named by ``argv[1]``; return a process exit code."""
    return run_cli(
        sys.argv[1:],
        usage="usage: validate_evidence.py <evidence.json>",
        validate=validate,
        success_message="schema OK",
    )


if __name__ == "__main__":
    sys.exit(main())
