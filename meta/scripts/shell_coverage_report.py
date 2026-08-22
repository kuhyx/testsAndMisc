#!/usr/bin/env python3
"""Report line coverage for one shell file from a kcov output directory.

Reads kcov's cobertura-style ``cov.xml`` rather than its ``coverage.json``:
the JSON summary carries only a percentage, so it cannot say which lines are
missing, which is the only part that helps close a gap.

kcov alone is not trustworthy (``docs/kcov-under-report.md``): it counts
continuation lines of multi-line quoted arguments as statements that never run
(wrong denominator), and it fails to record ordinary statements that provably
execute (wrong numerator). Both are corrected here -- the denominator by
excluding non-statements, the numerator by unioning in a PS4 xtrace captured
in a second pass.

Exits 1 when coverage is below the requested minimum, so the caller can use
it as a gate.
"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from defusedxml import ElementTree

# Loaded by path rather than imported: meta/scripts/lib is not a package on
# sys.path, and a sys.path.insert would need the import to sit below it,
# which is an E402 the repo will not suppress.
_LINES_PATH = Path(__file__).resolve().parent / "lib" / "shell_coverage_lines.py"
_SPEC = spec_from_file_location("shell_coverage_lines", _LINES_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - unreachable
    raise ImportError(_LINES_PATH)
_LINES = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_LINES)
continuation_lines = _LINES.continuation_lines
traced_lines = _LINES.traced_lines


def _kcov_lines(out_dir: Path, subject: str) -> dict[int, int]:
    """Return kcov's {line: hits} for *subject*.

    kcov writes one report per instrumented process. A harness that stages
    the subject into a temp dir produces several, so the entries are merged:
    a line counts as covered if any process hit it.
    """
    hits: dict[int, int] = {}
    for xml_path in out_dir.rglob("cov.xml"):
        for cls in ElementTree.parse(xml_path).iter("class"):
            if Path(cls.get("filename", "")).name != subject:
                continue
            for line in cls.iter("line"):
                number = line.get("number")
                if number is None:
                    continue
                key = int(number)
                hits[key] = hits.get(key, 0) + int(line.get("hits", "0"))
    return hits


def _find_source(subject: str, trace_dir: Path | None) -> Path | None:
    """Locate *subject*'s source file so its non-statements can be excluded.

    kcov records `filename="dwm_config.sh"` -- a bare BASENAME, not a path --
    so the XML cannot supply the source location. The PS4 trace can: it
    carries ${BASH_SOURCE}, an absolute path, for every line it reports.
    Falling back to a repo search keeps the exclusion working for a subject
    whose trace is empty.
    """
    if trace_dir is not None:
        for candidate in _LINES.traced_paths(trace_dir, subject):
            if candidate.is_file():
                return candidate
    matches = sorted(Path(__file__).resolve().parents[2].rglob(subject))
    real = [m for m in matches if m.is_file() and ".git" not in m.parts]
    # Exactly one match, or the exclusion would be applied from the wrong
    # file. Ambiguity is reported by the caller as "no exclusions" rather
    # than silently guessing, which could only inflate coverage.
    return real[0] if len(real) == 1 else None


def _measure(
    out_dir: Path, subject: str, trace_dir: Path | None
) -> tuple[int, int, list[str], int]:
    """Return (covered, total, uncovered line numbers, off-set trace count)."""
    hits = _kcov_lines(out_dir, subject)
    if not hits:
        return 0, 0, [], 0

    source = _find_source(subject, trace_dir)
    excluded = continuation_lines(source) if source is not None else set()
    denominator = set(hits) - excluded

    executed = {line for line, count in hits.items() if count > 0}
    traced: set[int] = set()
    if trace_dir is not None:
        traced = traced_lines(trace_dir, subject)

    # Lines the trace saw executing that kcov never listed as instrumentable.
    # Dropped from the numerator (they are not in the denominator), but
    # surfaced: a non-zero count means kcov's LINE SET is wrong too, which is
    # a third defect this design cannot correct for.
    off_set = len(traced - set(hits) - excluded)

    covered_set = (executed | traced) & denominator
    uncovered = sorted(denominator - covered_set)
    return len(covered_set), len(denominator), [str(n) for n in uncovered], off_set


# argv: <cov-dir> <subject> <minimum> [<trace-dir>]. The trace dir is optional
# so the report still runs against a kcov-only output directory.
_ARGV_WITH_TRACE = 5


def main() -> None:
    """Print the coverage summary and gate on the minimum percentage."""
    out_dir, subject, minimum = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3])
    trace_dir = Path(sys.argv[4]) if len(sys.argv) >= _ARGV_WITH_TRACE else None

    covered, total, uncovered, off_set = _measure(out_dir, subject, trace_dir)
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
    if off_set:
        sys.stdout.write(
            f"  note: {off_set} traced line(s) are absent from kcov's line set\n"
        )

    if percent < minimum:
        sys.exit(f"coverage {percent:.2f}% is below the required {minimum:.2f}%")


if __name__ == "__main__":
    main()
