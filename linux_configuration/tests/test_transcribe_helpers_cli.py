"""Tests for the transcribe_helpers command-line dispatch.

transcribe.sh calls this module as a subcommand runner and branches on the
exit status, so the codes are the contract: 7 means "faster_whisper missing",
2 means "required argument missing", 1 means "the operation failed".
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import pytest
import transcribe_helpers as helpers

if TYPE_CHECKING:
    from pathlib import Path

_EXIT_MISSING_ARG = 2
_EXIT_NO_FASTER_WHISPER = 7


def _run(monkeypatch: pytest.MonkeyPatch, *argv: str) -> None:
    """Invoke main() with the given command line."""
    monkeypatch.setattr(sys, "argv", ["transcribe_helpers.py", *argv])
    helpers.main()


# --------------------------------------------------------------------------- #
# commands that report through the exit status
# --------------------------------------------------------------------------- #
def test_python_version_prints_and_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """transcribe.sh parses this to decide which wheels to install."""
    with caplog.at_level(logging.INFO):
        _run(monkeypatch, "python-version")

    assert helpers.get_python_version() in caplog.text


def test_check_faster_whisper_exits_7_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exit 7 is the offline-mode signal transcribe.sh branches on."""
    monkeypatch.setattr(helpers, "check_faster_whisper", lambda: False)

    with pytest.raises(SystemExit) as excinfo:
        _run(monkeypatch, "check-faster-whisper")

    assert excinfo.value.code == _EXIT_NO_FASTER_WHISPER


def test_check_faster_whisper_is_silent_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A satisfied dependency exits 0, so the shell continues."""
    monkeypatch.setattr(helpers, "check_faster_whisper", lambda: True)

    _run(monkeypatch, "check-faster-whisper")


def test_check_diarization_never_fails_the_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing diarization deps only warn: speaker labels are optional."""
    monkeypatch.setattr(helpers, "check_diarization_deps", lambda: False)

    _run(monkeypatch, "check-diarization")


@pytest.mark.parametrize(("available", "raises"), [(True, False), (False, True)])
def test_check_ctranslate2_exits_1_when_absent(
    monkeypatch: pytest.MonkeyPatch, *, available: bool, raises: bool
) -> None:
    """ctranslate2 is required, so its absence is a hard failure."""
    monkeypatch.setattr(helpers, "check_ctranslate2", lambda: available)

    if raises:
        with pytest.raises(SystemExit) as excinfo:
            _run(monkeypatch, "check-ctranslate2")
        assert excinfo.value.code == 1
    else:
        _run(monkeypatch, "check-ctranslate2")


def test_deps_installed_reports_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """The confirmation command exits 0."""
    _run(monkeypatch, "deps-installed")


# --------------------------------------------------------------------------- #
# commands taking arguments
# --------------------------------------------------------------------------- #
def test_generate_wav_writes_the_requested_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The --file argument is passed through to the generator."""
    out = tmp_path / "tone.wav"

    _run(monkeypatch, "generate-wav", "--file", str(out))

    assert out.exists()


def test_generate_wav_requires_a_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Omitting --file is a usage error, exit 2."""
    with pytest.raises(SystemExit) as excinfo:
        _run(monkeypatch, "generate-wav")

    assert excinfo.value.code == _EXIT_MISSING_ARG


def test_generate_wav_exits_1_when_generation_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A generator failure surfaces as exit 1."""
    monkeypatch.setattr(helpers, "generate_sine_wav", lambda _f: False)

    with pytest.raises(SystemExit) as excinfo:
        _run(monkeypatch, "generate-wav", "--file", str(tmp_path / "x.wav"))

    assert excinfo.value.code == 1


def test_prepare_model_passes_both_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--model and --model-dir reach prepare_model unchanged."""
    seen: list[tuple[str, str]] = []

    def _record(model: str, model_dir: str) -> bool:
        seen.append((model, model_dir))
        return True

    monkeypatch.setattr(helpers, "prepare_model", _record)

    _run(monkeypatch, "prepare-model", "--model", "small", "--model-dir", "/m")

    assert seen == [("small", "/m")]


@pytest.mark.parametrize(
    "argv",
    [
        ("prepare-model",),
        ("prepare-model", "--model", "small"),
        ("prepare-model", "--model-dir", "/m"),
    ],
)
def test_prepare_model_requires_both_arguments(
    monkeypatch: pytest.MonkeyPatch, argv: tuple[str, ...]
) -> None:
    """Either argument missing is a usage error, exit 2."""
    with pytest.raises(SystemExit) as excinfo:
        _run(monkeypatch, *argv)

    assert excinfo.value.code == _EXIT_MISSING_ARG


def test_prepare_model_exits_1_on_download_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed download surfaces as exit 1."""
    monkeypatch.setattr(helpers, "prepare_model", lambda _m, _d: False)

    with pytest.raises(SystemExit) as excinfo:
        _run(monkeypatch, "prepare-model", "--model", "small", "--model-dir", "/m")

    assert excinfo.value.code == 1


@pytest.mark.parametrize(("works", "raises"), [(True, False), (False, True)])
def test_test_cuda_reports_through_the_exit_status(
    monkeypatch: pytest.MonkeyPatch, *, works: bool, raises: bool
) -> None:
    """transcribe.sh falls back to CPU when this exits non-zero."""
    monkeypatch.setattr(helpers, "test_cuda", lambda: works)

    if raises:
        with pytest.raises(SystemExit) as excinfo:
            _run(monkeypatch, "test-cuda")
        assert excinfo.value.code == 1
    else:
        _run(monkeypatch, "test-cuda")


def test_an_unknown_command_is_rejected_by_argparse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The choices list means a typo cannot silently do nothing."""
    with pytest.raises(SystemExit) as excinfo:
        _run(monkeypatch, "not-a-command")

    assert excinfo.value.code == _EXIT_MISSING_ARG


def test_a_command_with_no_handler_is_a_no_op(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The dispatch guard tolerates a choice with no handler behind it.

    Unreachable through the CLI today, because argparse's ``choices`` list and
    the dispatch dict carry the same eight commands. It is exercised here by
    accepting a ninth choice, so that adding a command to one list but not the
    other degrades to doing nothing rather than raising.
    """
    real_parse_args = helpers.argparse.ArgumentParser.parse_args

    def _parse_with_extra_choice(
        self: helpers.argparse.ArgumentParser, *args: object, **kwargs: object
    ) -> helpers.argparse.Namespace:
        for action in self._actions:
            if action.dest == "command" and action.choices is not None:
                action.choices = [*action.choices, "unhandled"]
        return real_parse_args(self, *args, **kwargs)

    monkeypatch.setattr(
        helpers.argparse.ArgumentParser, "parse_args", _parse_with_extra_choice
    )

    _run(monkeypatch, "unhandled")
