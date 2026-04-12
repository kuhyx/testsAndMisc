"""Tests for python_pkg.fm24_searcher.cli."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

import zstandard

from python_pkg.fm24_searcher.binary_parser import TAD_MAGIC
from python_pkg.fm24_searcher.cli import (
    _DEFAULT_LIMIT,
    _format_player,
    _format_tsv_header,
    _format_tsv_row,
    _print_stats,
    build_parser,
    run_dump,
)
from python_pkg.fm24_searcher.models import ALL_VISIBLE_ATTRS, Player

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _zstd_compress(data: bytes) -> bytes:
    """Compress data with zstd."""
    cctx = zstandard.ZstdCompressor()
    result: bytes = cctx.compress(data)
    return result


def _make_tad(payload: bytes) -> bytes:
    """Create a TAD-formatted blob."""
    return TAD_MAGIC + _zstd_compress(payload)


def _make_player_record(
    name: str,
    *,
    day_of_year: int = 180,
    year: int = 1995,
) -> bytes:
    """Build a minimal binary player record."""
    name_bytes = name.encode("utf-8")
    rec = b"\x00"
    rec += struct.pack("<I", len(name_bytes))
    rec += name_bytes
    rec += struct.pack("<H", day_of_year)
    rec += struct.pack("<H", year)
    rec += b"\x07\x03\x0b\x06\x0c"
    rec += b"\x8b\x00\x00\x00\x01\x03\x00\x00"
    rec += b"\x0a\x0b\x0c\x0d\x0e\x0f\x10\x05"
    return rec


def _make_db(tmp_path: Path, names: list[str]) -> Path:
    """Build a minimal TAD database file."""
    sep = b"\x05\x00\x00\x00\x00"
    inner = b"\x00" * 8 + struct.pack("<I", len(names))
    for name in names:
        inner += sep + _make_player_record(name)
    inner += b"\x00" * 50
    filepath = tmp_path / "people_db.dat"
    filepath.write_bytes(_make_tad(inner))
    return filepath


class TestFormatPlayer:
    """_format_player tests."""

    def test_basic_fields(self) -> None:
        p = Player(
            name="Test Player",
            date_of_birth="1995-06-29",
            source="binary",
            uid=100,
        )
        result = _format_player(p)
        assert "=== Test Player ===" in result
        assert "DOB: 1995-06-29" in result
        assert "Source: binary" in result
        assert "UID (byte offset): 100" in result

    def test_with_attrs(self) -> None:
        p = Player(
            name="Star",
            attributes={"Crossing": 15, "Finishing": 18},
            source="binary",
        )
        result = _format_player(p, show_attrs=True)
        assert "Crossing: 15" in result
        assert "Finishing: 18" in result
        assert "Missing attrs:" in result

    def test_no_attrs_block(self) -> None:
        p = Player(name="Noattr", source="binary")
        result = _format_player(p, show_attrs=True)
        assert "(no attribute block found)" in result

    def test_all_optional_fields(self) -> None:
        p = Player(
            name="Full",
            current_ability=160,
            potential_ability=190,
            nationality="Argentina",
            club="Inter Miami",
            position="AM (R,C), ST",
            personality=[10, 11, 12, 13, 14, 15, 16, 5],
            source="binary",
        )
        result = _format_player(p)
        assert "CA: 160" in result
        assert "PA: 190" in result
        assert "Nationality: Argentina" in result
        assert "Club: Inter Miami" in result
        assert "Position: AM (R,C), ST" in result
        assert "Personality bytes:" in result

    def test_no_optional_fields(self) -> None:
        p = Player(name="Minimal", source="binary", uid=0)
        result = _format_player(p)
        assert "DOB:" not in result
        assert "CA:" not in result
        assert "PA:" not in result

    def test_attrs_all_present(self) -> None:
        attrs = dict.fromkeys(ALL_VISIBLE_ATTRS, 10)
        p = Player(name="Complete", attributes=attrs, source="binary")
        result = _format_player(p, show_attrs=True)
        assert "Missing attrs:" not in result

    def test_attrs_show_false(self) -> None:
        p = Player(
            name="Skip",
            attributes={"Crossing": 15},
            source="binary",
        )
        result = _format_player(p, show_attrs=False)
        assert "Crossing" not in result


class TestFormatTsv:
    """TSV formatting tests."""

    def test_header_without_attrs(self) -> None:
        hdr = _format_tsv_header(show_attrs=False)
        assert hdr == "Name\tDOB\tCA\tPA\tPersonality\tUID"

    def test_header_with_attrs(self) -> None:
        hdr = _format_tsv_header(show_attrs=True)
        assert "Corners" in hdr
        assert "Acceleration" in hdr

    def test_row_basic(self) -> None:
        p = Player(
            name="John",
            date_of_birth="1995-01-01",
            personality=[1, 2, 3],
            uid=50,
            source="binary",
        )
        row = _format_tsv_row(p, show_attrs=False)
        parts = row.split("\t")
        assert parts[0] == "John"
        assert parts[1] == "1995-01-01"
        assert parts[4] == "1,2,3"
        assert parts[5] == "50"

    def test_row_with_attrs(self) -> None:
        p = Player(
            name="Star",
            attributes={"Crossing": 15},
            uid=10,
            source="binary",
        )
        row = _format_tsv_row(p, show_attrs=True)
        assert "15" in row

    def test_row_empty_fields(self) -> None:
        p = Player(name="Empty", uid=0, source="binary")
        row = _format_tsv_row(p, show_attrs=False)
        parts = row.split("\t")
        assert parts[2] == ""  # CA
        assert parts[3] == ""  # PA


class TestBuildParser:
    """build_parser tests."""

    def test_defaults(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--dump"])
        assert args.dump is True
        assert args.search == ""
        assert args.limit == _DEFAULT_LIMIT
        assert args.attrs is False
        assert args.tsv is False

    def test_all_flags(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "--dump",
                "--search",
                "Messi",
                "--limit",
                "10",
                "--attrs",
                "--tsv",
                "--with-attrs-only",
                "--stats",
            ]
        )
        assert args.search == "Messi"
        assert args.limit == 10
        assert args.attrs is True
        assert args.tsv is True
        assert args.with_attrs_only is True
        assert args.stats is True

    def test_custom_db(self, tmp_path: Path) -> None:
        parser = build_parser()
        db_path = str(tmp_path)
        args = parser.parse_args(["--dump", "--db", db_path])
        assert args.db == db_path


class TestPrintStats:
    """_print_stats tests."""

    def test_basic_stats(self, capsys: pytest.CaptureFixture[str]) -> None:
        players = [
            Player(
                name="A",
                date_of_birth="1995-01-01",
                attributes={"Crossing": 15, "Finishing": 18},
                current_ability=160,
                source="binary",
            ),
            Player(name="B", source="binary"),
        ]
        _print_stats(players)
        out = capsys.readouterr().out
        assert "Total players: 2" in out
        assert "With DOB: 1" in out
        assert "With attributes: 1" in out
        assert "With CA/PA: 1" in out
        assert "Crossing" in out

    def test_empty_players(self, capsys: pytest.CaptureFixture[str]) -> None:
        _print_stats([])
        out = capsys.readouterr().out
        assert "Total players: 0" in out

    def test_no_attrs(self, capsys: pytest.CaptureFixture[str]) -> None:
        players = [Player(name="X", source="binary")]
        _print_stats(players)
        out = capsys.readouterr().out
        assert "With attributes: 0" in out
        # No attr coverage section when no attrs
        assert "Attribute coverage" not in out


class TestRunDump:
    """run_dump integration tests."""

    def test_no_dump_flag(self) -> None:
        assert run_dump([]) == 1

    def test_db_not_found(self) -> None:
        result = run_dump(["--dump", "--db", "/nonexistent/db.dat"])
        assert result == 2

    def test_dump_text(self, tmp_path: Path) -> None:
        db = _make_db(tmp_path, ["Alpha Beta", "Gamma Delta"])
        result = run_dump(
            [
                "--dump",
                "--db",
                str(db),
                "--limit",
                "5",
            ]
        )
        assert result == 0

    def test_dump_text_output(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        db = _make_db(tmp_path, ["Alpha Beta"])
        run_dump(["--dump", "--db", str(db), "--limit", "5"])
        out = capsys.readouterr().out
        assert "Alpha Beta" in out
        assert "Showing" in out

    def test_dump_tsv(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        db = _make_db(tmp_path, ["TSV Player"])
        run_dump(["--dump", "--db", str(db), "--tsv"])
        out = capsys.readouterr().out
        assert "Name\tDOB\tCA\tPA" in out
        assert "TSV Player" in out

    def test_dump_with_search(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        db = _make_db(tmp_path, ["Alpha Beta", "Gamma Delta"])
        run_dump(["--dump", "--db", str(db), "--search", "alpha"])
        out = capsys.readouterr().out
        assert "Alpha Beta" in out
        assert "Gamma Delta" not in out

    def test_dump_with_attrs(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        db = _make_db(tmp_path, ["Attr Check"])
        run_dump(["--dump", "--db", str(db), "--attrs"])
        out = capsys.readouterr().out
        assert "Attr Check" in out

    def test_dump_tsv_with_attrs(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        db = _make_db(tmp_path, ["TSV Attrs"])
        run_dump(["--dump", "--db", str(db), "--tsv", "--attrs"])
        out = capsys.readouterr().out
        assert "Corners" in out

    def test_dump_with_attrs_only(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        db = _make_db(tmp_path, ["No Attrs"])
        run_dump(["--dump", "--db", str(db), "--with-attrs-only"])
        out = capsys.readouterr().out
        # No players should have attrs in synthetic data.
        assert "Showing 0 of 0" in out

    def test_dump_stats(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        db = _make_db(tmp_path, ["Stats Test"])
        result = run_dump(["--dump", "--db", str(db), "--stats"])
        assert result == 0
        out = capsys.readouterr().out
        assert "Total players:" in out

    def test_progress_goes_to_stderr(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        db = _make_db(tmp_path, ["Progress"])
        run_dump(["--dump", "--db", str(db)])
        err = capsys.readouterr().err
        assert "Decompressing" in err
