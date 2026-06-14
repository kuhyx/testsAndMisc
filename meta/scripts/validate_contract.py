#!/usr/bin/env python3
"""Validate a workflow-contract artifact against the required schema.

Used by the ``check_agent_contract.sh`` pre-commit hook: given one contract JSON
path as ``argv[1]``, it prints ``<path>: contract schema OK`` and exits 0 when the
file is valid, or writes each problem to stderr and exits 1 otherwise.

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
        if not is_nonempty_str(data.get(key))
    ]


def validate(path: Path) -> list[str]:
    """Return a list of schema problems for ``path`` (empty when it is valid)."""
    data, _text, errors = load_and_check_required(path, _check_required_keys)
    if data is None:
        return errors
    errors += _check_strings(data)
    errors += check_string_lists(data, _STRING_LIST_KEYS, "items")
    return errors


def main() -> int:
    """Validate the contract named by ``argv[1]``; return a process exit code."""
    return run_cli(
        sys.argv[1:],
        usage="usage: validate_contract.py <contract.json>",
        validate=validate,
        success_message="contract schema OK",
    )


if __name__ == "__main__":
    sys.exit(main())
