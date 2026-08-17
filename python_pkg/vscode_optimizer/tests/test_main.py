"""Tests for applying a plan to one variant, and for the CLI entry point.

Every variant used here points at ``tmp_path``. The suite must never be able
to resolve a real ``~/.config/*/User/settings.json``; the last test in this
module asserts that directly.
"""

from __future__ import annotations

import builtins
import json
import sys
from typing import TYPE_CHECKING

import pytest

from python_pkg.vscode_optimizer import _config_io as config_io
from python_pkg.vscode_optimizer import _optimize as opt
from python_pkg.vscode_optimizer._types import _Hw, _Variant

if TYPE_CHECKING:
    from pathlib import Path


def _variant(tmp_path: Path) -> _Variant:
    """A VS Code variant rooted entirely inside tmp_path."""
    return _Variant(
        name="Test Code",
        settings=tmp_path / "User" / "settings.json",
        flags=tmp_path / "code-flags.conf",
        binary="code",
    )


_HW = _Hw(cpu_physical_cores=8, ram_total_mb=32000, gpu_vendor="NVIDIA")


# --------------------------------------------------------------------------- #
# _apply_variant
# --------------------------------------------------------------------------- #
def test_apply_variant_writes_settings_and_flags(tmp_path: Path) -> None:
    """With --yes, both files are written and the plan is applied."""
    v = _variant(tmp_path)

    opt._apply_variant(v, _HW, ["--enable-zero-copy"], dry_run=False, auto_yes=True)

    written = json.loads(v.settings.read_text())
    assert written["search.maxThreads"] == 8
    assert written["files.maxMemoryForLargeFilesMB"] == 4096
    assert v.flags.read_text().strip() == "--enable-zero-copy"


def test_apply_variant_writes_nothing_in_dry_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--dry-run reports the plan and leaves the disk untouched."""
    v = _variant(tmp_path)

    opt._apply_variant(v, _HW, ["--enable-zero-copy"], dry_run=True, auto_yes=True)

    assert not v.settings.exists()
    assert not v.flags.exists()
    assert "dry-run" in capsys.readouterr().out


def test_apply_variant_backs_up_an_existing_settings_file(tmp_path: Path) -> None:
    """An existing file is copied aside before being overwritten."""
    v = _variant(tmp_path)
    v.settings.parent.mkdir(parents=True)
    v.settings.write_text('{"editor.fontSize": 14}')

    opt._apply_variant(v, _HW, [], dry_run=False, auto_yes=True)

    backups = list(v.settings.parent.glob("*.bak"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text()) == {"editor.fontSize": 14}
    assert json.loads(v.settings.read_text())["editor.fontSize"] == 14


def test_apply_variant_backs_up_an_existing_flags_file(tmp_path: Path) -> None:
    """The flags file gets the same backup treatment as settings."""
    v = _variant(tmp_path)
    v.flags.write_text("--existing-flag\n")

    opt._apply_variant(v, _HW, ["--enable-zero-copy"], dry_run=False, auto_yes=True)

    assert list(tmp_path.glob("*.bak"))
    assert "--existing-flag" in v.flags.read_text()
    assert "--enable-zero-copy" in v.flags.read_text()


def test_apply_variant_does_nothing_when_already_optimized(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A variant needing no changes is reported and skipped."""
    v = _variant(tmp_path)
    opt._apply_variant(v, _HW, [], dry_run=False, auto_yes=True)
    before = v.settings.read_text()
    capsys.readouterr()

    opt._apply_variant(v, _HW, [], dry_run=False, auto_yes=True)

    assert v.settings.read_text() == before
    assert "Nothing to do" in capsys.readouterr().out


def test_apply_variant_writes_only_flags_when_settings_are_current(
    tmp_path: Path,
) -> None:
    """A flags-only change leaves settings.json untouched, with no backup."""
    v = _variant(tmp_path)
    opt._apply_variant(v, _HW, [], dry_run=False, auto_yes=True)
    settings_before = v.settings.read_text()

    opt._apply_variant(v, _HW, ["--ignore-gpu-blocklist"], dry_run=False, auto_yes=True)

    assert v.settings.read_text() == settings_before
    assert not list(v.settings.parent.glob("*.bak"))
    assert "--ignore-gpu-blocklist" in v.flags.read_text()


