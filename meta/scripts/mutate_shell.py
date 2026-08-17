#!/usr/bin/env python3
r"""Mutation-test a shell library against its test script.

A test that passes proves nothing on its own. kcov measures *lines*, not
branches, so ``[ -n "$x" ] && thing`` counts as covered when only one side
ever runs -- and a suite can reach 100% while asserting nothing that would
break if the code were wrong. This applies the check that does discriminate:
break the subject, require the suite to fail, restore.

Mutations are declared in a JSON spec so a run is reproducible from the repo
rather than from a scratch directory::

    {
      "test": "phone_focus_mode/lib/tests/test_monitor.sh",
      "timeout": 180,
      "mutations": [
        {
          "file": "phone_focus_mode/lib/monitor.sh",
          "find": "status=\\"warn\\"",
          "replace": "status=\\"ok\\"",
          "describe": "silence every health warning"
        }
      ]
    }

``find`` is a literal string, not a regex: a sed-style pattern has to be
escaped twice (once for JSON, once for the shell) and the delimiter collides
with ``||``, which silently produced six false survivors when this started
life as a shell script.

Three outcomes, and only one of them is success:

* **killed**  -- the suite failed, so the assertions cover this behaviour.
* **survived** -- the suite passed with the code broken. Either the assertion
  is missing, or the mutation is *equivalent* and the code it changes is dead.
  Both are findings; neither is resolved by deleting the mutation.
* **no-op**   -- ``find`` matched nothing, so the spec is stale. Counted as a
  failure, because a mutation that cannot apply silently stops testing.

Exit status is 0 only when every mutation was killed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import sys


@dataclass(frozen=True)
class Mutation:
    """One edit to apply to one file, with a human-readable description."""

    file: Path
    find: str
    replace: str
    describe: str


@dataclass(frozen=True)
class Spec:
    """A test script plus the mutations it is expected to catch."""

    test: Path
    mutations: tuple[Mutation, ...]
    timeout: int


def _load_spec(path: Path, root: Path) -> Spec:
    """Parse a mutation spec, resolving every path relative to ``root``."""
    data = json.loads(path.read_text(encoding="utf-8"))
    mutations = tuple(
        Mutation(
            file=root / entry["file"],
            find=entry["find"],
            replace=entry["replace"],
            describe=entry["describe"],
        )
        for entry in data["mutations"]
    )
    if not mutations:
        message = f"{path}: spec declares no mutations"
        raise ValueError(message)
    return Spec(
        test=root / data["test"],
        mutations=mutations,
        timeout=int(data.get("timeout", 180)),
    )


def _suite_passes(test: Path, root: Path, timeout: int) -> bool:
    """Run the test script, returning whether it exited 0."""
    try:
        completed = subprocess.run(
            ["/usr/bin/env", "bash", str(test)],
            cwd=root,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        # A hang is not a pass: the mutation broke the suite badly enough that
        # it never finished, which still means the behaviour is covered.
        return False
    return completed.returncode == 0


def _apply(mutation: Mutation) -> bool:
    """Apply one mutation in place. Returns False when it matched nothing."""
    original = mutation.file.read_text(encoding="utf-8")
    mutated = original.replace(mutation.find, mutation.replace)
    if mutated == original:
        return False
    mutation.file.write_text(mutated, encoding="utf-8")
    return True


def _run_one(mutation: Mutation, spec: Spec, root: Path) -> str:
    """Apply, run, restore. Returns 'killed', 'survived' or 'no-op'."""
    backup = mutation.file.with_suffix(mutation.file.suffix + ".mutbak")
    shutil.copy2(mutation.file, backup)
    try:
        if not _apply(mutation):
            return "no-op"
        return "survived" if _suite_passes(spec.test, root, spec.timeout) else "killed"
    finally:
        # Restore unconditionally: a crash mid-run must not leave the working
        # tree holding a deliberately broken subject.
        shutil.move(str(backup), str(mutation.file))


def main() -> int:
    """Run every mutation in the spec and report the tally."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="path to the mutation spec JSON")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="repo root that spec paths are relative to (default: cwd)",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    spec = _load_spec(args.spec, root)

    killed = 0
    failures: list[str] = []

    for mutation in spec.mutations:
        outcome = _run_one(mutation, spec, root)
        if outcome == "killed":
            killed += 1
        else:
            failures.append(f"{outcome.upper()}: {mutation.describe}")
        sys.stdout.write(f"{outcome:>8}: {mutation.describe}\n")

    sys.stdout.write(
        f"\nMutations: {killed} killed, {len(failures)} not killed "
        f"(of {len(spec.mutations)})\n",
    )
    for failure in failures:
        sys.stdout.write(f"  {failure}\n")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
