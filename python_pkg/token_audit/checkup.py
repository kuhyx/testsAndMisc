"""The weekly standing-cost checkup.

Complements the spend report. That report answers "where did the tokens go";
this answers "what is still being paid for every turn regardless of use", which
is the question earlier audits kept answering by memory and kept getting wrong.

Run as ``python3 -m python_pkg.token_audit.checkup``.
"""

from __future__ import annotations

import sys

from python_pkg.token_audit import surfaces, unused
from python_pkg.token_audit.probe import weighted_pct


def _fmt_usage(rows: list[unused.Usage]) -> list[str]:
    """Render call counts, marking only rows dead in BOTH windows."""
    header = (
        f"| name | {unused.SHORT_WINDOW_DAYS}d | {unused.LONG_WINDOW_DAYS}d | verdict |"
    )
    lines = [header, "|---|---|---|---|"]
    for row in rows:
        verdict = "**park**" if row.dead else "keep"
        lines.append(
            f"| {row.name} | {row.short_calls} | {row.long_calls} | {verdict} |"
        )
    return lines


def build(turns: int, weighted_total: int) -> str:
    """Render the checkup as markdown."""
    out = ["# Standing-cost checkup", ""]
    out.append(
        "Every row below is billed on each of "
        f"{turns:,} turns. Shares are weighted (cache-read weight 0.1)."
    )
    out.append("")
    out.append("## Surfaces")
    out.append("| surface | est tokens | share | detail |")
    out.append("|---|---|---|---|")
    for surface in surfaces.collect():
        share = weighted_pct(surface.est_tokens, turns, weighted_total)
        est = f"{surface.est_tokens:,}" if surface.est_tokens else "A/B only"
        out.append(f"| {surface.name} | {est} | {share:.2f}% | {surface.detail} |")
    out += ["", "## MCP servers", ""]
    out += _fmt_usage(unused.mcp_usage())
    out += ["", "## Skills", ""]
    out += _fmt_usage(unused.skill_usage())
    out += [
        "",
        "_A surface marked `A/B only` cannot be sized from disk; measure it",
        "with `probe.measure()`, which runs non-strict so project `.mcp.json`",
        "files are included._",
        "",
    ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """Print the checkup, taking turns and weighted total from the last report."""
    argv = sys.argv[1:] if argv is None else argv
    turns = int(argv[0]) if argv else 44311
    total = int(argv[1]) if len(argv) > 1 else 1230346533
    sys.stdout.write(build(turns, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
