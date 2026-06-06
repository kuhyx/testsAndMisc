#!/usr/bin/env python3
"""Validate a workflow-contract artifact against the required schema.

Used by the ``check_agent_contract.sh`` pre-commit hook: given one contract JSON
path as ``argv[1]``, it prints ``<path>: contract schema OK`` and exits 0 when the
file is valid, or writes each problem to stderr and exits 1 otherwise.

Kept as a standalone module (not inline ``python <<PY`` in the shell hook) so the
repository's Python tooling applies; see CLAUDE.md "Shell Style".
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

# Top-level keys every contract must define.
_REQUIRED_KEYS = (
    "title",
    "objective",
    "acceptance_criteria",
    "out_of_scope",
    "verifier",
)
# Keys whose value must be a non-empty string.
_STRING_KEYS = ("title", "objective", "verifier")
# Keys whose value must be a non-empty list of non-empty strings.
_STRING_LIST_KEYS = ("acceptance_criteria", "out_of_scope")


def _is_nonempty_str(value: object) -> bool:
    """Return True if ``value`` is a string with non-whitespace content."""
    return isinstance(value, str) and bool(value.strip())


def _check_required_keys(data: dict[str, object]) -> list[str]:
    """Report any required top-level keys that are absent."""
    missing = [key for key in _REQUIRED_KEYS if key not in data]
    if missing:
        return [f"missing required fields: {', '.join(missing)}"]
    return []


def _check_strings(data: dict[str, object]) -> list[str]:
    """Each scalar field must be a non-empty string."""
    return [
        f"{key} must be non-empty string"
        for key in _STRING_KEYS
        if not _is_nonempty_str(data.get(key))
    ]


def _check_string_lists(data: dict[str, object]) -> list[str]:
    """Each list field must be a non-empty list of non-empty strings."""
    errors: list[str] = []
    for key in _STRING_LIST_KEYS:
        value = data.get(key)
        if not isinstance(value, list) or not value:
            errors.append(f"{key} must be a non-empty list")
            continue
        if any(not _is_nonempty_str(item) for item in value):
            errors.append(f"{key} items must be non-empty strings")
    return errors


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
    errors += _check_strings(data)
    errors += _check_string_lists(data)
    return errors


def main() -> int:
    """Validate the contract named by ``argv[1]``; return a process exit code."""
    args = sys.argv[1:]
    if not args:
        sys.stderr.write("usage: validate_contract.py <contract.json>\n")
        return 2
    path = Path(args[0])
    errors = validate(path)
    if errors:
        for error in errors:
            sys.stderr.write(f"{path}: {error}\n")
        return 1
    sys.stdout.write(f"{path}: contract schema OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
