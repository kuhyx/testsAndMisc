#!/usr/bin/env python3
"""Shared JSON-schema validation helpers for validate_contract/validate_evidence.

Both CLI scripts validate a JSON artifact against a small required-field schema
and report problems via the same read/parse/dispatch shell. Factored out here so
the duplicated logic is defined once (see pylint duplicate-code).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


def is_nonempty_str(value: object) -> bool:
    """Return True if ``value`` is a string with non-whitespace content."""
    return isinstance(value, str) and bool(value.strip())


def load_and_check_required(
    path: Path,
    check_required: Callable[[dict[str, object]], list[str]],
) -> tuple[dict[str, object] | None, str, list[str]]:
    """Load ``path`` as JSON and verify its required top-level keys are present.

    Returns ``(data, text, [])`` once the file is valid JSON, is an object, and
    ``check_required(data)`` reports no problems. Otherwise returns
    ``(None, "", errors)`` with the relevant problem(s). ``text`` is the raw file
    contents (useful for whole-text checks).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, "", [f"cannot read file ({exc})"]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, "", [f"invalid JSON ({exc})"]
    if not isinstance(data, dict):
        return None, "", ["top-level JSON value must be an object"]

    errors = check_required(data)
    if errors:  # without the required keys present, the per-field checks are noise
        return None, "", errors
    return data, text, []


def check_string_lists(
    data: dict[str, object],
    keys: Sequence[str],
    item_noun: str,
) -> list[str]:
    """Each field in ``keys`` must be a non-empty list of non-empty strings.

    ``item_noun`` (e.g. "items" or "entries") customizes the per-element message.
    """
    errors: list[str] = []
    for key in keys:
        value = data.get(key)
        if not isinstance(value, list) or not value:
            errors.append(f"{key} must be a non-empty list")
            continue
        if any(not is_nonempty_str(item) for item in value):
            errors.append(f"{key} {item_noun} must be non-empty strings")
    return errors


def run_cli(
    argv: Sequence[str],
    *,
    usage: str,
    validate: Callable[[Path], list[str]],
    success_message: str,
) -> int:
    """Validate the path named by ``argv[0]`` and report via stdout/stderr.

    Returns 2 if ``argv`` is empty (usage error), 1 if validation found
    problems, or 0 if the artifact is valid.
    """
    if not argv:
        sys.stderr.write(f"{usage}\n")
        return 2
    path = Path(argv[0])
    errors = validate(path)
    if errors:
        for error in errors:
            sys.stderr.write(f"{path}: {error}\n")
        return 1
    sys.stdout.write(f"{path}: {success_message}\n")
    return 0
