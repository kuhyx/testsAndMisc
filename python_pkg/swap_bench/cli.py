"""``python -m python_pkg.swap_bench run|row|summary`` for swap_bench.sh."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from python_pkg.swap_bench.stats import compute_row, format_row
from python_pkg.swap_bench.summary import summarize
from python_pkg.swap_bench.workload import Spec, run


def _snapshot(text: str) -> tuple[Path, Path]:
    src, sep, dest = text.partition("=")
    if not sep:
        msg = f"--snapshot wants SRC=DEST, got {text!r}"
        raise argparse.ArgumentTypeError(msg)
    return Path(src), Path(dest)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swap_bench")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="run the seeded workload once")
    p_run.add_argument("--size-mib", type=int, required=True)
    p_run.add_argument("--seed", type=int, required=True)
    p_run.add_argument("--rounds", type=int, default=3)
    p_run.add_argument("--hot-share", type=float, default=0.25)
    p_run.add_argument("--snapshot", type=_snapshot, action="append", default=[])
    p_row = sub.add_parser("row", help="print one TSV row for a run directory")
    p_row.add_argument("--dir", type=Path, required=True)
    p_row.add_argument("--env", required=True)
    p_row.add_argument("--setup", required=True)
    p_row.add_argument("--seed", type=int, required=True)
    p_row.add_argument("--size-mib", type=int, required=True)
    p_row.add_argument("--date", required=True)
    p_row.add_argument("--header", action="store_true", help="print the header first")
    p_row.add_argument(
        "--max-desktop-ms",
        type=int,
        help="exit 3 when a host run stalled the login sessions longer",
    )
    p_sum = sub.add_parser("summary", help="medians and the winner for a TSV")
    p_sum.add_argument("tsv", type=Path)
    return parser


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        spec = Spec(
            size_mib=args.size_mib,
            seed=args.seed,
            rounds=args.rounds,
            hot_share=args.hot_share,
        )
    except ValueError as exc:
        sys.stderr.write(f"swap_bench: {exc}\n")
        return 2
    result = run(spec, args.snapshot)
    for field in ("pages", "fill_crc", "touch_crc", "majflt", "seconds"):
        sys.stdout.write(f"{field}={getattr(result, field)}\n")
    return 0


def _cmd_row(args: argparse.Namespace) -> int:
    row = compute_row(
        args.dir,
        env=args.env,
        setup=args.setup,
        seed=args.seed,
        size_mib=args.size_mib,
        date=args.date,
    )
    if args.header:
        sys.stdout.write(format_row(None) + "\n")
    sys.stdout.write(format_row(row) + "\n")
    stall, limit = row["desktop_full_ms"], args.max_desktop_ms
    if limit is not None and stall != "na" and int(stall) > limit:
        sys.stderr.write(
            f"swap_bench: the login sessions stalled {stall} ms "
            f"(limit {limit} ms): this run pressed the desktop\n"
        )
        return 3
    return 0


def main(argv: list[str] | None = None) -> int:
    """Dispatch a subcommand; return its exit code."""
    args = _parser().parse_args(argv)
    if args.cmd == "run":
        return _cmd_run(args)
    if args.cmd == "row":
        return _cmd_row(args)
    sys.stdout.write(summarize(args.tsv))
    return 0