@pytest.mark.parametrize("answer", ["y", "yes", "Y", "YES"])
def test_apply_variant_applies_on_confirmation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: str
) -> None:
    """Any spelling of yes at the prompt applies the change."""
    v = _variant(tmp_path)
    monkeypatch.setattr(builtins, "input", lambda _p: answer)

    opt._apply_variant(v, _HW, [], dry_run=False, auto_yes=False)

    assert v.settings.exists()


@pytest.mark.parametrize("answer", ["n", "", "no", "maybe"])
def test_apply_variant_skips_when_declined(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    answer: str,
) -> None:
    """Anything other than yes leaves the disk untouched."""
    v = _variant(tmp_path)
    monkeypatch.setattr(builtins, "input", lambda _p: answer)

    opt._apply_variant(v, _HW, [], dry_run=False, auto_yes=False)

    assert not v.settings.exists()
    assert "Skipped" in capsys.readouterr().out


def test_apply_variant_adds_flags_without_duplicating_existing_ones(
    tmp_path: Path,
) -> None:
    """Merging flags preserves order and drops duplicates."""
    v = _variant(tmp_path)
    v.flags.write_text("--enable-zero-copy\n--custom\n")

    opt._apply_variant(
        v,
        _HW,
        ["--enable-zero-copy", "--ignore-gpu-blocklist"],
        dry_run=False,
        auto_yes=True,
    )

    assert v.flags.read_text().split() == [
        "--enable-zero-copy",
        "--custom",
        "--ignore-gpu-blocklist",
    ]


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def test_main_optimizes_every_discovered_variant(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The entry point detects hardware, then applies to each variant."""
    v = _variant(tmp_path)
    monkeypatch.setattr(sys, "argv", ["optimize_vscode", "--yes"])
    monkeypatch.setattr(opt, "_detect_hardware", lambda: _HW)
    monkeypatch.setattr(opt, "_discover_variants", lambda: [v])

    opt.main()

    assert json.loads(v.settings.read_text())["search.maxThreads"] == 8


def test_main_honours_dry_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """--dry-run reaches _apply_variant and prevents all writes."""
    v = _variant(tmp_path)
    monkeypatch.setattr(sys, "argv", ["optimize_vscode", "--dry-run"])
    monkeypatch.setattr(opt, "_detect_hardware", lambda: _HW)
    monkeypatch.setattr(opt, "_discover_variants", lambda: [v])

    opt.main()

    assert not v.settings.exists()


def test_main_exits_nonzero_without_an_installation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No VS Code variant is a usage error, not a silent success."""
    monkeypatch.setattr(sys, "argv", ["optimize_vscode", "--dry-run"])
    monkeypatch.setattr(opt, "_detect_hardware", lambda: _HW)
    monkeypatch.setattr(opt, "_discover_variants", list)

    with pytest.raises(SystemExit) as excinfo:
        opt.main()

    assert excinfo.value.code == 1
    assert "No VS Code installation found" in capsys.readouterr().out


def test_the_module_entry_point_exposes_main() -> None:
    """`python3 -m python_pkg.vscode_optimizer` resolves to the same main().

    The script used to be run by path from meta/scripts/; this import is what
    proves the replacement entry point works after the move.
    """
    from python_pkg.vscode_optimizer import __main__ as entry

    assert entry.main is opt.main


def test_the_suite_never_touches_the_real_user_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Guard rail: with Path.home redirected, discovery stays inside tmp_path.

    A regression here would mean some test could rewrite the developer's own
    VS Code configuration, which is exactly what --dry-run exists to prevent.
    """
    monkeypatch.setattr(config_io.Path, "home", classmethod(lambda _cls: tmp_path))

    for variant in config_io._discover_variants():
        assert tmp_path in variant.settings.parents
        assert tmp_path in variant.flags.parents
