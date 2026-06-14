"""Tests for the shared ``as_float`` coercion helper."""

from __future__ import annotations

from python_pkg.shared.coerce import as_float


def test_bool_rejected() -> None:
    """Booleans coerce to 0.0 despite subclassing ``int``."""
    true_value: bool = True
    false_value: bool = False
    assert as_float(true_value) == 0.0
    assert as_float(false_value) == 0.0


def test_numeric_coerced() -> None:
    """ints and floats coerce to a float value."""
    assert as_float(3) == 3.0
    assert as_float(2.5) == 2.5


def test_non_numeric_is_zero() -> None:
    """Strings, ``None`` and other types yield 0.0."""
    assert as_float("abc") == 0.0
    assert as_float(None) == 0.0
    assert as_float([1, 2]) == 0.0
