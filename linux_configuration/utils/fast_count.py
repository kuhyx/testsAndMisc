#!/usr/bin/env python3
"""Print the most common whole-line entries read from stdin.

Reads lines from stdin, counts identical (trailing-whitespace-stripped) lines,
and writes the ``argv[1]`` most common as ``<count> <line>`` rows to stdout. Used
by ``analyze_repo.sh`` as the fallback word counter when the Rust ``counts`` tool
is unavailable.

Kept as a standalone module (not inline ``python3 -c`` in the shell script) so the
repository's Python tooling applies; see CLAUDE.md "Shell Style".
"""

from __future__ import annotations

from collections import Counter
import sys

_DEFAULT_TOP_N = 50


def main() -> int:
    """Count stdin lines and print the top-N most frequent to stdout."""
    args = sys.argv[1:]
    top_n = int(args[0]) if args else _DEFAULT_TOP_N
    counter = Counter(line.rstrip() for line in sys.stdin)
    sys.stdout.write(
        "".join(f"{count} {word}\n" for word, count in counter.most_common(top_n)),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
