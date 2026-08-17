"""Render the hardware summary and the optimization plan to the terminal.

The only module that owns the ANSI colour codes, so changing the palette
touches one file.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python_pkg.vscode_optimizer._types import _Hw, _Opt

_MIB_1024 = 1024
_B = "\033[94m"
_G = "\033[92m"
_Y = "\033[93m"
_C = "\033[96m"
_BO = "\033[1m"
_R = "\033[0m"


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
