"""Fail unless lcov reports 100% line coverage for every ``billsplit/lib`` file.

Two separate checks, because they catch different mistakes: a file present in
the report but with unhit lines, and a file missing from the report entirely.
The second is the one that catches a newly added Dart file nothing imports —
partial coverage is visible in the report, absence is not.

The default project root is resolved from this file's location rather than the
working directory, so the CI job can invoke the module from anywhere in the
repository.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Final

# python_pkg/billsplit_coverage/checker.py -> repo root -> billsplit/
_DEFAULT_PROJECT: Final[pathlib.Path] = (
    pathlib.Path(__file__).resolve().parents[2] / "billsplit"
)

EXIT_INCOMPLETE: Final[int] = 1
EXIT_NO_REPORT: Final[int] = 2


def parse_lcov(lcov: pathlib.Path) -> dict[str, list[int]]:
    """Map each file in an lcov report to its uncovered line numbers.

    Parameters:
    lcov (pathlib.Path): Path to an ``lcov.info`` report.

    Returns:
    dict[str, list[int]]: Source path to the lines with a zero hit count. A
        fully covered file maps to an empty list, which is what lets the caller
        tell "covered completely" apart from "absent from the report".
    """
    uncovered: dict[str, list[int]] = {}
    current: str | None = None
    for line in lcov.read_text(encoding="utf-8").splitlines():
        if line.startswith("SF:"):
            # lcov quotes the path verbatim; normalise Windows separators.
            current = line[3:].replace("\\", "/")
            uncovered.setdefault(current, [])
        elif line.startswith("DA:") and current is not None:
            number, hits = line[3:].split(",")
            if int(hits) == 0:
                uncovered[current].append(int(number))
    return uncovered


def find_failures(
    uncovered: dict[str, list[int]],
    project: pathlib.Path,
) -> list[str]:
    """Describe every coverage gap, as lines ready to print.

    Parameters:
    uncovered (dict[str, list[int]]): Output of :func:`parse_lcov`.
    project (pathlib.Path): Flutter project root holding ``lib/``.

    Returns:
    list[str]: One message per gap; empty when coverage is complete.
    """
    failures = [
        f"{path}: uncovered lines {misses}"
        for path, misses in sorted(uncovered.items())
        if misses
    ]
    lib_files = {
        str(path.relative_to(project)).replace("\\", "/")
        for path in (project / "lib").rglob("*.dart")
    }
    failures.extend(
        f"{path}: not executed by any test (0% coverage)"
        for path in sorted(lib_files - set(uncovered))
    )
    return failures


def check(project: pathlib.Path) -> int:
    """Run the gate for one Flutter project and report to stdout/stderr.

    Parameters:
    project (pathlib.Path): Flutter project root, i.e. the directory holding
        ``lib/`` and ``coverage/lcov.info``.

    Returns:
    int: 0 when coverage is complete, :data:`EXIT_INCOMPLETE` when it is not,
        :data:`EXIT_NO_REPORT` when the lcov report is missing.
    """
    lcov = project / "coverage" / "lcov.info"
    if not lcov.exists():
        sys.stderr.write(f"{lcov} missing — run: flutter test --coverage\n")
        return EXIT_NO_REPORT

    uncovered = parse_lcov(lcov)
    failures = find_failures(uncovered, project)
    if failures:
        sys.stderr.write("COVERAGE < 100%:\n")
        for failure in failures:
            sys.stderr.write(f"  {failure}\n")
        return EXIT_INCOMPLETE

    sys.stdout.write(f"100% line coverage across {len(uncovered)} lib files.\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the gate.

    Parameters:
    argv (list[str] | None): Argument list, or None to read ``sys.argv``.

    Returns:
    int: Process exit status.
    """
    parser = argparse.ArgumentParser(
        description="Fail unless billsplit has 100% line coverage.",
    )
    parser.add_argument(
        "--project",
        type=pathlib.Path,
        default=_DEFAULT_PROJECT,
        help="Flutter project root (defaults to the billsplit/ app in this repo)",
    )
    args = parser.parse_args(argv)
    return check(args.project)
