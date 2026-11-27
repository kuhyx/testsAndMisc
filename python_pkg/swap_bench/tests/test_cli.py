"""Tests for the swap_bench command line."""

from __future__ import annotations

import runpy
from typing import TYPE_CHECKING

import pytest

from python_pkg.swap_bench import cli
from python_pkg.swap_bench.stats import COLUMNS

if TYPE_CHECKING:
    from pathlib import Path


def _out(capsys: pytest.CaptureFixture[str]) -> str:
    return capsys.readouterr().out


def test_run_prints_key_value_lines(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """``run`` prints one key=value line per result field."""
    src = tmp_path / "s"
    src.write_text("x")
    argv = [
        "run",
        "--size-mib",
        "1",
        "--seed",
        "5",
        "--rounds",
        "1",
        "--snapshot",
        f"{src}={tmp_path / 'd'}",
    ]
    assert cli.main(argv) == 0
    lines = dict(line.split("=", 1) for line in _out(capsys).splitlines())
    assert lines["pages"] == "256"
    assert set(lines) == {"pages", "fill_crc", "touch_crc", "majflt", "seconds"}
    assert (tmp_path / "d").read_text() == "x"


def test_run_rejects_bad_spec(capsys: pytest.CaptureFixture[str]) -> None:
    """A bad spec exits 2 with the reason on stderr."""
    assert cli.main(["run", "--size-mib", "0", "--seed", "5"]) == 2
    assert "size_mib" in capsys.readouterr().err


def test_run_rejects_bad_snapshot() -> None:
    """A snapshot without ``=`` is a usage error."""
    with pytest.raises(SystemExit):
        cli.main(["run", "--size-mib", "1", "--seed", "1", "--snapshot", "nope"])


def test_row_with_and_without_header(
    capsys: pytest.CaptureFixture[str], run_dir: Path
) -> None:
    """``row`` prints the TSV row, optionally after the header."""
    base = ["row", "--dir", str(run_dir), "--env", "host", "--setup", "zram"]
    base += ["--seed", "1", "--size-mib", "1", "--date", "d"]
    assert cli.main([*base, "--header"]) == 0
    header, row = _out(capsys).splitlines()
    assert header.split("\t") == list(COLUMNS)
    assert row.startswith("d\thost\tzram\t")
    assert cli.main(base) == 0
    assert len(_out(capsys).splitlines()) == 1


@pytest.mark.parametrize(
    ("env", "limit", "code"),
    [("host", 5, 3), ("host", 6, 0), ("vm", 0, 0)],
)
def test_row_fails_when_the_desktop_stalled(
    capsys: pytest.CaptureFixture[str],
    run_dir: Path,
    env: str,
    limit: int,
    code: int,
) -> None:
    """A host row whose desktop stall (6 ms here) passes the limit exits 3."""
    argv = ["row", "--dir", str(run_dir), "--env", env, "--setup", "zram"]
    argv += ["--seed", "1", "--size-mib", "1", "--date", "d"]
    assert cli.main([*argv, "--max-desktop-ms", str(limit)]) == code
    out, err = capsys.readouterr()
    assert out.startswith("d\t")  # the row is printed either way
    assert ("the login sessions stalled 6 ms" in err) == (code == 3)


def test_summary(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """``summary`` prints the medians table."""
    path = tmp_path / "r.tsv"
    path.write_text("\t".join(COLUMNS) + "\n")
    assert cli.main(["summary", str(path)]) == 0
    assert "| env | setup |" in _out(capsys)


def test_module_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    """``python -m python_pkg.swap_bench`` delegates to cli.main."""
    calls: list[int] = []

    def fake_main() -> int:
        calls.append(1)
        return 0

    monkeypatch.setattr(cli, "main", fake_main)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("python_pkg.swap_bench", run_name="__main__")
    assert exc.value.code == 0
    assert calls == [1]
