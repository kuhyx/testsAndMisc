"""Tests for GPU and root-disk detection, and the aggregate probe.

Both probes shell out, so ``subprocess.run`` is patched at the boundary; the
sysfs reads in ``_detect_disk`` are redirected by patching the module-level
``Path`` name. Nothing here touches the machine's real hardware.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from python_pkg.vscode_optimizer import _optimize as opt
from python_pkg.vscode_optimizer.tests.conftest import fake_run as _fake_run

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


# --------------------------------------------------------------------------- #
# _detect_gpu
# --------------------------------------------------------------------------- #
_NVIDIA_LINE = (
    "01:00.0 VGA compatible controller: NVIDIA Corporation GA102 [GeForce RTX 3090]"
)


def test_detect_gpu_reads_nvidia_vram(monkeypatch: pytest.MonkeyPatch) -> None:
    """An NVIDIA card triggers a second probe for its VRAM."""
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_run({"lspci": _NVIDIA_LINE, "nvidia-smi": "24576\n"}),
    )
    hw = opt._Hw()

    opt._detect_gpu(hw)

    assert hw.gpu_vendor == "NVIDIA"
    assert hw.gpu_model == "NVIDIA Corporation GA102 [GeForce RTX 3090]"
    assert hw.gpu_vram_mb == 24576


def test_detect_gpu_tolerates_nvidia_smi_being_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without nvidia-smi the vendor is still known; VRAM stays unset."""
    monkeypatch.setattr(subprocess, "run", _fake_run({"lspci": _NVIDIA_LINE}))
    hw = opt._Hw()

    opt._detect_gpu(hw)

    assert hw.gpu_vendor == "NVIDIA"
    assert hw.gpu_vram_mb == 0


@pytest.mark.parametrize(
    ("line", "vendor"),
    [
        ("03:00.0 VGA compatible controller: AMD Radeon RX 7900", "AMD"),
        ("03:00.0 VGA compatible controller: ATI Technologies Inc", "AMD"),
        # Characterisation, not endorsement: see the xfail below. Every real
        # lspci display line contains "VGA compATIble", so "ati" matches first
        # and both of these are reported as AMD.
        ("00:02.0 VGA compatible controller: Intel UHD Graphics 630", "AMD"),
        ("04:00.0 VGA compatible controller: Some Unlisted Vendor", "AMD"),
        # A 3D controller line has no "compatible" in it, so it escapes the trap.
        ("04:00.0 3D controller: Some Unlisted Vendor", "Unknown"),
    ],
)
def test_detect_gpu_maps_each_vendor_keyword(
    monkeypatch: pytest.MonkeyPatch, line: str, vendor: str
) -> None:
    """Vendor keywords map to display names; 3D controllers count as GPUs."""
    monkeypatch.setattr(subprocess, "run", _fake_run({"lspci": line}))
    hw = opt._Hw()

    opt._detect_gpu(hw)

    assert hw.gpu_vendor == vendor


@pytest.mark.xfail(
    reason=(
        "Pre-existing bug carried verbatim through the move: _VENDOR_KW's 'ati' "
        "key is a substring of 'VGA compatible controller', which appears in "
        "every lspci display line, so it matches before 'intel' is ever tried. "
        "Intel iGPUs are misreported as AMD, which wrongly enables the "
        "GPU-accelerated terminal and AMD-only Electron flags. Fixing it is a "
        "behaviour change and does not belong in a move commit."
    ),
    strict=True,
)
def test_detect_gpu_should_recognise_an_intel_igpu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An Intel iGPU ought to be detected as Intel."""
    line = "00:02.0 VGA compatible controller: Intel UHD Graphics 630"
    monkeypatch.setattr(subprocess, "run", _fake_run({"lspci": line}))
    hw = opt._Hw()

    opt._detect_gpu(hw)

    assert hw.gpu_vendor == "Intel"


def test_detect_gpu_leaves_defaults_when_lspci_lists_no_display_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A listing with no VGA/3D line exhausts the loop without a match."""
    monkeypatch.setattr(
        subprocess, "run", _fake_run({"lspci": "00:1f.3 Audio device: Intel\n"})
    )
    hw = opt._Hw()

    opt._detect_gpu(hw)

    assert hw.gpu_vendor == "Unknown"
    assert hw.gpu_model == "Unknown"


