"""Tests for the command runner and for CPU and RAM detection.

``_run`` shells out, so ``subprocess.run`` is patched at the boundary, and
``_detect_ram``'s hardcoded ``/proc/meminfo`` is redirected by patching the
module-level ``Path`` name. Nothing here reads the machine's real hardware.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from python_pkg.vscode_optimizer import _optimize as opt
from python_pkg.vscode_optimizer.tests.conftest import FakeProc as _Proc
from python_pkg.vscode_optimizer.tests.conftest import fake_run as _fake_run

if TYPE_CHECKING:
    from pathlib import Path

_LSCPU_OUT = """\
Architecture:                       x86_64
Model name:                         AMD Ryzen 9 7900X3D 12-Core Processor
CPU(s):                             24
Core(s) per socket:                 12
CPU max MHz:                        5662.5000
"""


# --------------------------------------------------------------------------- #
# _run
# --------------------------------------------------------------------------- #
def test_run_returns_stripped_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful command hands back its stdout without surrounding space."""
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: _Proc("  out  \n"))

    assert opt._run(["anything"]) == "out"


@pytest.mark.parametrize(
    "error",
    [subprocess.TimeoutExpired(cmd="x", timeout=10), FileNotFoundError()],
)
def test_run_returns_empty_when_the_command_fails(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    """A missing binary or a timeout degrades to an empty string, not a crash."""

    def _boom(*_a: object, **_k: object) -> None:
        raise error

    monkeypatch.setattr(subprocess, "run", _boom)

    assert opt._run(["anything"]) == ""


# --------------------------------------------------------------------------- #
# _detect_cpu
# --------------------------------------------------------------------------- #
def test_detect_cpu_reads_model_cores_and_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each recognised lscpu key lands on its typed _Hw attribute."""
    monkeypatch.setattr(subprocess, "run", _fake_run({"lscpu": _LSCPU_OUT}))
    hw = opt._Hw()

    opt._detect_cpu(hw)

    assert hw.cpu_model == "AMD Ryzen 9 7900X3D 12-Core Processor"
    assert hw.cpu_logical_cores == 24
    assert hw.cpu_physical_cores == 12
    assert hw.cpu_max_mhz == pytest.approx(5662.5)


def test_detect_cpu_ignores_unknown_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lines outside the _LSCPU map leave the defaults alone."""
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_run({"lscpu": "Architecture: x86_64\nBogoMIPS: 9000\n"}),
    )
    hw = opt._Hw()

    opt._detect_cpu(hw)

    assert hw.cpu_model == "Unknown"
    assert hw.cpu_physical_cores == 1


# --------------------------------------------------------------------------- #
# _detect_ram
# --------------------------------------------------------------------------- #
def test_detect_ram_converts_kb_to_mb(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """MemTotal in kB becomes whole MB."""
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal:       32768000 kB\nMemFree: 100 kB\n")
    monkeypatch.setattr(opt, "Path", lambda _p: meminfo)
    hw = opt._Hw()

    opt._detect_ram(hw)

    assert hw.ram_total_mb == 32000


def test_detect_ram_leaves_zero_when_memtotal_is_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A procfs file without MemTotal is not an error, just no reading."""
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("SwapTotal: 4096 kB\n")
    monkeypatch.setattr(opt, "Path", lambda _p: meminfo)
    hw = opt._Hw()

    opt._detect_ram(hw)

    assert hw.ram_total_mb == 0


def test_detect_ram_survives_an_unreadable_procfs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An OSError reading /proc/meminfo leaves the default in place."""
    monkeypatch.setattr(opt, "Path", lambda _p: tmp_path / "does-not-exist")
    hw = opt._Hw()

    opt._detect_ram(hw)

    assert hw.ram_total_mb == 0
