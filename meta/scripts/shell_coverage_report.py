#!/usr/bin/env python3
"""Report line coverage for one shell file from a kcov output directory.

Reads kcov's cobertura-style ``cov.xml`` rather than its ``coverage.json``:
the JSON summary carries only a percentage, so it cannot say which lines are
missing, which is the only part that helps close a gap.

Exits 1 when coverage is below the requested minimum, so the caller can use
it as a gate.
"""

from __future__ import annotations

from pathlib import Path
import sys

from defusedxml import ElementTree


def _measure(out_dir: Path, subject: str) -> tuple[int, int, list[str]]:
    """Return (covered, total, uncovered line numbers) for *subject*.

    kcov writes one report per instrumented process. A harness that stages
    the subject into a temp dir produces several, so the entries are merged:
    a line counts as covered if any process hit it.
    """
    hits: dict[str, int] = {}
    for xml_path in out_dir.rglob("cov.xml"):
        for cls in ElementTree.parse(xml_path).iter("class"):
            filename = cls.get("filename", "")
            if Path(filename).name != subject:
                continue
            for line in cls.iter("line"):
                number = line.get("number")
                if number is None:
                    continue
                hits[number] = hits.get(number, 0) + int(line.get("hits", "0"))

    uncovered = sorted((n for n, h in hits.items() if h == 0), key=int)
    return len(hits) - len(uncovered), len(hits), uncovered


def main() -> None:
    """Print the coverage summary and gate on the minimum percentage."""
    out_dir, subject, minimum = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3])

    covered, total, uncovered = _measure(out_dir, subject)
    if total == 0:
        sys.exit(
            f"{subject}: kcov instrumented no lines. It was probably invoked as "
            f"`kcov ... bash <script>`; hand it the script directly instead."
        )

    percent = 100.0 * covered / total
    # sys.stdout.write rather than print, matching extract_shell_functions.py:
    # this is the tool's result, not debug output, and ruff's T201 autofix
    # silently deletes bare print() calls.
    sys.stdout.write(f"{subject}: {covered}/{total} lines = {percent:.2f}%\n")
    if uncovered:
        sys.stdout.write(f"  uncovered: {', '.join(uncovered)}\n")

    if percent < minimum:
        sys.exit(f"coverage {percent:.2f}% is below the required {minimum:.2f}%")


if __name__ == "__main__":
    main()
