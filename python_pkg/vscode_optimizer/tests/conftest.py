"""Shared doubles for the hardware-probe tests.

``name-tests-test`` requires every module under a tests directory to be named
``test_*.py``, so helpers shared between test modules live here rather than in
a helper module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class FakeProc:
    """Stand-in for the CompletedProcess ``_run`` inspects."""

    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def fake_run(mapping: dict[str, str]) -> Callable[..., FakeProc]:
    """Return a ``subprocess.run`` double keyed on the executable name.

    Commands absent from *mapping* return empty stdout, which is how the
    probes see a tool that is installed but reports nothing.
    """

    def _run(args: list[str], **_kw: object) -> FakeProc:
        return FakeProc(mapping.get(args[0], ""))

    return _run
