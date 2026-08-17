"""Auto-optimize VS Code settings based on detected hardware.

Run as ``python3 -m python_pkg.vscode_optimizer [--dry-run] [--yes]``.
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from python_pkg.vscode_optimizer._config_io import (
    _backup,
    _discover_variants,
    _read_flags,
    _read_settings,
    _write_flags,
    _write_settings,
)
from python_pkg.vscode_optimizer._hardware import _detect_hardware
from python_pkg.vscode_optimizer._plan import _compute_opts, _gpu_flags
from python_pkg.vscode_optimizer._render import (
    _BO,
    _G,
    _R,
    _Y,
    _hdr,
    _out,
    _show_hw,
    _show_plan,
)

if TYPE_CHECKING:
    from python_pkg.vscode_optimizer._types import _Hw, _Variant


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
