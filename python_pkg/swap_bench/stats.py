"""Turn the raw files of one swap_bench.sh run into one TSV row.

swap_bench.sh copies /proc and /sys files into a run directory:

- ``before/`` and ``after/``: vmstat, pressure (global PSI), zram_stat and
  mm_stat (absent without zram), desktop_pressure (every login session
  scope's PSI, concatenated);
- ``peak/``: mm_stat, meminfo and the scope's memory.stat, copied by the
  workload while its mapping is still live;
- ``cg_pressure`` and ``cg_memory.stat``: the scope's totals at exit;
- ``workload.txt``: the workload's ``key=value`` output.

On the host the scope's own counters are used (the desktop keeps running);
in a VM the whole guest is the experiment, so global deltas are used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

COLUMNS = (
    "date",
    "env",
    "setup",
    "seed",
    "size_mib",
    "pages",
    "fill_crc",
    "touch_crc",
    "seconds",
    "ratio",
    "psi_some_ms",
    "psi_full_ms",
    "majflt",
    "disk_wb_pages",
    "zswpwb",
    "global_full_avg10",
    "desktop_full_ms",
    "outside_pswpout",
)
_SECTOR_PER_PAGE = 8  # 512-byte sectors in a 4 KiB page


def _read(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def _kv(path: Path, sep: str | None = None) -> dict[str, int]:
    """Parse ``key value`` (or ``key: value kB``) lines into ints."""
    out: dict[str, int] = {}
    for line in _read(path).splitlines():
        key, _, rest = line.partition(":") if sep else line.partition(" ")
        out[key.strip()] = int(rest.split()[0])
    return out


def _fields(path: Path) -> list[int]:
    return [int(x) for x in _read(path).split()]


def _psi(path: Path) -> dict[str, dict[str, float]]:
    """Parse a PSI file into ``{"some": {...}, "full": {...}}``."""
    out: dict[str, dict[str, float]] = {}
    for line in _read(path).splitlines():
        kind, *pairs = line.split()
        out[kind] = {k: float(v) for k, v in (p.split("=") for p in pairs)}
    return out


def _full_total(path: Path) -> float:
    """Sum the ``full`` stall totals of a file holding several PSI files."""
    return sum(
        float(line.split("total=")[1])
        for line in _read(path).splitlines()
        if line.startswith("full")
    )


def _desktop_full_ms(run: Path, env: str) -> str:
    """Stall the login sessions saw; ``na`` in a VM, whose bench runs in one."""
    if env != "host" or not (run / "before/desktop_pressure").exists():
        return "na"
    delta = _full_total(run / "after/desktop_pressure") - _full_total(
        run / "before/desktop_pressure"
    )
    return str(round(delta / 1000))


def _outside_pswpout(
    run: Path, env: str, before: dict[str, int], after: dict[str, int]
) -> str:
    """Pages the rest of the host swapped out during a host run.

    Global pswpout minus the scope's own. zram's pool is not charged to the
    scope, so a zram run can make global reclaim swap other processes out
    too. A VM run has no outside: ``na``.
    """
    if env != "host":
        return "na"
    scope_out = _kv(run / "cg_memory.stat").get("pswpout", 0)
    return str(after["pswpout"] - before["pswpout"] - scope_out)


def _ratio(stored_in: float, stored_out: float) -> str:
    return f"{stored_in / stored_out:.2f}" if stored_out > 0 else "na"


def _zram_delta(run: Path, a: str, b: str, index: int) -> int:
    first, last = _fields(run / a), _fields(run / b)
    return last[index] - first[index] if first and last else 0


def _compute_ratio(run: Path, env: str, setup: str) -> str:
    if setup == "zram":
        return _ratio(
            _zram_delta(run, "before/mm_stat", "peak/mm_stat", 0),
            _zram_delta(run, "before/mm_stat", "peak/mm_stat", 1),
        )
    if env == "host":
        cg = _kv(run / "peak/memory.stat")
        return _ratio(cg.get("zswapped", 0), cg.get("zswap", 0))
    mem = _kv(run / "peak/meminfo", sep=":")
    return _ratio(mem.get("Zswapped", 0), mem.get("Zswap", 0))


def compute_row(
    run: Path, *, env: str, setup: str, seed: int, size_mib: int, date: str
) -> dict[str, str]:
    """Return one result row (all values as strings) for run directory ``run``."""
    if env not in {"host", "vm"}:
        msg = f"env must be host or vm, got {env!r}"
        raise ValueError(msg)
    work = dict(line.split("=", 1) for line in _read(run / "workload.txt").split())
    before, after = _kv(run / "before/vmstat"), _kv(run / "after/vmstat")
    zram_pages = (
        _zram_delta(run, "before/zram_stat", "after/zram_stat", 6) // _SECTOR_PER_PAGE
    )
    disk_wb = max(0, after["pswpout"] - before["pswpout"] - zram_pages)
    if env == "host":
        psi = _psi(run / "cg_pressure")
        some, full = psi["some"]["total"], psi["full"]["total"]
        zswpwb = _kv(run / "cg_memory.stat").get("zswpwb", 0)
    else:
        g0, g1 = _psi(run / "before/pressure"), _psi(run / "after/pressure")
        some = g1["some"]["total"] - g0["some"]["total"]
        full = g1["full"]["total"] - g0["full"]["total"]
        zswpwb = after.get("zswpwb", 0) - before.get("zswpwb", 0)
    values = {
        "date": date,
        "env": env,
        "setup": setup,
        "seed": str(seed),
        "size_mib": str(size_mib),
        "pages": work["pages"],
        "fill_crc": work["fill_crc"],
        "touch_crc": work["touch_crc"],
        "seconds": work["seconds"],
        "ratio": _compute_ratio(run, env, setup),
        "psi_some_ms": str(round(some / 1000)),
        "psi_full_ms": str(round(full / 1000)),
        "majflt": work["majflt"],
        "disk_wb_pages": str(disk_wb),
        "zswpwb": str(zswpwb),
        "global_full_avg10": f"{_psi(run / 'after/pressure')['full']['avg10']:.2f}",
        "desktop_full_ms": _desktop_full_ms(run, env),
        "outside_pswpout": _outside_pswpout(run, env, before, after),
    }
    return {c: values[c] for c in COLUMNS}


def format_row(row: dict[str, str] | None) -> str:
    """Tab-join a row in column order; ``None`` gives the header line."""
    return "\t".join(COLUMNS if row is None else (row[c] for c in COLUMNS))
