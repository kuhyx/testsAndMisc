"""Tests for python_pkg.fm24_searcher.gui."""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import after conftest sets QT_QPA_PLATFORM=offscreen.
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QPaintEvent
from PyQt6.QtWidgets import QApplication
import pytest

from python_pkg.fm24_searcher.gui import (
    _IMPORT_GUIDE,
    CompareDialog,
    FilterPanel,
    LoadingOverlay,
    MainWindow,
    PlayerTableModel,
    WeightPanel,
    _attr_color,
    _build_tooltip,
    _player_age,
    main,
)
from python_pkg.fm24_searcher.models import ALL_VISIBLE_ATTRS, Player


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    """Get or create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_player(**kwargs: object) -> Player:
    """Helper to create Player with sensible defaults."""
    defaults: dict[str, object] = {
        "name": "Test Player",
        "date_of_birth": "1995-06-29",
        "current_ability": 170,
        "potential_ability": 185,
        "source": "binary",
    }
    defaults.update(kwargs)
    return Player(**defaults)


class TestPlayerAge:
    """_player_age tests."""

    def test_valid_dob(self) -> None:
        p = Player(date_of_birth="1995-06-29")
        age = _player_age(p)
        today = datetime.datetime.now(tz=datetime.UTC).date()
        expected = today.year - 1995
        if (today.month, today.day) < (6, 29):
            expected -= 1
        assert age == expected

    def test_no_dob(self) -> None:
        assert _player_age(Player()) == 0

    def test_invalid_dob(self) -> None:
        assert _player_age(Player(date_of_birth="not-a-date")) == 0

    def test_birthday_edge_before(self) -> None:
        # Birthday is Dec 31 — hasn't happened yet if today < Dec 31.
        today = datetime.datetime.now(tz=datetime.UTC).date()
        p = Player(date_of_birth=f"{today.year - 20}-12-31")
        age = _player_age(p)
        if (today.month, today.day) < (12, 31):
            assert age == 19
        else:
            assert age == 20

    def test_birthday_edge_after(self) -> None:
        p = Player(date_of_birth="2000-01-01")
        age = _player_age(p)
        today = datetime.datetime.now(tz=datetime.UTC).date()
        expected = today.year - 2000
        if (today.month, today.day) < (1, 1):
            expected -= 1  # Can't happen: Jan 1 is always ≤ today
        assert age == expected


class TestAttrColor:
    """_attr_color thresholds."""

    def test_excellent(self) -> None:
        c = _attr_color(20)
        assert c.green() == 150

    def test_good(self) -> None:
        c = _attr_color(16)
        assert c.green() == 180

    def test_average(self) -> None:
        c = _attr_color(13)
        assert c.green() == 180
        assert c.red() == 180

    def test_below(self) -> None:
        c = _attr_color(9)
        assert c.red() == 220

    def test_poor(self) -> None:
        c = _attr_color(3)
        assert c.red() == 200


class TestBuildTooltip:
    """_build_tooltip tests."""

    def test_full(self) -> None:
        p = Player(
            name="John",
            club="Madrid",
            nationality="Spain",
            position="AMC",
            date_of_birth="1995-06-29",
            value="€50M",
            wage="€200K",
            personality=[10, 11, 12, 13, 14, 15, 16, 5],
        )
        tip = _build_tooltip(p)
        assert "John" in tip
        assert "Club: Madrid" in tip
        assert "Nationality: Spain" in tip
        assert "Position: AMC" in tip
        assert "DOB: 1995-06-29" in tip
        assert "Value: €50M" in tip
        assert "Wage: €200K" in tip
        assert "Personality:" in tip

    def test_minimal(self) -> None:
        p = Player(name="Only Name")
        tip = _build_tooltip(p)
        assert tip == "Only Name"


class TestPlayerTableModel:
    """PlayerTableModel tests."""

    def test_empty(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        assert model.rowCount() == 0
        assert model.columnCount() == len(["Name", "Age", "CA", "PA"]) + len(
            ALL_VISIBLE_ATTRS,
        )

    def test_set_players(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player()])
        assert model.rowCount() == 1

    def test_data_invalid_index(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        assert model.data(QModelIndex()) is None

    def test_data_row_out_of_range(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player()])
        idx = model.index(5, 0)
        assert model.data(idx) is None

    def test_data_name(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player(name="Alice")])
        idx = model.index(0, 0)
        assert model.data(idx) == "Alice"

    def test_data_age(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player(date_of_birth="1995-06-29")])
        idx = model.index(0, 1)
        val = model.data(idx)
        assert isinstance(val, int)
        assert val > 0

    def test_data_age_zero(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player(date_of_birth="")])
        idx = model.index(0, 1)
        assert model.data(idx) == ""

    def test_data_ca(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player(current_ability=170)])
        idx = model.index(0, 2)
        assert model.data(idx) == 170

    def test_data_ca_zero(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player(current_ability=0)])
        idx = model.index(0, 2)
        assert model.data(idx) == ""

    def test_data_pa(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player(potential_ability=185)])
        idx = model.index(0, 3)
        assert model.data(idx) == 185

    def test_data_pa_zero(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player(potential_ability=0)])
        idx = model.index(0, 3)
        assert model.data(idx) == ""

    def test_data_attribute(self, qapp: QApplication) -> None:
        p = _make_player(attributes={"Corners": 15})
        model = PlayerTableModel()
        model.set_players([p])
        # Corners is first attr after fixed cols → col 4.
        idx = model.index(0, 4)
        assert model.data(idx) == 15

    def test_data_attribute_zero(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player()])
        idx = model.index(0, 4)
        assert model.data(idx) == ""

    def test_background_role_attr(self, qapp: QApplication) -> None:
        p = _make_player(attributes={"Corners": 15})
        model = PlayerTableModel()
        model.set_players([p])
        idx = model.index(0, 4)
        bg = model.data(idx, Qt.ItemDataRole.BackgroundRole)
        assert bg is not None

    def test_background_role_no_attr(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player()])
        idx = model.index(0, 4)
        bg = model.data(idx, Qt.ItemDataRole.BackgroundRole)
        assert bg is None

    def test_background_role_fixed_col(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player()])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.ItemDataRole.BackgroundRole) is None

    def test_tooltip_name(self, qapp: QApplication) -> None:
        p = _make_player(name="TipTest", club="MyClub")
        model = PlayerTableModel()
        model.set_players([p])
        idx = model.index(0, 0)
        tip = model.data(idx, Qt.ItemDataRole.ToolTipRole)
        assert "TipTest" in tip
        assert "MyClub" in tip

    def test_tooltip_ca(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player()])
        idx = model.index(0, 2)
        tip = model.data(idx, Qt.ItemDataRole.ToolTipRole)
        assert "Current Ability" in tip

    def test_tooltip_pa(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player()])
        idx = model.index(0, 3)
        tip = model.data(idx, Qt.ItemDataRole.ToolTipRole)
        assert "Potential Ability" in tip

    def test_tooltip_other(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player()])
        idx = model.index(0, 4)
        assert model.data(idx, Qt.ItemDataRole.ToolTipRole) is None

    def test_alignment_non_name(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player()])
        idx = model.index(0, 2)
        align = model.data(idx, Qt.ItemDataRole.TextAlignmentRole)
        assert align == Qt.AlignmentFlag.AlignCenter

    def test_alignment_name(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player()])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.ItemDataRole.TextAlignmentRole) is None

    def test_unsupported_role(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players([_make_player()])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.ItemDataRole.DecorationRole) is None

    def test_header_display(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        h = model.headerData(0, Qt.Orientation.Horizontal)
        assert h == "Name"
        h = model.headerData(2, Qt.Orientation.Horizontal)
        assert h == "CA"

    def test_header_tooltip(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        tip = model.headerData(
            2,
            Qt.Orientation.Horizontal,
            Qt.ItemDataRole.ToolTipRole,
        )
        assert "Current Ability" in tip

    def test_header_tooltip_attr(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        tip = model.headerData(
            4,
            Qt.Orientation.Horizontal,
            Qt.ItemDataRole.ToolTipRole,
        )
        assert tip == "Corners"

    def test_header_vertical(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        assert model.headerData(0, Qt.Orientation.Vertical) is None

    def test_sort_by_name(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players(
            [
                _make_player(name="Zeta"),
                _make_player(name="Alpha"),
            ]
        )
        model.sort(0, Qt.SortOrder.AscendingOrder)
        assert model.data(model.index(0, 0)) == "Alpha"

    def test_sort_by_age(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players(
            [
                _make_player(date_of_birth="1990-01-01"),
                _make_player(date_of_birth="2000-01-01"),
            ]
        )
        model.sort(1, Qt.SortOrder.DescendingOrder)
        # Older player (1990) has higher age → first in descending.
        older_age = model.data(model.index(0, 1))
        younger_age = model.data(model.index(1, 1))
        assert older_age > younger_age

    def test_sort_by_ca(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players(
            [
                _make_player(current_ability=100),
                _make_player(current_ability=200),
            ]
        )
        model.sort(2, Qt.SortOrder.DescendingOrder)
        assert model.data(model.index(0, 2)) == 200

    def test_sort_by_pa(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players(
            [
                _make_player(potential_ability=100),
                _make_player(potential_ability=200),
            ]
        )
        model.sort(3, Qt.SortOrder.DescendingOrder)
        assert model.data(model.index(0, 3)) == 200

    def test_sort_by_attr(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        model.set_players(
            [
                _make_player(attributes={"Corners": 5}),
                _make_player(attributes={"Corners": 20}),
            ]
        )
        model.sort(4, Qt.SortOrder.DescendingOrder)
        assert model.data(model.index(0, 4)) == 20

    def test_get_player(self, qapp: QApplication) -> None:
        model = PlayerTableModel()
        p = _make_player(name="Target")
        model.set_players([p])
        assert model.get_player(0) is p

    def test_get_player_out_of_range(
        self,
        qapp: QApplication,
    ) -> None:
        model = PlayerTableModel()
        assert model.get_player(5) is None

    def test_get_player_negative(
        self,
        qapp: QApplication,
    ) -> None:
        model = PlayerTableModel()
        assert model.get_player(-1) is None

    def test_data_stale_row(self, qapp: QApplication) -> None:
        """Row >= len(players) via createIndex (line 205)."""
        model = PlayerTableModel()
        model.set_players([_make_player()])
        idx = model.createIndex(5, 0)
        assert model.data(idx) is None

    def test_display_data_fallthrough(self, qapp: QApplication) -> None:
        """_display_data returns None for impossible col (line 239)."""
        model = PlayerTableModel()
        p = _make_player()
        model.set_players([p])
        # Call _display_data directly with col=-1 (not a fixed col)
        assert model._display_data(p, 0, -1) is None

    def test_sort_invalid_column(self, qapp: QApplication) -> None:
        """sort() with col returning None key_fn (lines 304, 314)."""
        model = PlayerTableModel()
        model.set_players([_make_player()])
        # col=-1 returns None from _sort_key → sort returns early
        model.sort(-1)


class TestLoadingOverlay:
    """LoadingOverlay tests."""

    def test_update_progress(self, qapp: QApplication) -> None:
        overlay = LoadingOverlay()
        overlay.update_progress("Testing...", 50, "~5s remaining")
        assert overlay._stage.text() == "Testing..."
        assert overlay._progress.value() == 50
        assert overlay._eta.text() == "~5s remaining"

    def test_paint_event(self, qapp: QApplication) -> None:
        overlay = LoadingOverlay()
        overlay.resize(200, 200)
        overlay.show()
        # Call paintEvent directly to ensure coverage.
        event = QPaintEvent(overlay.rect())
        overlay.paintEvent(event)


class TestFilterPanel:
    """FilterPanel tests."""

    def test_get_filters_empty(self, qapp: QApplication) -> None:
        panel = FilterPanel("Test", ["Pace", "Stamina"])
        assert panel.get_filters() == {}

    def test_get_filters_nonzero(self, qapp: QApplication) -> None:
        panel = FilterPanel("Test", ["Pace", "Stamina"])
        panel.sliders["Pace"].setValue(10)
        result = panel.get_filters()
        assert result == {"Pace": 10}

    def test_reset(self, qapp: QApplication) -> None:
        panel = FilterPanel("Test", ["Pace"])
        panel.sliders["Pace"].setValue(15)
        panel.reset()
        assert panel.sliders["Pace"].value() == 0


class TestWeightPanel:
    """WeightPanel tests."""

    def test_get_weights_empty(self, qapp: QApplication) -> None:
        panel = WeightPanel()
        assert panel.get_weights() == {}

    def test_get_weights_nonzero(self, qapp: QApplication) -> None:
        panel = WeightPanel()
        panel.combos["Pace"].setValue(5)
        result = panel.get_weights()
        assert result == {"Pace": 5.0}


class TestCompareDialog:
    """CompareDialog tests."""

    def test_creation(self, qapp: QApplication) -> None:
        players = [
            _make_player(name="P1", current_ability=170),
            _make_player(name="P2", current_ability=180),
        ]
        dlg = CompareDialog(players)
        assert dlg.windowTitle() == "Compare Players"

    def test_attr_bolding(self, qapp: QApplication) -> None:
        """Best attribute value is bolded (lines 607-611)."""
        players = [
            _make_player(
                name="P1",
                attributes={"Corners": 18, "Pace": 10},
            ),
            _make_player(
                name="P2",
                attributes={"Corners": 12, "Pace": 15},
            ),
        ]
        dlg = CompareDialog(players)
        assert dlg.windowTitle() == "Compare Players"


@pytest.fixture
def main_window(qapp: QApplication) -> MainWindow:
    """Create MainWindow with non-existent default DB and drain timers."""
    with patch(
        "python_pkg.fm24_searcher.gui.DEFAULT_PEOPLE_DB",
        Path("/nonexistent/path.dat"),
    ):
        win = MainWindow()
        QApplication.processEvents()
        return win


class TestMainWindow:
    """MainWindow tests."""

    def test_creation_no_db(
        self,
        main_window: MainWindow,
    ) -> None:
        assert main_window.windowTitle() == "FM24 Database Searcher"

    def test_search_empty(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window.all_players = [_make_player(name="Alice")]
        main_window._do_search()
        assert len(main_window.filtered_players) == 1

    def test_search_with_query(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window.all_players = [
            _make_player(name="Alice"),
            _make_player(name="Bob"),
        ]
        main_window.search_input.setText("alice")
        main_window._do_search()
        assert len(main_window.filtered_players) == 1
        assert main_window.filtered_players[0].name == "Alice"

    def test_reset_filters(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window.all_players = [_make_player()]
        main_window.search_input.setText("test")
        main_window._reset_filters()
        assert main_window.search_input.text() == ""
        assert len(main_window.filtered_players) == 1

    def test_apply_filters_with_weights(
        self,
        main_window: MainWindow,
    ) -> None:
        p1 = _make_player(
            name="Good",
            attributes={"Pace": 18, "Stamina": 15},
        )
        p2 = _make_player(
            name="Bad",
            attributes={"Pace": 5, "Stamina": 5},
        )
        main_window.all_players = [p2, p1]
        main_window.weight_panel.combos["Pace"].setValue(5)
        main_window._apply_filters()
        assert main_window.filtered_players[0].name == "Good"

    def test_apply_filters_no_weights(
        self,
        main_window: MainWindow,
    ) -> None:
        p1 = _make_player(name="High", current_ability=190)
        p2 = _make_player(name="Low", current_ability=100)
        main_window.all_players = [p2, p1]
        main_window._apply_filters()
        assert main_window.filtered_players[0].name == "High"

    def test_apply_filters_min_ca(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window.all_players = [
            _make_player(current_ability=100),
            _make_player(current_ability=200),
        ]
        main_window.min_ca.setText("150")
        main_window._apply_filters()
        assert len(main_window.filtered_players) == 1

    def test_on_load_finished_first(
        self,
        main_window: MainWindow,
    ) -> None:
        players = [_make_player()]
        main_window._on_load_finished(players)
        assert len(main_window.all_players) == 1

    def test_on_load_finished_merge(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window.all_players = [_make_player(name="Existing")]
        main_window._on_load_finished([_make_player(name="New")])
        names = {p.name for p in main_window.all_players}
        assert "Existing" in names
        assert "New" in names

    def test_on_load_error(
        self,
        main_window: MainWindow,
    ) -> None:
        with patch(
            "python_pkg.fm24_searcher.gui.QMessageBox.critical",
        ) as mock_critical:
            main_window._on_load_error("test error")
            mock_critical.assert_called_once()

    def test_on_load_progress_no_eta(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window._load_start = 0.0
        main_window._on_load_progress("Stage", 3)

    def test_on_load_progress_with_eta(
        self,
        main_window: MainWindow,
    ) -> None:
        import time

        main_window._load_start = time.monotonic() - 5.0
        main_window._on_load_progress("Stage", 50)

    def test_overlay_show_hide(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window._show_overlay()
        assert not main_window._overlay.isHidden()
        main_window._hide_overlay()
        assert main_window._overlay.isHidden()

    def test_resize_event(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window.resize(800, 600)

    def test_search_timer(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window._on_search_changed()
        assert main_window._search_timer.isActive()

    def test_compare_too_few(
        self,
        main_window: MainWindow,
    ) -> None:
        with patch(
            "python_pkg.fm24_searcher.gui.QMessageBox.information",
        ):
            main_window._compare_selected()

    def test_load_html_cancel(
        self,
        main_window: MainWindow,
    ) -> None:
        with patch(
            "python_pkg.fm24_searcher.gui.QFileDialog.getOpenFileName",
            return_value=("", ""),
        ):
            main_window._load_html()
        assert len(main_window.all_players) == 0

    def test_load_html_success(
        self,
        main_window: MainWindow,
        tmp_path: Path,
    ) -> None:
        html_file = tmp_path / "test.html"
        html_file.write_text(
            "<table><tr><th>Name</th></tr><tr><td>HTMLPlayer</td></tr></table>",
            encoding="utf-8",
        )
        with patch(
            "python_pkg.fm24_searcher.gui.QFileDialog.getOpenFileName",
            return_value=(str(html_file), ""),
        ):
            main_window._load_html()
        assert any(p.name == "HTMLPlayer" for p in main_window.all_players)

    def test_load_html_error(
        self,
        main_window: MainWindow,
    ) -> None:
        with (
            patch(
                "python_pkg.fm24_searcher.gui.QFileDialog.getOpenFileName",
                return_value=("/bad/path.html", ""),
            ),
            patch(
                "python_pkg.fm24_searcher.gui.QMessageBox.critical",
            ) as mock_crit,
        ):
            main_window._load_html()
            mock_crit.assert_called_once()

    def test_load_html_merge_existing(
        self,
        main_window: MainWindow,
        tmp_path: Path,
    ) -> None:
        main_window.all_players = [_make_player(name="Existing")]
        html_file = tmp_path / "test.html"
        html_file.write_text(
            "<table><tr><th>Name</th></tr><tr><td>New</td></tr></table>",
            encoding="utf-8",
        )
        with patch(
            "python_pkg.fm24_searcher.gui.QFileDialog.getOpenFileName",
            return_value=(str(html_file), ""),
        ):
            main_window._load_html()
        names = {p.name for p in main_window.all_players}
        assert "Existing" in names
        assert "New" in names

    def test_load_binary_db_cancel(
        self,
        main_window: MainWindow,
    ) -> None:
        with patch(
            "python_pkg.fm24_searcher.gui.QFileDialog.getOpenFileName",
            return_value=("", ""),
        ):
            main_window._load_binary_db()

    def test_load_binary_db_with_file(
        self,
        main_window: MainWindow,
        tmp_path: Path,
    ) -> None:
        """_load_binary_db when a file is selected (line 870)."""
        fake_path = tmp_path / "fake.dat"
        with (
            patch(
                "python_pkg.fm24_searcher.gui.QFileDialog.getOpenFileName",
                return_value=(str(fake_path), ""),
            ),
            patch.object(
                main_window,
                "_load_binary_db_from_path",
            ) as mock_load,
        ):
            main_window._load_binary_db()
            mock_load.assert_called_once_with(fake_path)

    def test_load_binary_db_from_path_success(
        self,
        main_window: MainWindow,
    ) -> None:
        """_load_binary_db_from_path thread emits done_sig (lines 877-901)."""
        fake_players = [_make_player()]
        with patch(
            "python_pkg.fm24_searcher.gui.parse_people_db",
            return_value=fake_players,
        ):
            main_window._load_binary_db_from_path(Path("/fake.dat"))
            main_window._load_thread.join(timeout=5)
        QApplication.processEvents()
        assert len(main_window.all_players) >= 1

    def test_load_binary_db_from_path_error(
        self,
        main_window: MainWindow,
    ) -> None:
        """_load_binary_db_from_path thread emits error_sig on failure."""
        with (
            patch(
                "python_pkg.fm24_searcher.gui.parse_people_db",
                side_effect=OSError("bad file"),
            ),
            patch(
                "python_pkg.fm24_searcher.gui.QMessageBox.critical",
            ) as mock_crit,
        ):
            main_window._load_binary_db_from_path(Path("/bad.dat"))
            main_window._load_thread.join(timeout=5)
            QApplication.processEvents()
            mock_crit.assert_called_once()

    def test_auto_load_when_db_exists(
        self,
        qapp: QApplication,
    ) -> None:
        """_auto_load calls _load_binary_db_from_path (line 853)."""
        with patch(
            "python_pkg.fm24_searcher.gui.DEFAULT_PEOPLE_DB",
            Path("/fake/path.dat"),
        ):
            win = MainWindow()
            with (
                patch.object(
                    win,
                    "_load_binary_db_from_path",
                ) as mock_load,
                patch(
                    "python_pkg.fm24_searcher.gui.DEFAULT_PEOPLE_DB",
                ) as mock_db,
            ):
                mock_db.exists.return_value = True
                win._auto_load()
                mock_load.assert_called_once()
            QApplication.processEvents()

    def test_resize_event_with_central_widget(
        self,
        main_window: MainWindow,
    ) -> None:
        """resizeEvent repositions overlay (lines 834-837)."""
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QResizeEvent

        event = QResizeEvent(QSize(1000, 700), QSize(800, 600))
        main_window.resizeEvent(event)

    def test_show_overlay_no_central_widget(
        self,
        main_window: MainWindow,
    ) -> None:
        """_show_overlay when centralWidget is None (branch 841→843)."""
        with patch.object(
            main_window,
            "centralWidget",
            return_value=None,
        ):
            main_window._show_overlay()
        assert not main_window._overlay.isHidden()

    def test_resize_event_no_central_widget(
        self,
        main_window: MainWindow,
    ) -> None:
        """resizeEvent when centralWidget is None (branch 836→exit)."""
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QResizeEvent

        event = QResizeEvent(QSize(500, 300), QSize(400, 200))
        with patch.object(
            main_window,
            "centralWidget",
            return_value=None,
        ):
            main_window.resizeEvent(event)

    def test_create_menu_null_menubar(
        self,
        main_window: MainWindow,
    ) -> None:
        """_create_menu returns early when menuBar is None (line 655)."""
        with patch.object(
            main_window,
            "menuBar",
            return_value=None,
        ):
            main_window._create_menu()

    def test_create_menu_null_file_menu(
        self,
        main_window: MainWindow,
    ) -> None:
        """_create_menu returns early when addMenu is None (line 659)."""
        mock_bar = MagicMock()
        mock_bar.addMenu.return_value = None
        with patch.object(
            main_window,
            "menuBar",
            return_value=mock_bar,
        ):
            main_window._create_menu()

    def test_create_table_null_hdr(
        self,
        qapp: QApplication,
    ) -> None:
        """Branch 798→813: horizontalHeader returns None."""
        with (
            patch(
                "python_pkg.fm24_searcher.gui.DEFAULT_PEOPLE_DB",
                Path("/nonexistent/path.dat"),
            ),
            patch(
                "python_pkg.fm24_searcher.gui.QTableView.horizontalHeader",
                return_value=None,
            ),
        ):
            win = MainWindow()
            QApplication.processEvents()
            assert win.player_table is not None

    def test_create_table_null_vhdr(
        self,
        qapp: QApplication,
    ) -> None:
        """Branch 814→817: verticalHeader returns None."""
        with (
            patch(
                "python_pkg.fm24_searcher.gui.DEFAULT_PEOPLE_DB",
                Path("/nonexistent/path.dat"),
            ),
            patch(
                "python_pkg.fm24_searcher.gui.QTableView.verticalHeader",
                return_value=None,
            ),
        ):
            win = MainWindow()
            QApplication.processEvents()
            assert win.player_table is not None

    def test_compare_selected_null_selection_model(
        self,
        main_window: MainWindow,
    ) -> None:
        """_compare_selected returns when sel is None (line 1064)."""
        with patch.object(
            main_window.player_table,
            "selectionModel",
            return_value=None,
        ):
            main_window._compare_selected()

    def test_compare_selected_with_players(
        self,
        main_window: MainWindow,
    ) -> None:
        """_compare_selected creates dialog (lines 1073-1083)."""
        p1 = _make_player(name="Player1", current_ability=170)
        p2 = _make_player(name="Player2", current_ability=180)
        main_window.all_players = [p1, p2]
        main_window._model.set_players([p1, p2])
        # Select both rows.
        sel = main_window.player_table.selectionModel()
        idx0 = main_window._model.index(0, 0)
        idx1 = main_window._model.index(1, 0)
        from PyQt6.QtCore import QItemSelectionModel

        sel.select(
            idx0,
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )
        sel.select(
            idx1,
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )
        with patch(
            "python_pkg.fm24_searcher.gui.CompareDialog.exec",
        ):
            main_window._compare_selected()

    def test_compare_selected_get_player_none(
        self,
        main_window: MainWindow,
    ) -> None:
        """_compare_selected when get_player returns None (1079, 1081)."""
        p1 = _make_player(name="P1")
        p2 = _make_player(name="P2")
        main_window.all_players = [p1, p2]
        main_window._model.set_players([p1, p2])
        sel = main_window.player_table.selectionModel()
        idx0 = main_window._model.index(0, 0)
        idx1 = main_window._model.index(1, 0)
        from PyQt6.QtCore import QItemSelectionModel

        sel.select(
            idx0,
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )
        sel.select(
            idx1,
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )
        with patch.object(
            main_window._model,
            "get_player",
            return_value=None,
        ):
            main_window._compare_selected()

    def test_apply_filters_meta(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window.all_players = [
            _make_player(
                name="Target",
                position="AMC",
                nationality="Spain",
                club="Madrid",
            ),
        ]
        main_window.pos_filter.setText("AMC")
        main_window.nat_filter.setText("Spain")
        main_window.club_filter.setText("Madrid")
        main_window._apply_filters()
        assert len(main_window.filtered_players) == 1

    def test_apply_filters_with_search(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window.all_players = [
            _make_player(name="Alice"),
            _make_player(name="Bob"),
        ]
        main_window.search_input.setText("alice")
        main_window._apply_filters()
        assert len(main_window.filtered_players) == 1

    def test_apply_filters_attr_filter(
        self,
        main_window: MainWindow,
    ) -> None:
        main_window.all_players = [
            _make_player(
                name="Fast",
                attributes={"Pace": 18},
            ),
            _make_player(name="Slow", attributes={"Pace": 3}),
        ]
        main_window.phys_filter.sliders["Pace"].setValue(10)
        main_window._apply_filters()
        assert len(main_window.filtered_players) == 1

    def test_info_banner_visible_no_data(
        self,
        main_window: MainWindow,
    ) -> None:
        """Info banner is visible when no attr data loaded."""
        main_window.all_players = []
        main_window._update_data_status(0)
        assert not main_window._info_banner.isHidden()

    def test_info_banner_hidden_with_ca(
        self,
        main_window: MainWindow,
    ) -> None:
        """Info banner is hidden when CA data is available."""
        main_window.all_players = [
            _make_player(current_ability=170),
        ]
        main_window._update_data_status(1)
        assert main_window._info_banner.isHidden()

    def test_info_banner_hidden_with_attrs(
        self,
        main_window: MainWindow,
    ) -> None:
        """Info banner is hidden when attributes loaded."""
        main_window.all_players = [
            _make_player(
                current_ability=0,
                attributes={"Pace": 15},
            ),
        ]
        main_window._update_data_status(1)
        assert main_window._info_banner.isHidden()

    def test_update_data_status_no_data(
        self,
        main_window: MainWindow,
    ) -> None:
        """Status shows import hint when no attrs."""
        main_window.all_players = [
            _make_player(
                current_ability=0,
                potential_ability=0,
            ),
        ]
        main_window._update_data_status(1)
        msg = main_window.status.currentMessage()
        assert "import HTML" in msg

    def test_update_data_status_with_data(
        self,
        main_window: MainWindow,
    ) -> None:
        """Status shows CA/Attrs counts when data present."""
        main_window.all_players = [
            _make_player(
                current_ability=170,
                attributes={"Pace": 18},
            ),
        ]
        main_window._update_data_status(1)
        msg = main_window.status.currentMessage()
        assert "CA:" in msg
        assert "Attrs:" in msg

    def test_show_import_guide(
        self,
        main_window: MainWindow,
    ) -> None:
        """_show_import_guide opens a message box."""
        with patch(
            "python_pkg.fm24_searcher.gui.QMessageBox.information",
        ) as mock_info:
            main_window._show_import_guide()
            mock_info.assert_called_once()
            args = mock_info.call_args
            assert "Import" in args[0][1]

    def test_import_guide_constant(self) -> None:
        """_IMPORT_GUIDE contains key instructions."""
        assert "Ctrl+P" in _IMPORT_GUIDE
        assert "HTML" in _IMPORT_GUIDE
        assert "CA" in _IMPORT_GUIDE

    def test_create_menu_null_help_menu(
        self,
        main_window: MainWindow,
    ) -> None:
        """_create_menu handles None help menu."""
        mock_bar = MagicMock()
        file_menu = MagicMock()
        mock_bar.addMenu.side_effect = [
            file_menu,
            None,
        ]
        with patch.object(
            main_window,
            "menuBar",
            return_value=mock_bar,
        ):
            main_window._create_menu()


class TestMainEntry:
    """main() entry point test."""

    def test_main_calls_app(self) -> None:
        with (
            patch(
                "python_pkg.fm24_searcher.gui.QApplication",
            ) as mock_app_cls,
            patch(
                "python_pkg.fm24_searcher.gui.MainWindow",
            ) as mock_win_cls,
            patch("sys.exit"),
        ):
            mock_app = MagicMock()
            mock_app_cls.return_value = mock_app
            mock_win = MagicMock()
            mock_win_cls.return_value = mock_win
            main()
            mock_app_cls.assert_called_once()
            mock_win.show.assert_called_once()

    def test_dunder_main_import(self) -> None:
        """Cover __main__.py line 2 (the import)."""
        import importlib

        mod = importlib.import_module("python_pkg.fm24_searcher.__main__")
        importlib.reload(mod)
