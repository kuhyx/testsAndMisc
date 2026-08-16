"""Defensive accessors for the loosely-typed /wsg/ JSON payloads.

The API omits file fields entirely on posts without an attachment and is fed by
an anonymous imageboard, so nothing here trusts the shape of what it is handed:
every accessor answers "not usable" rather than raising.
"""

from __future__ import annotations

import re
from typing import Any

# base64 of a 16-byte digest is always 22 characters plus "==". Matching the
# exact shape -- not merely the length -- is what keeps a NUL byte out of a
# filename: one such value poisons the index permanently, because the crash
# happens before the row can ever be marked gone.
_MD5_SHAPE = re.compile(r"[A-Za-z0-9+/]{22}==")

# sqlite stores signed 64-bit integers; anything wider raises OverflowError deep
# inside executemany, which used to take the worker thread down with it.
_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1


def get(container: object, key: str) -> object:
    """Read *key* from *container* when it is a mapping.

    Args:
        container: Anything; only dicts yield a value.
        key: Key to read.

    Returns:
        object: The value, or None.
    """
    if isinstance(container, dict):
        return container.get(key)
    return None


def as_list(value: object) -> list[Any]:
    """Return *value* when it is a list, else an empty list.

    Args:
        value: Candidate.

    Returns:
        list[Any]: Safe list to iterate.
    """
    return value if isinstance(value, list) else []


def as_int(value: object) -> int | None:
    """Coerce *value* to int when it is a real integer.

    Booleans are rejected: ``True`` is an int in Python but never a valid post
    number or timestamp. Values outside sqlite's signed 64-bit range are
    rejected too -- they raise OverflowError on insert, which is not in the
    worker's recoverable set and would kill it silently.

    Args:
        value: Candidate.

    Returns:
        int | None: The integer, or None.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if _INT64_MIN <= value <= _INT64_MAX else None


def as_md5(value: object) -> str | None:
    """Validate the API's base64 md5 field.

    The charset check is not decoration: the tail of this value ends up in a
    filename via ``store.local_name``, and it arrives from an anonymous
    imageboard. Length alone would let through a NUL byte, which raises deep
    inside the filesystem call instead of being rejected here.

    Args:
        value: Candidate.

    Returns:
        str | None: The 24-character digest, or None when malformed.
    """
    if not isinstance(value, str):
        return None
    return value if _MD5_SHAPE.fullmatch(value) else None
