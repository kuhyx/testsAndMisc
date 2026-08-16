"""Tests for the consumable supply level maths and its display.

Split from test_display.py under the 250-line cap. The classification and bar
formatting live in _supply; the two functions that print the section stay in
display, where test_display_part2.py patches them.
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from python_pkg.brother_printer._supply import (
    _classify_percentage_level,
    _classify_supply_level,
    _collect_supply_items,
    _format_supply_bar,
    _parse_supply_value,
    _process_supply_item,
)
from python_pkg.brother_printer.data_classes import NetworkResult, SupplyReadings
from python_pkg.brother_printer.display import (
    _display_supply_levels,
    _display_supply_warnings,
)


class TestClassifyPercentageLevel:
    def test_low(self) -> None:
        pct, _, _, _, replace = _classify_percentage_level("Toner", 5)
        assert pct == 5
        assert replace is True

    def test_warn(self) -> None:
        _, _, _, warn, replace = _classify_percentage_level("Toner", 20)
        assert replace is False
        assert "order soon" in warn

    def test_ok(self) -> None:
        _, _, _, warn, replace = _classify_percentage_level("Toner", 80)
        assert replace is False
        assert warn == ""


class TestClassifySupplyLevel:
    def test_snmp_ok(self) -> None:
        _, text, _, _, replace = _classify_supply_level("Toner", 100, -3)
        assert text == "OK"
        assert replace is False

    def test_snmp_low(self) -> None:
        _, text, _, _, replace = _classify_supply_level("Toner", 100, -2)
        assert text == "LOW"
        assert replace is True

    def test_empty(self) -> None:
        _, text, _, _, replace = _classify_supply_level("Toner", 100, 0)
        assert text == "EMPTY"
        assert replace is True

    def test_normal_percentage(self) -> None:
        pct, _, _, _, replace = _classify_supply_level("Toner", 100, 80)
        assert pct == 80
        assert replace is False

    def test_no_max_val(self) -> None:
        pct, text, _, _, _ = _classify_supply_level("Toner", 0, 50)
        assert pct == -1
        assert text == ""

    def test_over_100_capped(self) -> None:
        pct, _, _, _, _ = _classify_supply_level("Toner", 50, 100)
        assert pct == 100


class TestFormatSupplyBar:
    def test_negative(self) -> None:
        assert _format_supply_bar(-1) == ""

    def test_zero(self) -> None:
        bar = _format_supply_bar(0)
        assert "░" in bar

    def test_full(self) -> None:
        bar = _format_supply_bar(100)
        assert "█" in bar


class TestProcessSupplyItem:
    def test_normal(self) -> None:
        item = _process_supply_item("Toner", 100, 80)
        assert item.status_text == "80%"

    def test_empty(self) -> None:
        item = _process_supply_item("Toner", 100, 0)
        assert item.needs_replacement is True


class TestDisplaySupplyWarnings:
    def test_replacement_needed(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_supply_warnings(
                needs_replacement=True,
                warnings=["Toner low"],
            )
            assert "ACTION NEEDED" in out.getvalue()

    def test_warnings_only(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_supply_warnings(
                needs_replacement=False,
                warnings=["Toner at 20%"],
            )
            assert "HEADS UP" in out.getvalue()

    def test_all_healthy(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_supply_warnings(
                needs_replacement=False,
                warnings=[],
            )
            assert "healthy" in out.getvalue()


class TestParseSupplyValue:
    def test_valid(self) -> None:
        assert _parse_supply_value(["10", "20"], 0) == 10

    def test_index_error(self) -> None:
        assert _parse_supply_value([], 0) == 0

    def test_value_error(self) -> None:
        assert _parse_supply_value(["abc"], 0) == 0


class TestCollectSupplyItems:
    def test_collect(self) -> None:
        result = NetworkResult(
            supplies=SupplyReadings(
                descriptions=["Toner", "Drum"],
                max_values=["100", "200"],
                levels=["80", "150"],
            ),
        )
        items, descs = _collect_supply_items(result)
        assert len(items) == 2
        assert descs == ["Toner", "Drum"]


class TestDisplaySupplyLevels:
    def test_with_items(self) -> None:
        result = NetworkResult(
            supplies=SupplyReadings(
                descriptions=["Toner"],
                max_values=["100"],
                levels=["80"],
            ),
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_supply_levels(result)
            assert "Toner" in out.getvalue()

    def test_needs_replacement_and_warning(self) -> None:
        result = NetworkResult(
            supplies=SupplyReadings(
                descriptions=["Toner", "Drum"],
                max_values=["100", "100"],
                levels=["0", "15"],
            ),
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_supply_levels(result)
            text = out.getvalue()
            assert "ACTION NEEDED" in text
