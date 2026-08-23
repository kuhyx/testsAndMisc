"""Pytest bootstrap: make non-package script dirs importable for these tests.

Several helper modules live in standalone script directories (outside
``python_pkg/``) and are invoked as ``python <file>.py`` rather than imported as
packages. To unit-test them they must be importable by bare module name, so each
directory is placed on ``sys.path`` before the tests import them.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

# Repo root is two levels up from this file (linux_configuration/tests/conftest.py).
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Each standalone script directory whose Python modules these tests import.
_SCRIPT_DIRS = (
    _REPO_ROOT / "meta" / "scripts",  # validate_evidence, validate_contract
    _REPO_ROOT
    / "linux_configuration"
    / "scripts"
    / "single_use"
    / "utils",  # fast_count
    _REPO_ROOT
    / "linux_configuration"
    / "scripts"
    / "single_use"
    / "misc"
    / "testsAndMisc-bash"
    / "tools",  # transcribe_fw and its helpers
)

for _script_dir in _SCRIPT_DIRS:
    if str(_script_dir) not in sys.path:
        sys.path.insert(0, str(_script_dir))


@pytest.fixture
def fake_whisper() -> type[FakeWhisper]:
    """The faster_whisper double, as a fixture (conftest is not importable)."""
    return FakeWhisper


@pytest.fixture
def importer() -> Callable[[dict[str, object]], object]:
    """The ``_try_import`` double factory, as a fixture."""
    return fake_importer


class FakeWhisper:
    """Stand-in for faster_whisper, recording how a model was constructed.

    ``WhisperModel`` is upstream's CamelCase name, so it is exposed through
    ``__getattr__`` rather than defined as a method: defining it would mean
    naming a non-PEP8 identifier here just to satisfy a third-party API.
    """

    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self._error = error

    def _construct(self, name: str, **kwargs: object) -> object:
        if self._error is not None:
            raise self._error
        self.calls.append({"name": name, **kwargs})
        return object()

    def __getattr__(self, attr: str) -> object:
        if attr == "WhisperModel":
            return self._construct
        raise AttributeError(attr)


def fake_importer(available: dict[str, object]) -> object:
    """Return a ``_try_import`` double resolving only the named modules."""

    def _try(name: str) -> object | None:
        return available.get(name)

    return _try
