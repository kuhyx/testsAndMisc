#!/usr/bin/env python3
"""Auto-optimize VS Code settings based on detected hardware."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

_RAM_THRESHOLDS = ((28000, 4096), (14000, 2048), (7000, 1024))
_DEFAULT_MEM = 512
_MIB_1024 = 1024
_MIN_THREADS = 4
_SUBMOD_LIMIT = 30
_LSCPU = {
    "Model name": "cpu_model",
    "CPU(s)": "cpu_logical_cores",
    "Core(s) per socket": "cpu_physical_cores",
    "CPU max MHz": "cpu_max_mhz",
}
_VENDOR_KW = {"nvidia": "NVIDIA", "amd": "AMD", "ati": "AMD", "intel": "Intel"}
_WATCHER_EX: dict[str, bool] = dict.fromkeys(
    [
        "**/.git/objects/**",
        "**/.git/subtree-cache/**",
        "**/node_modules/**",
        "**/.venv/**",
        "**/venv/**",
        "**/__pycache__/**",
        "**/build/**",
        "**/.mypy_cache/**",
        "**/.ruff_cache/**",
        "**/.pytest_cache/**",
        "**/dist/**",
        "**/*.egg-info/**",
    ],
    True,
)
_SEARCH_EX: dict[str, bool] = dict.fromkeys(
    [
        "**/node_modules",
        "**/build",
        "**/.venv",
        "**/venv",
        "**/__pycache__",
        "**/.mypy_cache",
        "**/.ruff_cache",
        "**/.pytest_cache",
        "**/dist",
    ],
    True,
)
_B = "\033[94m"
_G = "\033[92m"
_Y = "\033[93m"
_C = "\033[96m"
_BO = "\033[1m"
_R = "\033[0m"


@dataclass
class _Hw:
    """Detected system hardware."""

    cpu_model: str = "Unknown"
    cpu_physical_cores: int = 1
    cpu_logical_cores: int = 1
    cpu_max_mhz: float = 0.0
    ram_total_mb: int = 0
    gpu_vendor: str = "Unknown"
    gpu_model: str = "Unknown"
    gpu_vram_mb: int = 0
    disk_type: str = "unknown"


@dataclass
class _Opt:
    """Single proposed change."""

    key: str
    value: object
    reason: str
    current: object = None


@dataclass
class _Variant:
    """A VS Code installation."""

    name: str
    settings: Path
    flags: Path
    binary: str


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
        meminfo = Path("/proc/meminfo").read_text()
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
    if rotational.read_text().strip() == "1":
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


def _discover_variants() -> list[_Variant]:
    """Find all installed VS Code variants."""
    cfg = Path.home() / ".config"
    cands = [
        ("VS Code (stable)", "Code", "code-flags.conf", "code"),
        (
            "VS Code Insiders",
            "Code - Insiders",
            "code-insiders-flags.conf",
            "code-insiders",
        ),
        ("VSCodium", "VSCodium", "vscodium-flags.conf", "codium"),
    ]
    found: list[_Variant] = []
    for name, dir_name, flags_name, binary in cands:
        sp = cfg / dir_name / "User" / "settings.json"
        fp = cfg / flags_name
        if sp.exists() or shutil.which(binary):
            found.append(_Variant(name, sp, fp, binary))
    return found


def _parse_jsonc(text: str) -> dict[str, object]:
    """Parse JSON with Comments (JSONC) used by VS Code."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            out.append(text[i:j])
            i = j
        elif ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif ch == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            i = end + 2 if end != -1 else n
        else:
            out.append(ch)
            i += 1
    cleaned = re.sub(r",(\s*[}\]])", r"\1", "".join(out))
    if not cleaned.strip():
        return {}
    parsed: dict[str, object] = json.loads(cleaned)
    return parsed


def _ideal_mem(ram_mb: int) -> int:
    for threshold, value in _RAM_THRESHOLDS:
        if ram_mb >= threshold:
            return value
    return _DEFAULT_MEM


def _dict_merge_opt(
    cur_settings: dict[str, object],
    key: str,
    ideal: dict[str, bool],
    reason: str,
) -> _Opt | None:
    cur = cur_settings.get(key, {})
    if not isinstance(cur, dict):
        cur = {}
    if all(k in cur for k in ideal):
        return None
    return _Opt(key, {**cur, **ideal}, reason, cur or None)


