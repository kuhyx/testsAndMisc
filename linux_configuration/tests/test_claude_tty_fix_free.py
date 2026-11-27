"""Tests for CLAUDE_USE_FREE routing in linux_configuration/zsh/claude-tty-fix.zsh.

Copyright (c) kuhy.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import time

import pytest

pytestmark = pytest.mark.skipif(shutil.which("zsh") is None, reason="zsh not installed")

SCRIPT = Path(__file__).resolve().parents[1] / "zsh" / "claude-tty-fix.zsh"

_CLAUDE_STUB = '#!/bin/sh\necho "real $*" >> "$STUB_LOG"\n'
_CLAUDE_FREE_STUB = '#!/bin/sh\necho "free $*" >> "$STUB_LOG"\n'
# free-llm-check-dir exits 0 for a public repo; the test picks via CHECK_DIR_RC.
_CHECK_DIR_STUB = '#!/bin/sh\nexit "${CHECK_DIR_RC:-0}"\n'


def _run(tmp_path: Path, env_extra: dict[str, str], call: str) -> str:
    """Source the wrapper in a zsh subshell and return the recorded stub log.

    Two stub binaries (``claude`` and ``claude-free``) are placed on a private
    PATH; whichever the wrapper invokes appends a tagged line to ``$STUB_LOG``.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "stub.log"
    stubs = (
        ("claude", _CLAUDE_STUB),
        ("claude-free", _CLAUDE_FREE_STUB),
        ("free-llm-check-dir", _CHECK_DIR_STUB),
    )
    for name, body in stubs:
        stub = bin_dir / name
        stub.write_text(body)
        stub.chmod(0o755)
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "STUB_LOG": str(log),
        "CLAUDE_DEBUG_LOG_OFF": "1",
        **env_extra,
    }
    zsh = shutil.which("zsh")
    assert zsh is not None
    subprocess.run(
        [zsh, "-fc", f"source {SCRIPT}; {call}"],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return log.read_text() if log.exists() else ""


def test_default_runs_real_claude(tmp_path: Path) -> None:
    """With no opt-in the wrapper runs the real ``claude`` binary."""
    assert _run(tmp_path, {}, "claude -p hi") == "real -p hi\n"


def test_use_free_routes_to_claude_free(tmp_path: Path) -> None:
    """CLAUDE_USE_FREE=1 routes the plain ``claude`` call to ``claude-free``."""
    assert _run(tmp_path, {"CLAUDE_USE_FREE": "1"}, "claude -p hi") == "free -p hi\n"


def test_use_free_keeps_mcp_wrappers_working(tmp_path: Path) -> None:
    """The MCP wrappers still forward their flag when routing to free models."""
    out = _run(tmp_path, {"CLAUDE_USE_FREE": "1"}, "claude-rag x")
    assert out == f"free --mcp-config {tmp_path}/.claude/mcp-optional/rag.json x\n"


def test_use_free_with_tty_fix_off(tmp_path: Path) -> None:
    """CLAUDE_USE_FREE=1 still routes to free models with the TTY fix disabled."""
    assert (
        _run(
            tmp_path,
            {"CLAUDE_USE_FREE": "1", "CLAUDE_TTY_FIX_OFF": "1"},
            "claude -p hi",
        )
        == "free -p hi\n"
    )


def _write_limit_state(tmp_path: Path, five_pct: float, resets_in: int) -> None:
    """Write a statusLine-style limit-state shard under the fake HOME."""
    state_dir = tmp_path / ".claude" / "cache" / "limit-state"
    state_dir.mkdir(parents=True)
    now = int(time.time())
    state = {
        "five_hour_pct": five_pct,
        "five_hour_resets_at": now + resets_in,
        "seven_day_pct": 40,
        "seven_day_resets_at": now + 86400,
        "updated_at": now,
    }
    (state_dir / "-home-kuhy-x.json").write_text(json.dumps(state))


def test_spent_limit_auto_routes_to_free(tmp_path: Path) -> None:
    """A spent 5-hour window routes to ``claude-free`` with no opt-in."""
    _write_limit_state(tmp_path, 100.0, 3600)
    assert _run(tmp_path, {}, "claude -p hi") == "free -p hi\n"


def test_spent_seven_day_auto_routes_to_free(tmp_path: Path) -> None:
    """A spent 7-day window routes to ``claude-free`` too."""
    state_dir = tmp_path / ".claude" / "cache" / "limit-state"
    state_dir.mkdir(parents=True)
    now = int(time.time())
    state = {
        "five_hour_pct": 10,
        "five_hour_resets_at": now + 3600,
        "seven_day_pct": 100,
        "seven_day_resets_at": now + 86400,
    }
    (state_dir / "a.json").write_text(json.dumps(state))
    assert _run(tmp_path, {}, "claude -p hi") == "free -p hi\n"


def test_limit_below_cap_runs_real_claude(tmp_path: Path) -> None:
    """Usage under 100 % keeps the real binary."""
    _write_limit_state(tmp_path, 99.0, 3600)
    assert _run(tmp_path, {}, "claude -p hi") == "real -p hi\n"


def test_limit_already_reset_runs_real_claude(tmp_path: Path) -> None:
    """A spent window whose reset time has passed counts as fresh."""
    _write_limit_state(tmp_path, 100.0, -60)
    assert _run(tmp_path, {}, "claude -p hi") == "real -p hi\n"


def test_spent_limit_private_dir_runs_real_claude(tmp_path: Path) -> None:
    """Outside a public repo free models are refused, so the real binary runs."""
    _write_limit_state(tmp_path, 100.0, 3600)
    assert _run(tmp_path, {"CHECK_DIR_RC": "1"}, "claude -p hi") == "real -p hi\n"


def test_use_free_zero_disables_auto_routing(tmp_path: Path) -> None:
    """CLAUDE_USE_FREE=0 keeps the real binary even with the limit spent."""
    _write_limit_state(tmp_path, 100.0, 3600)
    assert _run(tmp_path, {"CLAUDE_USE_FREE": "0"}, "claude -p hi") == "real -p hi\n"
