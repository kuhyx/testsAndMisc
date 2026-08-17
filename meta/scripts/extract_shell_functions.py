#!/usr/bin/env python3
"""Move a shell script's top-level functions into a sourced library, verbatim.

Line-range slicing is the obvious approach and it is wrong: these scripts
interleave top-level commands between their function definitions, so a range
slice sweeps those commands into the library, where they run at source time
and in the wrong order. This walks the file brace-by-brace instead, lifts only
the function blocks (with the comment directly above each), and leaves every
other line exactly where it was.

Verify the result with meta/scripts/verify_shell_split.sh.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

_FUNC_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\(\)\s*\{")


def find_function_blocks(lines: list[str]) -> list[tuple[int, int, str]]:
    """Return (start, end, name) for each top-level function, brace-matched."""
    blocks: list[tuple[int, int, str]] = []
    index = 0
    while index < len(lines):
        if _FUNC_RE.match(lines[index]):
            start, depth = index, 0
            while index < len(lines):
                depth += lines[index].count("{") - lines[index].count("}")
                # A one-line `name() { ...; }` closes on its opening line, so
                # the depth check must accept index == start.
                if depth <= 0:
                    break
                index += 1
            blocks.append((start, index, lines[start].split("(")[0]))
        index += 1
    return blocks


def split_script(
    path: Path, lib_path: Path, names: list[str] | None, header: str
) -> tuple[int, int]:
    """Move the named functions (or all of them) into *lib_path*."""
    lines = path.read_text().split("\n")
    before_len = len(lines)
    blocks = find_function_blocks(lines)
    if names:
        blocks = [b for b in blocks if b[2] in names]
        missing = set(names) - {b[2] for b in blocks}
        if missing:
            sys.exit(f"no such top-level function(s): {', '.join(sorted(missing))}")
    if not blocks:
        sys.exit(f"no top-level functions to move out of {path}")

    parts: list[str] = []
    drop: set[int] = set()
    for start, end, _name in blocks:
        head = start
        while head - 1 >= 0 and lines[head - 1].lstrip().startswith("#"):
            head -= 1
        parts.append("\n".join(lines[head : end + 1]))
        drop.update(range(head, end + 1))

    kept = [ln for n, ln in enumerate(lines) if n not in drop]
    rel = lib_path.relative_to(path.parent)
    source_line = '. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/' + str(rel) + '"'
    out: list[str] = []
    inserted = False
    for line in kept:
        out.append(line)
        # `set -e # comment` is common here, so match the directive, not the line.
        if not inserted and re.match(r"^set -[euo pipefail]+\b", line.strip()):
            out += ["", f"# shellcheck source={rel}", source_line]
            inserted = True

    # Both files are written only once the whole split is known to be
    # expressible. Writing the library before this point and then exiting on a
    # missing anchor left the functions defined in BOTH files, so the entry
    # script came out longer than it started -- a duplicate-definition split
    # that still lints clean and still passes a function-body hash check.
    # A split that does not shrink the entry script did not move anything; it
    # duplicated. Refuse rather than write, since the result lints clean and
    # passes a function-body hash check while defining every function twice.
    if len(out) >= before_len:
        sys.exit(
            f"refusing to write: {path} would go from {before_len} to {len(out)} "
            f"lines, so nothing was actually moved out of it"
        )

    lib_path.parent.mkdir(parents=True, exist_ok=True)
    lib_path.write_text(header.rstrip() + "\n\n" + "\n\n".join(parts) + "\n")
    path.write_text("\n".join(out))

    if not inserted:
        sys.stderr.write(
            f"warning: no `set -e` line in {path} to anchor the source directive.\n"
            f"         The functions were moved and {lib_path.name} was written, "
            f"but nothing sources it yet.\n"
            f'         Add this by hand, after the existing `. "$SCRIPT_DIR/..."` '
            f"line:\n"
            f"             # shellcheck source={rel}\n"
            f'             . "$SCRIPT_DIR/{rel}"\n'
        )
    return len(out), len(lib_path.read_text().split("\n"))


def main() -> None:
    """Extract functions from a script into a library beside it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path)
    parser.add_argument("library", type=Path)
    parser.add_argument(
        "--functions",
        help="comma-separated function names to move (default: all)",
    )
    parser.add_argument(
        "--header",
        default="#!/usr/bin/env bash\n# Helpers sourced by the entry script.",
        help="header comment for the generated library",
    )
    args = parser.parse_args()
    names = args.functions.split(",") if args.functions else None
    entry_len, lib_len = split_script(args.script, args.library, names, args.header)
    sys.stdout.write(
        f"{args.script}: {entry_len} lines\n{args.library}: {lib_len} lines\n"
    )


if __name__ == "__main__":
    main()
