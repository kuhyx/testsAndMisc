"""Probe the machine's CPU, RAM, GPU, and root disk.

Every probe shells out and degrades to a default rather than raising, so a
missing tool narrows the report instead of failing the run.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

from python_pkg.vscode_optimizer._types import _Hw

_MIB_1024 = 1024
_LSCPU = {
    "Model name": "cpu_model",
    "CPU(s)": "cpu_logical_cores",
    "Core(s) per socket": "cpu_physical_cores",
    "CPU max MHz": "cpu_max_mhz",
}
_VENDOR_KW = {"nvidia": "NVIDIA", "amd": "AMD", "ati": "AMD", "intel": "Intel"}


def _run(args: list[str]) -> str:
    """Run *args* and return stdout, or ``""`` on failure."""
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""
    return proc.stdout.strip()


def _detect_cpu(hw: _Hw) -> None:
    for line in _run(["lscpu"]).splitlines():
        key, _, val = line.partition(":")
        attr = _LSCPU.get(key.strip())
        if attr == "cpu_model":
            hw.cpu_model = val.strip()
        elif attr == "cpu_max_mhz":
            hw.cpu_max_mhz = float(val)
        elif attr is not None:
            setattr(hw, attr, int(val))


def _detect_ram(hw: _Hw) -> None:
    try:
        meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
    except OSError:
        return
    m = re.search(r"MemTotal:\s+(\d+)\s+kB", meminfo)
    if m:
        hw.ram_total_mb = int(m.group(1)) // _MIB_1024


def _detect_gpu(hw: _Hw) -> None:
    for line in _run(["lspci"]).splitlines():
        low = line.lower()
        if "vga" not in low and "3d" not in low:
            continue
        hw.gpu_model = line.rsplit(":", maxsplit=1)[-1].strip()
        for kw, vendor in _VENDOR_KW.items():
            if kw in low:
                hw.gpu_vendor = vendor
                break
        if hw.gpu_vendor == "NVIDIA":
            vram = _run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                ]
            )
            if vram:
                hw.gpu_vram_mb = int(vram.split("\n")[0].strip())
        break


def _detect_disk(hw: _Hw) -> None:
    root_dev = _run(["findmnt", "-n", "-o", "SOURCE", "/"])
    if not root_dev:
        return
    base = re.sub(r"p?\d+$", "", Path(root_dev).name)
    rotational = Path(f"/sys/block/{base}/queue/rotational")
    if not rotational.exists():
        return
    if rotational.read_text(encoding="utf-8").strip() == "1":
        hw.disk_type = "hdd"
    elif "nvme" in base:
        hw.disk_type = "nvme"
    else:
        hw.disk_type = "ssd"


def _detect_hardware() -> _Hw:
    """Probe CPU, RAM, GPU, and root disk type."""
    hw = _Hw()
    for fn in (_detect_cpu, _detect_ram, _detect_gpu, _detect_disk):
        fn(hw)
    return hw