def _compute_opts(hw: _Hw, cur: dict[str, object]) -> list[_Opt]:
    """Return optimizations based on hardware and current settings."""
    opts: list[_Opt] = []

    def _p(key: str, val: object, reason: str) -> None:
        if cur.get(key) != val:
            opts.append(_Opt(key, val, reason, cur.get(key)))

    threads = max(_MIN_THREADS, hw.cpu_physical_cores)
    _p(
        "search.maxThreads",
        threads,
        f"{hw.cpu_physical_cores} physical cores - use them for workspace search",
    )
    mem = _ideal_mem(hw.ram_total_mb)
    _p(
        "files.maxMemoryForLargeFilesMB",
        mem,
        f"{hw.ram_total_mb // _MIB_1024} GB RAM - allow up to {mem} MB for large files",
    )
    if hw.gpu_vendor in ("NVIDIA", "AMD"):
        _p(
            "terminal.integrated.gpuAcceleration",
            "on",
            f"{hw.gpu_vendor} GPU - enable GPU-rendered terminal",
        )
        smooth = True
        for key in (
            "editor.smoothScrolling",
            "workbench.list.smoothScrolling",
            "terminal.integrated.smoothScrolling",
        ):
            _p(key, smooth, "Smooth scrolling is free with a dedicated GPU")
    no = False
    _p("search.followSymlinks", no, "Avoid duplicate results and wasted I/O")
    for result in (
        _dict_merge_opt(
            cur,
            "files.watcherExclude",
            _WATCHER_EX,
            "Exclude build/cache dirs from file watcher",
        ),
        _dict_merge_opt(
            cur, "search.exclude", _SEARCH_EX, "Exclude build/cache dirs from search"
        ),
    ):
        if result:
            opts.extend([result])
    _p("editor.guides.bracketPairs", "active", "Lightweight visual aid")
    _p(
        "diffEditor.maxComputationTime",
        0,
        f"Fast CPU ({hw.cpu_model}) - compute diffs fully",
    )
    _p("editor.minimap.enabled", no, "Minimap consumes GPU/CPU for little benefit")
    cur_sub = cur.get("git.detectSubmodulesLimit")
    if cur_sub is None or (isinstance(cur_sub, int) and cur_sub < _SUBMOD_LIMIT):
        opts.append(
            _Opt(
                "git.detectSubmodulesLimit",
                _SUBMOD_LIMIT,
                "Higher limit is fine with fast CPU",
                cur_sub,
            )
        )
    return opts


def _gpu_flags(hw: _Hw) -> list[str]:
    """Return Electron flags appropriate for the detected GPU."""
    if hw.gpu_vendor in ("NVIDIA", "AMD"):
        base = [
            "--enable-gpu-rasterization",
            "--enable-zero-copy",
            "--ignore-gpu-blocklist",
            "--enable-features=CanvasOopRasterization",
        ]
        if hw.gpu_vendor == "NVIDIA":
            base.append("--enable-features=VaapiVideoDecodeLinuxGL,VaapiVideoEncoder")
        return base
    if hw.gpu_vendor == "Intel":
        return [
            "--enable-gpu-rasterization",
            "--ignore-gpu-blocklist",
            "--enable-features=VaapiVideoDecodeLinuxGL",
        ]
    return []


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst = path.with_suffix(f".{ts}.bak")
    shutil.copy2(path, dst)
    return dst


def _read_settings(path: Path) -> dict[str, object]:
    return _parse_jsonc(path.read_text()) if path.exists() else {}


def _write_settings(path: Path, current: dict[str, object], opts: list[_Opt]) -> None:
    merged = {**current, **{o.key: o.value for o in opts}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=4, ensure_ascii=False) + "\n")


def _read_flags(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        ln.strip()
        for ln in path.read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]


def _write_flags(path: Path, flags: list[str]) -> None:
    path.write_text("\n".join(flags) + "\n")


def _out(text: str = "") -> None:
    """Write a line to stdout."""
    sys.stdout.write(text + "\n")


def _hdr(text: str) -> None:
    _out(f"\n{_BO}{_B}{'─' * 60}{_R}\n{_BO}{_B}  {text}{_R}\n{_BO}{_B}{'─' * 60}{_R}")


