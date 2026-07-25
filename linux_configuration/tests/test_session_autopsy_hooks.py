"""Behavioural tests for the two session_autopsy Claude Code hooks.

Both hooks end in an unconditional ``exit 0`` by design — an autopsy failure must
never surface into the session lifecycle — so exit status is a constant and
asserting it proves nothing. Every assertion here is on an observable side
effect instead: what the SessionEnd hook hands to ``setsid``, and what the
SessionStart hook writes to stdout.

The hooks under test are the real deployed artifacts in ``~/.claude/hooks``.
``AUTOPSY_HOOKS_DIR`` overrides that, which is what lets the mutation check run
the same suite against a deliberately broken copy without touching the live
hooks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time

import pytest

_HOOKS_DIR = Path(
    os.environ.get("AUTOPSY_HOOKS_DIR", Path.home() / ".claude" / "hooks")
)
_END_HOOK = _HOOKS_DIR / "session_autopsy_end.sh"
_START_HOOK = _HOOKS_DIR / "session_autopsy_start.sh"

# The hooks live in ~/.claude, which does not exist on a CI runner.
pytestmark = pytest.mark.skipif(
    not (_END_HOOK.is_file() and _START_HOOK.is_file()),
    reason=f"session_autopsy hooks are not deployed under {_HOOKS_DIR}",
)

_LAUNCH_WAIT_SECONDS = 5.0
_POLL_SECONDS = 0.02
_RUN_TIMEOUT_SECONDS = 30

# The hook detaches its ingest with ``setsid ... &``, so the parent can exit
# before the shim has recorded anything. Asserting "no launch" the instant the
# parent exits would therefore pass even against a hook whose guard had been
# deleted — vacuously. This window gives a launch that WAS made time to show up.
_SETTLE_SECONDS = 1.0


def _isolated_env(home: Path, *extra_path: Path) -> dict[str, str]:
    """Build an environment whose ``HOME`` — and so every hook path — is ``home``."""
    env = dict(os.environ)
    env["HOME"] = str(home)
    if extra_path:
        joined = os.pathsep.join(str(entry) for entry in extra_path)
        env["PATH"] = f"{joined}{os.pathsep}{env['PATH']}"
    return env


def _write_setsid_shim(bin_dir: Path, record: Path) -> None:
    """Install a ``setsid`` that records its argv instead of launching an ingest."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    shim = bin_dir / "setsid"
    shim.write_text(
        f'#!/bin/bash\nprintf "%s\\n" "$*" >> {record}\nexit 0\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)


def _run_end_hook(tmp_path: Path, payload: str) -> tuple[Path, Path]:
    """Run the SessionEnd hook on ``payload``; return its fake HOME and argv record.

    The record is written by the ``setsid`` shim, so its existence means the hook
    decided to launch an ingest, and its absence means a guard stopped it.
    """
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    record = tmp_path / "setsid.argv"
    _write_setsid_shim(tmp_path / "bin", record)
    subprocess.run(
        [str(_END_HOOK)],
        input=payload,
        env=_isolated_env(home, tmp_path / "bin"),
        capture_output=True,
        text=True,
        timeout=_RUN_TIMEOUT_SECONDS,
        check=False,
    )
    return home, record


def _await_launch(record: Path) -> str:
    """Return the recorded argv, waiting for the backgrounded ``setsid &`` to land."""
    deadline = time.monotonic() + _LAUNCH_WAIT_SECONDS
    while time.monotonic() < deadline:
        if record.is_file():
            return record.read_text(encoding="utf-8")
        time.sleep(_POLL_SECONDS)
    msg = f"no ingest was launched within {_LAUNCH_WAIT_SECONDS}s"
    raise AssertionError(msg)


def _assert_no_launch(record: Path) -> None:
    """Assert no ingest was launched, allowing for the hook's detached ``&``."""
    time.sleep(_SETTLE_SECONDS)
    assert not record.exists()


def _run_start_hook(
    tmp_path: Path, state: str | None, *, mode: int | None = None
) -> tuple[str, str]:
    """Run the SessionStart hook against ``state``; return ``(stdout, stderr)``.

    stderr matters as much as stdout here: this hook runs at every session start,
    and bash noise (an arithmetic error on a non-numeric count, say) would be
    injected into the session just as surely as an intentional banner.
    """
    home = tmp_path / "home"
    autopsy = home / ".claude" / "autopsy"
    autopsy.mkdir(parents=True, exist_ok=True)
    if state is not None:
        state_file = autopsy / "state.json"
        state_file.write_text(state, encoding="utf-8")
        if mode is not None:
            state_file.chmod(mode)
    result = subprocess.run(
        [str(_START_HOOK)],
        env=_isolated_env(home),
        capture_output=True,
        text=True,
        timeout=_RUN_TIMEOUT_SECONDS,
        check=False,
    )
    return result.stdout, result.stderr


class TestSessionEndHookLaunchesIngest:
    """A usable transcript is handed to the analyzer, detached."""

    def test_launches_ingest_for_the_transcript(self, tmp_path: Path) -> None:
        transcript = tmp_path / "session.jsonl"
        transcript.write_text('{"type":"user"}\n', encoding="utf-8")
        home, record = _run_end_hook(
            tmp_path,
            json.dumps({"transcript_path": str(transcript)}),
        )
        argv = _await_launch(record)
        assert "python_pkg.session_autopsy" in argv
        assert "ingest" in argv
        assert str(transcript) in argv
        assert "--quiet" in argv
        assert f"PYTHONPATH={home}/testsAndMisc" in argv
        assert "timeout 120" in argv

    def test_creates_the_autopsy_home(self, tmp_path: Path) -> None:
        transcript = tmp_path / "session.jsonl"
        transcript.write_text("{}\n", encoding="utf-8")
        home, record = _run_end_hook(
            tmp_path,
            json.dumps({"transcript_path": str(transcript)}),
        )
        _await_launch(record)
        assert (home / ".claude" / "autopsy").is_dir()


class TestSessionEndHookDeclinesToLaunch:
    """Nothing is launched without a transcript that exists."""

    def test_missing_key(self, tmp_path: Path) -> None:
        _, record = _run_end_hook(tmp_path, "{}")
        _assert_no_launch(record)

    def test_empty_path(self, tmp_path: Path) -> None:
        _, record = _run_end_hook(tmp_path, json.dumps({"transcript_path": ""}))
        _assert_no_launch(record)

    def test_nonexistent_path(self, tmp_path: Path) -> None:
        payload = json.dumps({"transcript_path": str(tmp_path / "gone.jsonl")})
        _, record = _run_end_hook(tmp_path, payload)
        _assert_no_launch(record)

    def test_malformed_payload(self, tmp_path: Path) -> None:
        _, record = _run_end_hook(tmp_path, "not json at all")
        _assert_no_launch(record)


class TestSessionStartHookAnnounces:
    """The nudge is printed only when there is something to review."""

    def test_announces_unreviewed_candidates(self, tmp_path: Path) -> None:
        stdout, stderr = _run_start_hook(tmp_path, json.dumps({"unreviewed_count": 7}))
        assert stderr == ""
        assert stdout.count("\n") == 1
        assert "7 unreviewed automation candidates" in stdout
        assert "REPORT.md" in stdout
        assert "/compile-candidate" in stdout


class TestSessionStartHookStaysSilent:
    """Every path that is not a positive count costs zero context tokens.

    Silence means BOTH streams: a bash error on stderr reaches the session too.
    """

    def test_no_state_file(self, tmp_path: Path) -> None:
        assert _run_start_hook(tmp_path, None) == ("", "")

    def test_zero_count(self, tmp_path: Path) -> None:
        assert _run_start_hook(tmp_path, json.dumps({"unreviewed_count": 0})) == (
            "",
            "",
        )

    def test_non_numeric_count(self, tmp_path: Path) -> None:
        state = json.dumps({"unreviewed_count": "abc"})
        assert _run_start_hook(tmp_path, state) == ("", "")

    def test_malformed_state(self, tmp_path: Path) -> None:
        assert _run_start_hook(tmp_path, "{not json") == ("", "")

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses the readability check")
    def test_unreadable_state(self, tmp_path: Path) -> None:
        state = json.dumps({"unreviewed_count": 9})
        assert _run_start_hook(tmp_path, state, mode=0o000) == ("", "")
