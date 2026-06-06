#!/usr/bin/env python3
"""Validate an AI-evidence artifact against the required schema.

Used by the ``check_ai_evidence.sh`` pre-commit hook: it is given one evidence
JSON path as ``argv[1]``, prints ``<path>: schema OK`` and exits 0 when the file
satisfies the schema, or writes each problem to stderr and exits 1 otherwise.

Kept as a standalone module (not inline ``python <<PY`` in the shell hook) so the
repository's Python tooling applies; see CLAUDE.md "Shell Style".
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

# Top-level keys every evidence artifact must define.
_REQUIRED_KEYS = ("intent", "scope", "changes", "verification", "risks", "rollback")
# Keys whose value must be a non-empty list of non-empty strings.
_STRING_LIST_KEYS = ("scope", "changes", "risks", "rollback")
# Fields required on every entry of the "verification" list.
_VERIFICATION_FIELDS = ("command", "result", "evidence")
# Rationalization phrases that must be replaced with concrete evidence.
_BANNED_PHRASES = ("should work", "probably fine", "seems right")


def _is_nonempty_str(value: object) -> bool:
    """Return True if ``value`` is a string with non-whitespace content."""
    return isinstance(value, str) and bool(value.strip())


def _check_required_keys(data: dict[str, object]) -> list[str]:
    """Report any required top-level keys that are absent."""
    missing = [key for key in _REQUIRED_KEYS if key not in data]
    if missing:
        return [f"missing required keys: {', '.join(missing)}"]
    return []


def _check_intent(data: dict[str, object]) -> list[str]:
    """The ``intent`` field must be a non-empty string."""
    if not _is_nonempty_str(data.get("intent")):
        return ["intent must be a non-empty string"]
    return []


def _check_string_lists(data: dict[str, object]) -> list[str]:
    """Each string-list field must be a non-empty list of non-empty strings."""
    errors: list[str] = []
    for key in _STRING_LIST_KEYS:
        value = data.get(key)
        if not isinstance(value, list) or not value:
            errors.append(f"{key} must be a non-empty list")
            continue
        if any(not _is_nonempty_str(item) for item in value):
            errors.append(f"{key} entries must be non-empty strings")
    return errors


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
            if field in item and not _is_nonempty_str(item[field])
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
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read file ({exc})"]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON ({exc})"]
    if not isinstance(data, dict):
        return ["top-level JSON value must be an object"]

    errors = _check_required_keys(data)
    if errors:  # without the keys present, the per-field checks are noise
        return errors
    errors += _check_intent(data)
    errors += _check_string_lists(data)
    errors += _check_verification(data)
    errors += _check_phrases(text)
    return errors


def main() -> int:
    """Validate the artifact named by ``argv[1]``; return a process exit code."""
    args = sys.argv[1:]
    if not args:
        sys.stderr.write("usage: validate_evidence.py <evidence.json>\n")
        return 2
    path = Path(args[0])
    errors = validate(path)
    if errors:
        for error in errors:
            sys.stderr.write(f"{path}: {error}\n")
        return 1
    sys.stdout.write(f"{path}: schema OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