def test_detect_gpu_skips_non_display_devices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only VGA/3D lines are considered; the first match wins."""
    listing = "00:1f.3 Audio device: Intel\n" + _NVIDIA_LINE + "\n05:00.0 VGA: AMD\n"
    monkeypatch.setattr(
        subprocess, "run", _fake_run({"lspci": listing, "nvidia-smi": "24576"})
    )
    hw = opt._Hw()

    opt._detect_gpu(hw)

    assert hw.gpu_vendor == "NVIDIA"


# --------------------------------------------------------------------------- #
# _detect_disk
# --------------------------------------------------------------------------- #
def _disk_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, base: str, rotational: str | None
) -> None:
    """Redirect /sys/block lookups into tmp_path, keeping /dev names real."""
    if rotational is not None:
        queue = tmp_path / "sys" / "block" / base / "queue"
        queue.mkdir(parents=True)
        (queue / "rotational").write_text(rotational)
    real_path = opt.Path
    monkeypatch.setattr(
        opt,
        "Path",
        lambda p: (
            tmp_path / str(p).lstrip("/")
            if str(p).startswith("/sys/")
            else real_path(p)
        ),
    )


@pytest.mark.parametrize(
    ("device", "base", "rotational", "expected"),
    [
        ("/dev/nvme0n1p2", "nvme0n1", "0", "nvme"),
        ("/dev/sda1", "sda", "0", "ssd"),
        ("/dev/sdb2", "sdb", "1", "hdd"),
    ],
)
def test_detect_disk_classifies_the_root_device(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    device: str,
    base: str,
    rotational: str,
    expected: str,
) -> None:
    """Partition suffixes are stripped, then rotational/nvme decide the type."""
    monkeypatch.setattr(subprocess, "run", _fake_run({"findmnt": device}))
    _disk_paths(monkeypatch, tmp_path, base, rotational)
    hw = opt._Hw()

    opt._detect_disk(hw)

    assert hw.disk_type == expected


def test_detect_disk_gives_up_when_findmnt_says_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No root device means the type stays unknown."""
    monkeypatch.setattr(subprocess, "run", _fake_run({}))
    hw = opt._Hw()

    opt._detect_disk(hw)

    assert hw.disk_type == "unknown"


def test_detect_disk_gives_up_without_a_rotational_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A device with no sysfs queue entry (e.g. dm-crypt) stays unknown."""
    monkeypatch.setattr(subprocess, "run", _fake_run({"findmnt": "/dev/mapper/root"}))
    _disk_paths(monkeypatch, tmp_path, "mapper/root", None)
    hw = opt._Hw()

    opt._detect_disk(hw)

    assert hw.disk_type == "unknown"


# --------------------------------------------------------------------------- #
# _detect_hardware
# --------------------------------------------------------------------------- #
def test_detect_hardware_runs_every_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """The aggregate calls all four detectors against one _Hw."""
    called: list[str] = []

    def _recorder(name: str) -> Callable[[opt._Hw], None]:
        """Build a probe double that records the name it stands in for."""

        def _probe(_hw: opt._Hw) -> None:
            called.append(name)

        return _probe

    for probe_name in ("_detect_cpu", "_detect_ram", "_detect_gpu", "_detect_disk"):
        monkeypatch.setattr(opt, probe_name, _recorder(probe_name))

    result = opt._detect_hardware()

    assert isinstance(result, opt._Hw)
    assert called == ["_detect_cpu", "_detect_ram", "_detect_gpu", "_detect_disk"]
