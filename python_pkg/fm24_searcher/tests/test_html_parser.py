"""Tests for python_pkg.fm24_searcher.html_parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.fm24_searcher.html_parser import (
    _extract_tables,
    _normalize_header,
    _strip_html,
    merge_players,
    parse_html_export,
)
from python_pkg.fm24_searcher.models import Player

if TYPE_CHECKING:
    from pathlib import Path


class TestStripHtml:
    """_strip_html tests."""

    def test_removes_tags(self) -> None:
        assert _strip_html("<b>bold</b>") == "bold"

    def test_decodes_entities(self) -> None:
        assert _strip_html("&amp; &lt;") == "& <"

    def test_collapses_whitespace(self) -> None:
        assert _strip_html("  hello   world  ") == "hello world"

    def test_nested_tags(self) -> None:
        assert _strip_html("<div><span>text</span></div>") == "text"


class TestNormalizeHeader:
    """_normalize_header tests."""

    def test_direct_map(self) -> None:
        assert _normalize_header("cor") == "Corners"
        assert _normalize_header("fin") == "Finishing"

    def test_full_name_lower(self) -> None:
        assert _normalize_header("Acceleration") == "Acceleration"

    def test_truncated_3char(self) -> None:
        assert _normalize_header("crossing") == "Crossing"

    def test_unknown(self) -> None:
        assert _normalize_header("xyz") is None

    def test_truncated_prefix_only(self) -> None:
        """Full string not in map but first 3 chars match (line 113)."""
        assert _normalize_header("corxxx") == "Corners"

    def test_html_in_header(self) -> None:
        assert _normalize_header("<b>cor</b>") == "Corners"

    def test_goalkeeper_attr(self) -> None:
        assert _normalize_header("han") == "Handling"
        assert _normalize_header("ref") == "Reflexes"


class TestExtractTables:
    """_extract_tables tests."""

    def test_single_table(self) -> None:
        html = (
            "<table><tr><th>Name</th><th>Age</th></tr>"
            "<tr><td>John</td><td>25</td></tr></table>"
        )
        tables = _extract_tables(html)
        assert len(tables) == 1
        assert tables[0][0] == ["Name", "Age"]
        assert tables[0][1] == ["John", "25"]

    def test_multiple_tables(self) -> None:
        html = "<table><tr><td>A</td></tr></table><table><tr><td>B</td></tr></table>"
        tables = _extract_tables(html)
        assert len(tables) == 2

    def test_empty_table_filtered(self) -> None:
        html = "<table></table><table><tr><td>X</td></tr></table>"
        tables = _extract_tables(html)
        assert len(tables) == 1

    def test_nested_html_stripped(self) -> None:
        html = "<table><tr><td><b>Bold</b></td></tr></table>"
        tables = _extract_tables(html)
        assert tables[0][0] == ["Bold"]

    def test_row_without_cells(self) -> None:
        """Row with no cells is skipped (branch 140→135)."""
        html = "<table><tr></tr><tr><td>valid</td></tr></table>"
        tables = _extract_tables(html)
        assert len(tables) == 1
        assert len(tables[0]) == 1
        assert tables[0][0] == ["valid"]


class TestParseHtmlExport:
    """parse_html_export tests."""

    def _write_html(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "export.html"
        p.write_text(content, encoding="utf-8")
        return p

    def test_basic_table(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>Age</th><th>CA</th>"
            "<th>PA</th><th>Pac</th><th>Sta</th></tr>"
            "<tr><td>John Smith</td><td>25</td><td>170</td>"
            "<td>180</td><td>18</td><td>15</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        players = parse_html_export(p)
        assert len(players) == 1
        assert players[0].name == "John Smith"
        assert players[0].current_ability == 170
        assert players[0].potential_ability == 180
        assert players[0].attributes["Pace"] == 18
        assert players[0].attributes["Stamina"] == 15
        assert players[0].source == "html"

    def test_no_name_column(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>CA</th><th>PA</th></tr>"
            "<tr><td>170</td><td>180</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        assert parse_html_export(p) == []

    def test_table_too_few_rows(self, tmp_path: Path) -> None:
        html = "<table><tr><th>Name</th></tr></table>"
        p = self._write_html(tmp_path, html)
        assert parse_html_export(p) == []

    def test_row_shorter_than_name_col(self, tmp_path: Path) -> None:
        html = (
            "<table><tr><th>A</th><th>Name</th></tr><tr><td>only_one</td></tr></table>"
        )
        p = self._write_html(tmp_path, html)
        assert parse_html_export(p) == []

    def test_empty_name_skipped(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th></tr>"
            "<tr><td></td></tr>"
            "<tr><td>Valid</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        players = parse_html_export(p)
        assert len(players) == 1
        assert players[0].name == "Valid"

    def test_invalid_ca_pa(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>CA</th><th>PA</th></tr>"
            "<tr><td>Test</td><td>abc</td><td>xyz</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        players = parse_html_export(p)
        assert players[0].current_ability == 0

    def test_attr_col_beyond_row_length(self, tmp_path: Path) -> None:
        """Attribute col index >= row length (branch 240→239)."""
        html = (
            "<table>"
            "<tr><th>Name</th><th>Cor</th><th>Pac</th></tr>"
            "<tr><td>Player</td><td>15</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        players = parse_html_export(p)
        assert len(players) == 1
        assert players[0].attributes.get("Corners") == 15
        assert "Pace" not in players[0].attributes
        assert players[0].potential_ability == 0

    def test_club_nat_pos_value_wage(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>Club</th><th>Nat</th>"
            "<th>Position</th><th>Value</th><th>Wage</th></tr>"
            "<tr><td>John</td><td>Madrid</td><td>Spain</td>"
            "<td>AMC</td><td>€50M</td><td>€200K</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        players = parse_html_export(p)
        assert players[0].club == "Madrid"
        assert players[0].nationality == "Spain"
        assert players[0].position == "AMC"
        assert players[0].value == "€50M"
        assert players[0].wage == "€200K"

    def test_range_format(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>Pac</th></tr>"
            "<tr><td>Test</td><td>12-16</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        players = parse_html_export(p)
        assert players[0].attributes["Pace"] == 12

    def test_attr_out_of_range(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>Pac</th></tr>"
            "<tr><td>Test</td><td>25</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        players = parse_html_export(p)
        assert "Pace" not in players[0].attributes

    def test_attr_not_int(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>Pac</th></tr>"
            "<tr><td>Test</td><td>N/A</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        players = parse_html_export(p)
        assert "Pace" not in players[0].attributes

    def test_gk_attributes(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>Han</th><th>Ref</th></tr>"
            "<tr><td>GK Test</td><td>15</td><td>18</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        players = parse_html_export(p)
        assert players[0].gk_attributes["Handling"] == 15
        assert players[0].gk_attributes["Reflexes"] == 18

    def test_player_header_name(self, tmp_path: Path) -> None:
        html = "<table><tr><th>Player</th></tr><tr><td>Alt Name</td></tr></table>"
        p = self._write_html(tmp_path, html)
        players = parse_html_export(p)
        assert players[0].name == "Alt Name"

    def test_club_header_team(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>Team</th></tr>"
            "<tr><td>Test</td><td>MyClub</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        assert parse_html_export(p)[0].club == "MyClub"

    def test_ability_header(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>Ability</th>"
            "<th>Potential</th></tr>"
            "<tr><td>T</td><td>150</td><td>180</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        players = parse_html_export(p)
        assert players[0].current_ability == 150
        assert players[0].potential_ability == 180

    def test_nationality_header(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>Nationality</th></tr>"
            "<tr><td>P</td><td>Brazil</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        assert parse_html_export(p)[0].nationality == "Brazil"

    def test_pos_header(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>Pos</th></tr>"
            "<tr><td>P</td><td>GK</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        assert parse_html_export(p)[0].position == "GK"

    def test_val_header(self, tmp_path: Path) -> None:
        html = (
            "<table>"
            "<tr><th>Name</th><th>Val</th></tr>"
            "<tr><td>P</td><td>€10M</td></tr>"
            "</table>"
        )
        p = self._write_html(tmp_path, html)
        assert parse_html_export(p)[0].value == "€10M"


class TestMergePlayers:
    """merge_players tests."""

    def test_match_by_name(self) -> None:
        bp = Player(
            name="John Smith",
            date_of_birth="1995-06-29",
            source="binary",
        )
        hp = Player(
            name="John Smith",
            current_ability=170,
            potential_ability=185,
            club="Madrid",
            nationality="Spain",
            position="AMC",
            value="€50M",
            wage="€200K",
            attributes={"Pace": 18},
            gk_attributes={"Handling": 15},
            source="html",
        )
        result = merge_players([bp], [hp])
        assert len(result) == 1
        merged = result[0]
        assert merged.source == "merged"
        assert merged.date_of_birth == "1995-06-29"
        assert merged.current_ability == 170
        assert merged.potential_ability == 185
        assert merged.club == "Madrid"
        assert merged.nationality == "Spain"
        assert merged.position == "AMC"
        assert merged.value == "€50M"
        assert merged.wage == "€200K"
        assert merged.attributes["Pace"] == 18
        assert merged.gk_attributes["Handling"] == 15

    def test_html_only(self) -> None:
        hp = Player(name="HTML Only", source="html")
        result = merge_players([], [hp])
        assert len(result) == 1
        assert result[0].name == "HTML Only"

    def test_binary_only(self) -> None:
        bp = Player(name="Binary Only", source="binary")
        result = merge_players([bp], [])
        assert len(result) == 1
        assert result[0].name == "Binary Only"

    def test_no_overwrite_when_html_zero(self) -> None:
        bp = Player(
            name="Test",
            current_ability=150,
            potential_ability=180,
            club="OldClub",
            source="binary",
        )
        hp = Player(
            name="Test",
            current_ability=0,
            potential_ability=0,
            club="",
            source="html",
        )
        result = merge_players([bp], [hp])
        assert result[0].current_ability == 150
        assert result[0].potential_ability == 180
        assert result[0].club == "OldClub"

    def test_case_insensitive_match(self) -> None:
        bp = Player(name="JOHN SMITH", source="binary")
        hp = Player(
            name="john smith",
            attributes={"Pace": 15},
            source="html",
        )
        result = merge_players([bp], [hp])
        assert len(result) == 1
        assert result[0].attributes["Pace"] == 15

    def test_mixed(self) -> None:
        bp1 = Player(name="Matched", source="binary")
        bp2 = Player(name="Binary Only", source="binary")
        hp1 = Player(
            name="Matched",
            club="Club",
            source="html",
        )
        hp2 = Player(name="HTML Only", source="html")
        result = merge_players([bp1, bp2], [hp1, hp2])
        names = {p.name for p in result}
        assert names == {"Matched", "Binary Only", "HTML Only"}
