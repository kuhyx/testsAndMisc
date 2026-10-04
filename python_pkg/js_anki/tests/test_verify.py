"""Tests for python_pkg.js_anki.verify."""

from __future__ import annotations

import dataclasses
import subprocess
from unittest import mock

import pytest

from python_pkg.js_anki.models import Entry
from python_pkg.js_anki.verify import VerificationError, run_examples, verify

ENTRY = Entry(
    family="array",
    method="m",
    tier="core",
    task="t",
    call="c",
    returns="r",
    example="return [1,2];",
    expected="[1,2]",
)


def test_verify_passes_with_real_node() -> None:
    verify(
        [
            ENTRY,
            dataclasses.replace(
                ENTRY, method="u", example="return;", expected="undefined"
            ),
        ]
    )


def test_verify_reports_mismatch() -> None:
    with pytest.raises(VerificationError, match="expected 9"):
        verify([dataclasses.replace(ENTRY, expected="9")])


def test_verify_reports_js_error() -> None:
    with pytest.raises(VerificationError, match="error"):
        verify([dataclasses.replace(ENTRY, example="throw new Error('x');")])


def test_verify_reports_missing_result() -> None:
    with (
        mock.patch("python_pkg.js_anki.verify.run_examples", return_value={}),
        pytest.raises(VerificationError, match="no result"),
    ):
        verify([ENTRY])


def test_node_missing() -> None:
    with (
        mock.patch("python_pkg.js_anki.verify.shutil.which", return_value=None),
        pytest.raises(VerificationError, match="node not found"),
    ):
        run_examples([ENTRY])


def test_node_failure_exit_code() -> None:
    failed = subprocess.CompletedProcess([], 1, stdout="", stderr="boom")
    with (
        mock.patch("python_pkg.js_anki.verify.subprocess.run", return_value=failed),
        pytest.raises(VerificationError, match="boom"),
    ):
        run_examples([ENTRY], node="node")
