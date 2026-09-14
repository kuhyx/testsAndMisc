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
    _REPO_ROOT / "linux_configuration" / "utils",  # fast_count
    _REPO_ROOT / "linux_configuration" / "fixes",  # g29_shifter_capture
    _REPO_ROOT
    / "linux_configuration"
    / "misc"
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


@pytest.fixture
def g29() -> type[G29Reports]:
    """Raw/xxd G29 report builders for the shifter-grader tests."""
    return G29Reports


class G29Reports:
    """Builders for 12-byte G29 input reports with chosen gear and hall values."""

    NEUTRAL_Y = 105
    TOP_Y = 200
    BOTTOM_Y = 45
    X_LEFT = 60
    X_CENTRE = 120
    X_RIGHT = 180

    @classmethod
    def raw_report(
        cls,
        gears: int = 0,
        x: int | None = None,
        y: int | None = None,
        *,
        down: bool = False,
    ) -> bytearray:
        """One raw input report; X/Y default to the centred, neutral stick."""
        import g29_shifter_capture as gsc

        raw = bytearray(gsc.REPORT_LEN)
        raw[2] = gears
        raw[9] = cls.X_CENTRE if x is None else x
        raw[10] = cls.NEUTRAL_Y if y is None else y
        raw[11] = 0x40 if down else 0x00
        return raw

    @classmethod
    def xxd_line(
        cls,
        gears: int = 0,
        x: int | None = None,
        y: int | None = None,
        *,
        down: bool = False,
    ) -> str:
        """The same report as one ``xxd -c 12`` line."""
        raw = cls.raw_report(gears, x, y, down=down)
        words = " ".join(raw[i : i + 2].hex() for i in range(0, len(raw), 2))
        return f"00000000: {words}\n"

    @staticmethod
    def parse_lines(lines: list[str]) -> list[object]:
        """Parse xxd lines into Report objects."""
        import g29_shifter_capture as gsc

        return list(gsc.parse(lines))
