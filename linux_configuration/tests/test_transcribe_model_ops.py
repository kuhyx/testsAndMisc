"""Tests for transcribe.sh's model download and CUDA probe.

Both reach faster_whisper through ``_try_import``, so the package itself is
never needed; the double records how the model would have been constructed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import _transcribe_probes as helpers

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import FakeWhisper
    import pytest


# --------------------------------------------------------------------------- #
# prepare_model / test_cuda
# --------------------------------------------------------------------------- #
def test_prepare_model_downloads_with_cpu_int8(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The model is fetched on CPU in int8, into the requested directory."""
    fw = fake_whisper()
    monkeypatch.setattr(helpers, "_try_import", importer({"faster_whisper": fw}))

    assert helpers.prepare_model("small", "/models") is True
    assert fw.calls == [
        {
            "name": "small",
            "device": "cpu",
            "compute_type": "int8",
            "download_root": "/models",
        }
    ]


def test_prepare_model_enables_progress_bars_when_hub_is_present(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """huggingface_hub progress bars are turned back on for the download."""
    fw = fake_whisper()
    hub_logging = type("L", (), {"set_verbosity_info": lambda self: None})()
    hub = type("H", (), {"constants": type("C", (), {})()})()
    monkeypatch.setattr(
        helpers,
        "_try_import",
        importer(
            {
                "faster_whisper": fw,
                "huggingface_hub.logging": hub_logging,
                "huggingface_hub": hub,
            }
        ),
    )
    monkeypatch.delenv("HF_HUB_DISABLE_PROGRESS_BARS", raising=False)

    assert helpers.prepare_model("small", "/models") is True
    assert hub.constants.HF_HUB_DISABLE_PROGRESS_BARS is False


def test_prepare_model_fails_without_faster_whisper(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Without the package there is nothing to download."""
    monkeypatch.setattr(helpers, "_try_import", importer({}))

    with caplog.at_level(logging.ERROR):
        result = helpers.prepare_model("small", "/models")

    assert result is False
    assert "not installed" in caplog.text


def test_prepare_model_reports_a_download_failure(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A network or disk error is logged and reported, not raised."""

    failing = fake_whisper(error=OSError("no space left"))
    monkeypatch.setattr(helpers, "_try_import", importer({"faster_whisper": failing}))

    with caplog.at_level(logging.ERROR):
        result = helpers.prepare_model("small", "/models")

    assert result is False
    assert "Failed to prepare model" in caplog.text


def test_test_cuda_initialises_a_tiny_model_on_the_gpu(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CUDA probe loads the tiny model in float16 on the GPU."""
    fw = fake_whisper()
    monkeypatch.setattr(helpers, "_try_import", importer({"faster_whisper": fw}))

    assert helpers.test_cuda() is True
    assert fw.calls == [{"name": "tiny", "device": "cuda", "compute_type": "float16"}]


def test_test_cuda_fails_without_faster_whisper(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No package means no CUDA test."""
    monkeypatch.setattr(helpers, "_try_import", importer({}))

    assert helpers.test_cuda() is False


def test_test_cuda_reports_an_unusable_gpu(
    fake_whisper: type[FakeWhisper],
    importer: Callable[[dict[str, object]], object],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A machine without a working CUDA stack reports False, not a crash."""

    no_cuda = fake_whisper(error=RuntimeError("CUDA driver not found"))
    monkeypatch.setattr(helpers, "_try_import", importer({"faster_whisper": no_cuda}))

    with caplog.at_level(logging.ERROR):
        result = helpers.test_cuda()

    assert result is False
    assert "CUDA test failed" in caplog.text
