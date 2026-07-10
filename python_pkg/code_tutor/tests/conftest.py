"""Shared factory helpers for the ``_challenge`` / ``_challenge_support`` tests.

Kept in ``conftest.py`` (a single, import-safe location) so the split test
modules (``test_challenge``, ``test_challenge_part2``, ``test_challenge_part3``)
reuse one definition instead of duplicating the factories, which would trip
pylint's ``duplicate-code`` check.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from python_pkg.code_tutor._analyzer import CodeItem


def _item(
    file: str = "mod.py",
    name: str = "fn",
    start: int = 1,
    end: int = 3,
    class_name: str = "",
) -> CodeItem:
    """Build a ``CodeItem`` with sensible defaults for tests.

    Args:
        file: Relative source-file path for the item.
        name: Function name.
        start: 1-based start line of the item.
        end: 1-based end line of the item.
        class_name: Owning class name, or empty for module-level functions.

    Returns:
        A populated ``CodeItem`` instance.
    """
    return CodeItem(
        id=f"{file}.{name}",
        file=file,
        type="function",
        name=name,
        start_line=start,
        end_line=end,
        class_name=class_name,
    )


def _make_live_mock() -> MagicMock:
    """Return a ``MagicMock`` that behaves like a ``rich.live.Live`` context.

    Returns:
        A mock whose ``__enter__`` yields itself and whose ``__exit__``
        returns ``False`` so exceptions propagate normally.
    """
    live = MagicMock()
    live.__enter__ = MagicMock(return_value=live)
    live.__exit__ = MagicMock(return_value=False)
    return live