def _show_hw(hw: _Hw) -> None:
    _hdr("Detected Hardware")
    _out(f"  {_C}CPU{_R}   {hw.cpu_model}")
    _out(
        f"        {hw.cpu_physical_cores} cores / {hw.cpu_logical_cores} threads"
        f" @ {hw.cpu_max_mhz:.0f} MHz"
    )
    _out(f"  {_C}RAM{_R}   {hw.ram_total_mb // _MIB_1024} GB")
    gpu = f"  {_C}GPU{_R}   {hw.gpu_vendor} - {hw.gpu_model}"
    if hw.gpu_vram_mb:
        gpu += f" ({hw.gpu_vram_mb} MB VRAM)"
    _out(gpu)
    _out(f"  {_C}Disk{_R}  {hw.disk_type.upper()}")


def _show_plan(opts: list[_Opt], new_fl: list[str], old_fl: list[str]) -> None:
    _hdr("Optimization Plan")
    added = [f for f in new_fl if f not in old_fl]
    if added:
        _out(f"\n  {_BO}Electron flags to add:{_R}")
        for fl in added:
            _out(f"    {_G}+ {fl}{_R}")
    elif new_fl:
        _out(f"\n  {_Y}Electron GPU flags already present{_R}")
    if opts:
        _out(f"\n  {_BO}Settings to change:{_R}")
        for i, o in enumerate(opts, 1):
            c = json.dumps(o.current)[:55] if o.current is not None else "-"
            v = json.dumps(o.value)[:55]
            _out(f"\n  {_BO}{i}. {o.key}{_R}\n     {o.reason}")
            _out(f"     {_Y}{c}{_R} -> {_G}{v}{_R}")
    else:
        _out(f"\n  {_G}All settings already optimized{_R}")
    total = len(opts) + len(added)
    if total:
        _out(f"\n  {_BO}{total} change(s) proposed.{_R}")


def _apply_variant(
    v: _Variant,
    hw: _Hw,
    ideal_flags: list[str],
    *,
    dry_run: bool,
    auto_yes: bool,
) -> None:
    """Compute and apply optimizations for a single variant."""
    _hdr(f"Optimizing: {v.name}")
    current = _read_settings(v.settings)
    opts = _compute_opts(hw, current)
    old_flags = _read_flags(v.flags)
    merged = list(dict.fromkeys(old_flags + ideal_flags))
    _show_plan(opts, ideal_flags, old_flags)
    flag_changed = merged != old_flags
    if not opts and not flag_changed:
        _out(f"\n  {_G}Nothing to do for {v.name}.{_R}")
        return
    if dry_run:
        _out(f"\n  {_Y}(dry-run) No files modified.{_R}")
        return
    if not auto_yes:
        ans = input(f"\n  Apply changes to {v.name}? [y/N] ").strip()
        if ans.lower() not in ("y", "yes"):
            _out("  Skipped.")
            return
    if opts:
        bak = _backup(v.settings)
        if bak:
            _out(f"  Backup: {bak}")
        _write_settings(v.settings, current, opts)
        _out(f"  {_G}\u2713 settings.json updated{_R}")
    if flag_changed:
        bak = _backup(v.flags)
        if bak:
            _out(f"  Backup: {bak}")
        _write_flags(v.flags, merged)
        _out(f"  {_G}\u2713 {v.flags.name} updated{_R}")


def main() -> None:
    """Entry point: detect hardware, compute optimizations, and apply."""
    ap = argparse.ArgumentParser(
        description="Auto-optimize VS Code for current hardware."
    )
    ap.add_argument("--dry-run", action="store_true", help="Preview without writing.")
    ap.add_argument("--yes", "-y", action="store_true", help="Skip confirmation.")
    args = ap.parse_args()
    hw = _detect_hardware()
    _show_hw(hw)
    variants = _discover_variants()
    if not variants:
        _out(f"\n{_Y}No VS Code installation found.{_R}")
        sys.exit(1)
    _hdr("VS Code Installations")
    for v in variants:
        _out(f"  {_G}\u2022{_R} {v.name}  ({v.settings})")
    ideal = _gpu_flags(hw)
    for v in variants:
        _apply_variant(v, hw, ideal, dry_run=args.dry_run, auto_yes=args.yes)
    _hdr("Done")
    _out(f"  {_BO}Restart VS Code{_R} to apply the changes.\n")


if __name__ == "__main__":
    main()
