"""Tests for transcribe.sh's dependency probes.

The ML dependencies (faster_whisper, torch, speechbrain, soundfile,
ctranslate2) are never installed in CI, and the module reaches them only
through ``_try_import``. Patching that one seam is what lets every probe be
tested in both directions without the real packages.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import _transcribe_probes as helpers
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import FakeWhisper


# --------------------------------------------------------------------------- #
# The optional-dependency import seam
# --------------------------------------------------------------------------- #
def test_try_import_returns_the_module_when_present() -> None:
    """A real, importable module comes back as a module object."""
    assert helpers._try_import("json") is not None


def test_try_import_returns_none_for_a_missing_module() -> None:
    """A missing optional dependency is None, not an ImportError."""
    assert helpers._try_import("no_such_module_anywhere_12345") is None


# --------------------------------------------------------------------------- #
# dependency probes
# --------------------------------------------------------------------------- #
def test_get_python_version_reports_major_minor() -> None:
    """The version string is major.minor, which is what transcribe.sh parses."""
    version = helpers.get_python_version()

    major, _, minor = version.partition(".")
    assert major.isdigit()
    assert minor.isdigit()


@pytest.mark.parametrize("present", [True, False])
def test_check_faster_whisper_reports_availability(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    monkeypatch: pytest.MonkeyPatch,
    *,
    present: bool,
) -> None:
    """The probe is True only when faster_whisper imports."""
    available = {"faster_whisper": fake_whisper()} if present else {}
    monkeypatch.setattr(helpers, "_try_import", importer(available))

    assert helpers.check_faster_whisper() is present


@pytest.mark.parametrize("present", [True, False])
def test_check_ctranslate2_reports_availability(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    monkeypatch: pytest.MonkeyPatch,
    *,
    present: bool,
) -> None:
    """The probe is True only when ctranslate2 imports."""
    available = {"ctranslate2": object()} if present else {}
    monkeypatch.setattr(helpers, "_try_import", importer(available))

    assert helpers.check_ctranslate2() is present


def test_check_diarization_deps_needs_all_three(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Diarization needs soundfile, speechbrain and torch together."""
    monkeypatch.setattr(
        helpers,
        "_try_import",
        importer({"soundfile": object(), "speechbrain": object(), "torch": object()}),
    )

    assert helpers.check_diarization_deps() is True


@pytest.mark.parametrize("missing", ["soundfile", "speechbrain", "torch"])
def test_check_diarization_deps_warns_when_one_is_missing(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    missing: str,
) -> None:
    """Any one absent dependency downgrades to a warning, not a failure."""
    available: dict[str, object] = {
        name: object()
        for name in ("soundfile", "speechbrain", "torch")
        if name != missing
    }
    monkeypatch.setattr(helpers, "_try_import", importer(available))

    with caplog.at_level(logging.WARNING):
        result = helpers.check_diarization_deps()

    assert result is False
    assert "speaker labels will be skipped" in caplog.text


def test_print_deps_installed_names_the_interpreter(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The confirmation line carries the running Python version."""
    with caplog.at_level(logging.INFO):
        helpers.print_deps_installed()

    assert "dependencies installed" in caplog.text
