#!/usr/bin/env python3
"""Prove the session_autopsy hook tests are non-vacuous, by mutation.

Both hooks in ``~/.claude/hooks`` end in an unconditional ``exit 0`` by design,
so a test that asserts exit status passes against a hook whose body has been
deleted. ``linux_configuration/tests/test_session_autopsy_hooks.py`` therefore
asserts side effects instead -- but "asserts a side effect" is a claim, and this
script is what checks it.

Each mutation below breaks ONE guard in a copy of the hooks, points the suite at
that copy through ``AUTOPSY_HOOKS_DIR`` and records which tests died. A test that
no mutation kills is asserting nothing worth asserting. The deployed hooks are
never modified.

Mutating per guard matters: gutting a whole hook body kills only the positive
tests, because a gutted hook emits neither a launch nor any output -- exactly
what the negative tests already expect. Run that way, nine of the twelve tests
look vacuous when they are not.

Used as a pre-commit hook entry point and runnable by hand. Exits 0 when the
hooks are not deployed (a CI runner has no ``~/.claude``), since there is then
nothing to mutate.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable

_TEST_FILE = "linux_configuration/tests/test_session_autopsy_hooks.py"
_END_HOOK = "session_autopsy_end.sh"
_START_HOOK = "session_autopsy_start.sh"
_GUTTED = "#!/bin/bash\nexit 0\n"
_OUTCOME = re.compile(r"::(test_\w+)\s+(PASSED|FAILED|ERROR|SKIPPED)")


def _emit(message: str) -> None:
    """Write ``message`` and a newline to stdout (``print`` is banned by ruff)."""
    sys.stdout.write(f"{message}\n")


def _hooks_dir() -> Path:
    """Return the hook directory under test, honouring ``AUTOPSY_HOOKS_DIR``."""
    override = os.environ.get("AUTOPSY_HOOKS_DIR")
    if override:
        return Path(override)
    return Path.home() / ".claude" / "hooks"


def _gut(_text: str) -> str:
    """Replace an entire hook body with a bare successful exit."""
    return _GUTTED


def _drop_transcript_guard(text: str) -> str:
    """Remove the SessionEnd guard that requires an existing transcript."""
    return re.sub(
        r'if \[\[ -z "\$transcript".*?\nfi\n',
        "",
        text,
        flags=re.DOTALL,
    )


def _widen_count(text: str) -> str:
    """Make a zero candidate count announce itself."""
    return text.replace("(( count > 0 ))", "(( count >= 0 ))")


def _drop_numeric_guard(text: str) -> str:
    """Drop the count regex guard, leaving the arithmetic syntactically valid."""
    return text.replace(
        '[[ "$count" =~ ^[0-9]+$ ]] && (( count > 0 ))',
        "(( count > 0 ))",
    )


def _drop_readable_guard(text: str) -> str:
    """Remove the early exit taken when the state file cannot be read."""
    return re.sub(
        r'if \[\[ ! -r "\$STATE" \]\]; then\n.*?\nfi\n',
        "",
        text,
        flags=re.DOTALL,
    )


def _always_announce(text: str) -> str:
    """Announce unconditionally -- the defect every silence test exists to catch."""
    return re.sub(r'if \[\[ "\$count".*?; then', "if true; then", text)


def _unguarded_and_always_announce(text: str) -> str:
    """Drop the readability guard AND announce unconditionally.

    Needed because the readability guard is redundant on its own: jq's stderr is
    suppressed and an empty count already fails the arithmetic, so removing it
    changes nothing observable. Only removing it together with the count
    condition can reach the no-state and unreadable-state cases.
    """
    return _always_announce(_drop_readable_guard(text))


class Mutation(NamedTuple):
    """One named defect injected into one hook."""

    name: str
    hook: str
    apply: Callable[[str], str]


_MUTATIONS = (
    Mutation("gut-end", _END_HOOK, _gut),
    Mutation("gut-start", _START_HOOK, _gut),
    Mutation("end-no-transcript-guard", _END_HOOK, _drop_transcript_guard),
    Mutation("start-count-ge-zero", _START_HOOK, _widen_count),
    Mutation("start-no-numeric-guard", _START_HOOK, _drop_numeric_guard),
    Mutation("start-no-readable-guard", _START_HOOK, _drop_readable_guard),
    Mutation("start-always-announce", _START_HOOK, _always_announce),
    Mutation("start-unguarded-announce", _START_HOOK, _unguarded_and_always_announce),
)


def _repo_root() -> Path:
    """Return the repository root (this file lives in ``meta/scripts``)."""
    return Path(__file__).resolve().parents[2]


def _run_suite(hooks_dir: Path, scratch: Path) -> set[str]:
    """Run the hook test suite against ``hooks_dir``; return failing test names.

    Args:
        hooks_dir: Directory holding the (possibly mutated) hooks under test.
        scratch: Directory for the throwaway coverage data file.

    Returns:
        The names of tests that failed or errored.

    Raises:
        RuntimeError: If pytest produced no parseable outcomes at all.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            _TEST_FILE,
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
            "-v",
            "--no-header",
            "--tb=no",
        ],
        cwd=_repo_root(),
        env={
            **os.environ,
            "AUTOPSY_HOOKS_DIR": str(hooks_dir),
            "COVERAGE_FILE": str(scratch / ".coverage"),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    outcomes = _OUTCOME.findall(result.stdout)
    if not outcomes:
        msg = f"pytest produced no test outcomes:\n{result.stdout[-2000:]}"
        raise RuntimeError(msg)
    return {name for name, outcome in outcomes if outcome in {"FAILED", "ERROR"}}


def _collect_test_names() -> set[str]:
    """Return every ``test_*`` function name defined in the suite."""
    tree = ast.parse((_repo_root() / _TEST_FILE).read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }


def _apply(mutation: Mutation, hooks_dir: Path, target_dir: Path) -> None:
    """Copy both hooks into ``target_dir`` and inject ``mutation``.

    Raises:
        RuntimeError: If the mutation left the hook text unchanged, which means
            the hook was edited and the mutation no longer describes it.
    """
    for hook in (_END_HOOK, _START_HOOK):
        shutil.copy2(hooks_dir / hook, target_dir / hook)
    target = target_dir / mutation.hook
    original = target.read_text(encoding="utf-8")
    mutated = mutation.apply(original)
    if mutated == original:
        msg = (
            f"mutation {mutation.name!r} no longer applies to {mutation.hook} -- "
            "the hook text changed, so this mutation tests nothing. Update it."
        )
        raise RuntimeError(msg)
    target.write_text(mutated, encoding="utf-8")
    target.chmod(0o755)


def main() -> int:
    """Run every mutation and fail if any test survives them all."""
    hooks_dir = _hooks_dir()
    if not all((hooks_dir / hook).is_file() for hook in (_END_HOOK, _START_HOOK)):
        _emit(f"session_autopsy hooks are not deployed under {hooks_dir} -- skipping")
        return 0

    with tempfile.TemporaryDirectory() as scratch_name:
        scratch = Path(scratch_name)
        baseline = _run_suite(hooks_dir, scratch)
        if baseline:
            _emit(f"BASELINE IS RED, cannot mutate: {sorted(baseline)}")
            return 1

        killed_by: dict[str, list[str]] = {}
        for mutation in _MUTATIONS:
            try:
                with tempfile.TemporaryDirectory() as mutant_name:
                    mutant_dir = Path(mutant_name)
                    _apply(mutation, hooks_dir, mutant_dir)
                    failures = _run_suite(mutant_dir, scratch)
            except RuntimeError as error:
                _emit(f"{mutation.name:26s} ERROR: {error}")
                return 1
            _emit(f"{mutation.name:26s} killed {len(failures):2d}: {sorted(failures)}")
            for test in failures:
                killed_by.setdefault(test, []).append(mutation.name)

    names = _collect_test_names()
    survivors = sorted(names - killed_by.keys())
    if survivors:
        _emit(f"\nVACUOUS -- no mutation kills these: {survivors}")
        return 1
    _emit(f"\nPASS: all {len(names)} tests killed by at least one mutation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
