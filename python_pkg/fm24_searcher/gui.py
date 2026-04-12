"""PyQt6-based GUI for FM24 Database Searcher.

Provides:
- Player search by name (debounced)
- Attribute filtering (min/max sliders)
- Weighted scouting score
- Player comparison
- Import from binary DB and HTML exports
- Threaded loading with progress overlay
"""

from __future__ import annotations

import datetime
from pathlib import Path
import struct
import sys
import threading
import time
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable

from PyQt6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSplitter,
    QStatusBar,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
import zstandard

from python_pkg.fm24_searcher.binary_parser import parse_people_db
from python_pkg.fm24_searcher.html_parser import (
    merge_players,
    parse_html_export,
)
from python_pkg.fm24_searcher.models import (
    ALL_VISIBLE_ATTRS,
    MENTAL_ATTRS,
    PHYSICAL_ATTRS,
    TECHNICAL_ATTRS,
    Player,
)

# Default path to FM24 people database.
DEFAULT_PEOPLE_DB = (
    Path.home()
    / ".local/share/Steam/steamapps/common"
    / "Football Manager 2024/data/database/db"
    / "2400/2400_fm/people_db.dat"
)

# Reference date for age calculation.
_TODAY = datetime.datetime.now(tz=datetime.UTC).date()

# Column layout.
_FIXED_COLS = ["Name", "Age", "CA", "PA"]
_COL_NAME = 0
_COL_AGE = 1
_COL_CA = 2
_COL_PA = 3

_FIXED_TOOLTIPS = {
    "CA": "Current Ability (1-200)",
    "PA": "Potential Ability (1-200)",
}

# Attribute color thresholds.
_ATTR_EXCELLENT = 18
_ATTR_GOOD = 15
_ATTR_AVERAGE = 12
_ATTR_BELOW = 8

_MIN_COMPARE_PLAYERS = 2
_MIN_ETA_PCT = 5
_COMPARE_HEADER_ROWS = 4

_IMPORT_GUIDE = """\
<h3>How to Import Player Attributes</h3>
<p>The FM24 binary database only contains player names and dates of birth.
To see <b>CA, PA</b>, and <b>attribute values</b>, you need to import an
HTML export from Football Manager.</p>
<h4>Steps:</h4>
<ol>
<li>Open <b>Football Manager 2024</b></li>
<li>Go to <b>Scouting &gt; Players</b> (or any player search screen)</li>
<li>Set up a <b>custom view</b> with columns: Name, Club, Nat, Pos, CA, PA,
    and all attributes (Cor, Cro, Dri, Fin, etc.)</li>
<li>Select all players with <b>Ctrl+A</b></li>
<li>Press <b>Ctrl+P</b> to print</li>
<li>Choose <b>"Web Page"</b> as the format and save the file</li>
<li>Use <b>File &gt; Import HTML Export</b> in this app to load it</li>
</ol>
<p><i>Tip: Export multiple pages (e.g. u21 players, each league)
and import them all — the app merges data automatically.</i></p>
"""


def _player_age(p: Player) -> int:
    """Calculate player age from DOB string."""
    if not p.date_of_birth:
        return 0
    try:
        dob = datetime.date.fromisoformat(p.date_of_birth)
    except ValueError:
        return 0
    else:
        age = _TODAY.year - dob.year
        if (_TODAY.month, _TODAY.day) < (dob.month, dob.day):
            age -= 1
        return age


def _attr_color(val: int) -> QColor:
    """Color-code an attribute value (1-20 scale)."""
    if val >= _ATTR_EXCELLENT:
        return QColor(0, 150, 50)
    if val >= _ATTR_GOOD:
        return QColor(80, 180, 80)
    if val >= _ATTR_AVERAGE:
        return QColor(180, 180, 50)
    if val >= _ATTR_BELOW:
        return QColor(220, 150, 50)
    return QColor(200, 60, 60)


def _build_tooltip(p: Player) -> str:
    """Build a multi-line tooltip for a player."""
    parts = [p.name]
    if p.club:
        parts.append(f"Club: {p.club}")
    if p.nationality:
        parts.append(f"Nationality: {p.nationality}")
    if p.position:
        parts.append(f"Position: {p.position}")
    if p.date_of_birth:
        parts.append(f"DOB: {p.date_of_birth}")
    if p.value:
        parts.append(f"Value: {p.value}")
    if p.wage:
        parts.append(f"Wage: {p.wage}")
    if p.personality:
        parts.append(f"Personality: {p.personality}")
    return "\n".join(parts)


class PlayerTableModel(QAbstractTableModel):
    """Virtual model for displaying players efficiently.

    Only renders visible rows, unlike QTableWidget which
    creates widget items for every cell in every row.
    """

    def __init__(
        self,
        parent: QObject | None = None,
    ) -> None:
        """Initialize the player table model."""
        super().__init__(parent)
        self._players: list[Player] = []
        self._ages: list[int] = []
        self._columns = list(_FIXED_COLS) + list(
            ALL_VISIBLE_ATTRS,
        )

    def set_players(self, players: list[Player]) -> None:
        """Replace all player data."""
        self.beginResetModel()
        self._players = players
        self._ages = [_player_age(p) for p in players]
        self.endResetModel()

    def rowCount(
        self,
        _parent: QModelIndex = QModelIndex(),
    ) -> int:
        """Return number of players."""
        return len(self._players)

    def columnCount(
        self,
        _parent: QModelIndex = QModelIndex(),
    ) -> int:
        """Return number of columns."""
        return len(self._columns)

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        """Return data for the given index and role."""
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if row >= len(self._players):
            return None
        p = self._players[row]
        handlers = {
            Qt.ItemDataRole.DisplayRole: lambda: self._display_data(p, row, col),
            Qt.ItemDataRole.BackgroundRole: lambda: self._bg_data(p, col),
            Qt.ItemDataRole.ToolTipRole: lambda: self._tooltip_data(p, col),
        }
        if role in handlers:
            return handlers[role]()
        if role == Qt.ItemDataRole.TextAlignmentRole and col >= 1:
            return Qt.AlignmentFlag.AlignCenter
        return None

    def _display_data(
        self,
        p: Player,
        row: int,
        col: int,
    ) -> object:
        """Return display text for a cell."""
        if col == _COL_NAME:
            return p.name
        if col == _COL_AGE:
            age = self._ages[row]
            return age or ""
        if col == _COL_CA:
            return p.current_ability or ""
        if col == _COL_PA:
            return p.potential_ability or ""
        fixed_count = len(_FIXED_COLS)
        if col >= fixed_count:
            attr = self._columns[col]
            val = p.get_attr(attr)
            return val if val > 0 else ""
        return None

    def _bg_data(
        self,
        p: Player,
        col: int,
    ) -> QBrush | None:
        """Return background brush for attribute cells."""
        fixed_count = len(_FIXED_COLS)
        if col >= fixed_count:
            attr = self._columns[col]
            val = p.get_attr(attr)
            if val > 0:
                return QBrush(_attr_color(val))
        return None

    def _tooltip_data(
        self,
        p: Player,
        col: int,
    ) -> str | None:
        """Return tooltip text for a cell."""
        if col == _COL_NAME:
            return _build_tooltip(p)
        if col == _COL_CA:
            return "Current Ability (1-200 scale)"
        if col == _COL_PA:
            return "Potential Ability (1-200 scale)"
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        """Return header label or tooltip."""
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self._columns[section]
            if role == Qt.ItemDataRole.ToolTipRole:
                col_name = self._columns[section]
                return _FIXED_TOOLTIPS.get(
                    col_name,
                    col_name,
                )
        return None

    def _sort_key(
        self,
        column: int,
    ) -> Callable[[int], object] | None:
        """Return a sort key function for the column."""
        fixed_count = len(_FIXED_COLS)
        if column == _COL_NAME:
            return lambda i: self._players[i].name.lower()
        if column == _COL_AGE:
            return lambda i: self._ages[i]
        if column == _COL_CA:
            return lambda i: self._players[i].current_ability
        if column == _COL_PA:
            return lambda i: self._players[i].potential_ability
        if column >= fixed_count:
            attr = self._columns[column]
            return lambda i: self._players[i].get_attr(attr)
        return None

    def sort(
        self,
        column: int,
        order: Qt.SortOrder = Qt.SortOrder.AscendingOrder,
    ) -> None:
        """Sort by column."""
        key_fn = self._sort_key(column)
        if key_fn is None:
            return
        self.beginResetModel()
        reverse = order == Qt.SortOrder.DescendingOrder
        indices = sorted(
            range(len(self._players)),
            key=key_fn,
            reverse=reverse,
        )
        self._players = [self._players[i] for i in indices]
        self._ages = [self._ages[i] for i in indices]
        self.endResetModel()

    def get_player(self, row: int) -> Player | None:
        """Get player at row index."""
        if 0 <= row < len(self._players):
            return self._players[row]
        return None


class LoadingOverlay(QWidget):
    """Full-window overlay shown during database loading."""

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the loading overlay."""
        super().__init__(parent)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            on=False,
        )
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel("LOADING DATABASE")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        self._title.setFont(title_font)
        self._title.setAlignment(
            Qt.AlignmentFlag.AlignCenter,
        )
        self._title.setStyleSheet("color: #333;")

        self._stage = QLabel("Initializing...")
        stage_font = QFont()
        stage_font.setPointSize(14)
        self._stage.setFont(stage_font)
        self._stage.setAlignment(
            Qt.AlignmentFlag.AlignCenter,
        )
        self._stage.setStyleSheet("color: #666;")

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setFixedWidth(500)
        self._progress.setFixedHeight(30)

        self._eta = QLabel("")
        self._eta.setAlignment(
            Qt.AlignmentFlag.AlignCenter,
        )
        self._eta.setStyleSheet("color: #888;")

        layout.addWidget(self._title)
        layout.addSpacing(20)
        layout.addWidget(self._stage)
        layout.addSpacing(10)
        layout.addWidget(
            self._progress,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        layout.addSpacing(5)
        layout.addWidget(self._eta)
        self.setLayout(layout)

    def update_progress(
        self,
        stage: str,
        percent: int,
        eta: str = "",
    ) -> None:
        """Update displayed loading status."""
        self._stage.setText(stage)
        self._progress.setValue(percent)
        self._eta.setText(eta)

    def paintEvent(self, event: object) -> None:
        """Draw semi-transparent background."""
        painter = QPainter(self)
        painter.fillRect(
            self.rect(),
            QColor(255, 255, 255, 220),
        )
        painter.end()
        super().paintEvent(event)


class FilterPanel(QGroupBox):
    """Attribute filter panel with min-value sliders."""

    def __init__(
        self,
        title: str,
        attrs: list[str],
        parent: QWidget | None = None,
    ) -> None:
        """Initialize filter sliders for given attrs."""
        super().__init__(title, parent)
        self.sliders: dict[str, QSlider] = {}
        self.labels: dict[str, QLabel] = {}

        layout = QGridLayout()
        layout.setSpacing(2)
        for i, attr in enumerate(attrs):
            lbl = QLabel(attr)
            lbl.setFixedWidth(110)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 20)
            slider.setValue(0)
            val_lbl = QLabel("0")
            val_lbl.setFixedWidth(20)
            slider.valueChanged.connect(
                lambda v, lb=val_lbl: lb.setText(str(v)),
            )
            layout.addWidget(lbl, i, 0)
            layout.addWidget(slider, i, 1)
            layout.addWidget(val_lbl, i, 2)
            self.sliders[attr] = slider
            self.labels[attr] = val_lbl
        self.setLayout(layout)

    def get_filters(self) -> dict[str, int]:
        """Return dict of attr_name -> min_value (skip 0)."""
        return {
            name: slider.value()
            for name, slider in self.sliders.items()
            if slider.value() > 0
        }

    def reset(self) -> None:
        """Reset all sliders to 0."""
        for slider in self.sliders.values():
            slider.setValue(0)


class WeightPanel(QGroupBox):
    """Weighted scouting formula panel."""

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize weight sliders for all attributes."""
        super().__init__("Scout Weights", parent)
        self.combos: dict[str, QSlider] = {}
        layout = QGridLayout()
        layout.setSpacing(2)

        for i, attr in enumerate(ALL_VISIBLE_ATTRS):
            lbl = QLabel(attr)
            lbl.setFixedWidth(110)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 10)
            slider.setValue(0)
            val_lbl = QLabel("0")
            val_lbl.setFixedWidth(20)
            slider.valueChanged.connect(
                lambda v, lb=val_lbl: lb.setText(str(v)),
            )
            layout.addWidget(lbl, i, 0)
            layout.addWidget(slider, i, 1)
            layout.addWidget(val_lbl, i, 2)
            self.combos[attr] = slider
        self.setLayout(layout)

    def get_weights(self) -> dict[str, float]:
        """Return non-zero weights."""
        return {
            name: float(slider.value())
            for name, slider in self.combos.items()
            if slider.value() > 0
        }


class CompareDialog(QDialog):
    """Side-by-side player comparison dialog."""

    def __init__(
        self,
        players: list[Player],
        parent: QWidget | None = None,
    ) -> None:
        """Initialize comparison table for given players."""
        super().__init__(parent)
        self.setWindowTitle("Compare Players")
        self.setMinimumSize(600, 700)

        layout = QVBoxLayout()
        table = QTableWidget()

        attrs = ALL_VISIBLE_ATTRS
        table.setRowCount(
            len(attrs) + _COMPARE_HEADER_ROWS,
        )
        table.setColumnCount(len(players) + 1)

        headers = ["Attribute"] + [p.name for p in players]
        table.setHorizontalHeaderLabels(headers)

        self._fill_header_rows(table, players)
        self._fill_attr_rows(table, players, attrs)

        table.resizeColumnsToContents()
        layout.addWidget(table)
        self.setLayout(layout)

    @staticmethod
    def _fill_header_rows(
        table: QTableWidget,
        players: list[Player],
    ) -> None:
        """Populate Name, Age, CA, PA rows."""
        # Name row.
        table.setItem(0, 0, QTableWidgetItem("Name"))
        for j, p in enumerate(players):
            item = QTableWidgetItem(p.name)
            font = QFont()
            font.setBold(True)
            item.setFont(font)
            table.setItem(0, j + 1, item)

        # Age row.
        table.setItem(1, 0, QTableWidgetItem("Age"))
        for j, p in enumerate(players):
            item = QTableWidgetItem(
                str(_player_age(p)),
            )
            table.setItem(1, j + 1, item)

        # CA row.
        table.setItem(
            _COL_CA,
            0,
            QTableWidgetItem("CA"),
        )
        for j, p in enumerate(players):
            item = QTableWidgetItem()
            item.setData(
                Qt.ItemDataRole.DisplayRole,
                p.current_ability,
            )
            table.setItem(_COL_CA, j + 1, item)

        # PA row.
        table.setItem(
            _COL_PA,
            0,
            QTableWidgetItem("PA"),
        )
        for j, p in enumerate(players):
            item = QTableWidgetItem()
            item.setData(
                Qt.ItemDataRole.DisplayRole,
                p.potential_ability,
            )
            table.setItem(_COL_PA, j + 1, item)

    @staticmethod
    def _fill_attr_rows(
        table: QTableWidget,
        players: list[Player],
        attrs: tuple[str, ...],
    ) -> None:
        """Populate attribute comparison rows."""
        for i, attr in enumerate(attrs):
            row = i + _COMPARE_HEADER_ROWS
            table.setItem(
                row,
                0,
                QTableWidgetItem(attr),
            )
            vals = [p.get_attr(attr) for p in players]
            max_val = max(vals) if vals else 0
            for j, p in enumerate(players):
                val = p.get_attr(attr)
                item = QTableWidgetItem()
                item.setData(
                    Qt.ItemDataRole.DisplayRole,
                    val,
                )
                if val > 0:
                    item.setBackground(_attr_color(val))
                    if val == max_val and len(players) > 1:
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                table.setItem(row, j + 1, item)


class MainWindow(QMainWindow):
    """Main application window."""

    progress_sig: ClassVar[type] = pyqtSignal(str, int)
    done_sig: ClassVar[type] = pyqtSignal(list)
    error_sig: ClassVar[type] = pyqtSignal(str)

    def __init__(self) -> None:
        """Initialize window, menu, UI, and auto-load."""
        super().__init__()
        self.setWindowTitle("FM24 Database Searcher")
        self.setMinimumSize(1200, 800)

        self.all_players: list[Player] = []
        self.filtered_players: list[Player] = []
        self._load_thread: threading.Thread | None = None
        self._load_start: float = 0.0

        self._create_menu()
        self._create_ui()
        self._create_status_bar()
        self._create_overlay()

        # Cross-thread signals.
        self.progress_sig.connect(self._on_load_progress)
        self.done_sig.connect(self._on_load_finished)
        self.error_sig.connect(self._on_load_error)

        # Debounce timer for search.
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._do_search)

        # Auto-load default DB after the window is shown.
        QTimer.singleShot(0, self._auto_load)

    def _create_menu(self) -> None:
        menubar = self.menuBar()
        if menubar is None:
            return

        file_menu = menubar.addMenu("&File")
        if file_menu is None:
            return

        load_db = QAction("Load &Binary DB...", self)
        load_db.triggered.connect(self._load_binary_db)
        file_menu.addAction(load_db)

        load_html = QAction(
            "Import &HTML Export...",
            self,
        )
        load_html.triggered.connect(self._load_html)
        file_menu.addAction(load_html)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = menubar.addMenu("&Help")
        if help_menu is None:
            return
        guide = QAction("How to &Import Attributes...", self)
        guide.triggered.connect(self._show_import_guide)
        help_menu.addAction(guide)

    def _create_ui(self) -> None:
        central = QWidget()
        main_layout = QVBoxLayout()

        # Info banner (shown when no attribute data loaded).
        self._info_banner = QLabel(
            "\u26a0 No attribute data loaded \u2014 "
            "use File > Import HTML Export to add CA, PA, "
            "and attributes. See Help > How to Import "
            "Attributes for instructions.",
        )
        self._info_banner.setWordWrap(True)
        self._info_banner.setStyleSheet(
            "background: #fff3cd; color: #856404; "
            "border: 1px solid #ffc107; border-radius: 4px; "
            "padding: 8px; font-size: 13px;",
        )
        self._info_banner.setVisible(True)
        main_layout.addWidget(self._info_banner)

        self._build_search_bar(main_layout)
        self._build_meta_filters(main_layout)
        self._build_splitter(main_layout)

        apply_btn = QPushButton("Apply Filters")
        apply_btn.clicked.connect(self._apply_filters)
        main_layout.addWidget(apply_btn)

        central.setLayout(main_layout)
        self.setCentralWidget(central)

    def _build_search_bar(
        self,
        parent_layout: QVBoxLayout,
    ) -> None:
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by name...",
        )
        self.search_input.textChanged.connect(
            self._on_search_changed,
        )
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._do_search)
        reset_btn = QPushButton("Reset Filters")
        reset_btn.clicked.connect(self._reset_filters)
        compare_btn = QPushButton("Compare Selected")
        compare_btn.clicked.connect(
            self._compare_selected,
        )

        search_layout.addWidget(QLabel("Name:"))
        search_layout.addWidget(
            self.search_input,
            stretch=1,
        )
        search_layout.addWidget(search_btn)
        search_layout.addWidget(reset_btn)
        search_layout.addWidget(compare_btn)
        parent_layout.addLayout(search_layout)

    def _build_meta_filters(
        self,
        parent_layout: QVBoxLayout,
    ) -> None:
        meta_layout = QHBoxLayout()
        self.pos_filter = QLineEdit()
        self.pos_filter.setPlaceholderText(
            "Position filter...",
        )
        self.pos_filter.setFixedWidth(120)
        self.nat_filter = QLineEdit()
        self.nat_filter.setPlaceholderText("Nationality...")
        self.nat_filter.setFixedWidth(120)
        self.club_filter = QLineEdit()
        self.club_filter.setPlaceholderText("Club...")
        self.club_filter.setFixedWidth(120)
        self.min_ca = QLineEdit()
        self.min_ca.setPlaceholderText("Min CA")
        self.min_ca.setFixedWidth(60)

        meta_layout.addWidget(QLabel("Pos:"))
        meta_layout.addWidget(self.pos_filter)
        meta_layout.addWidget(QLabel("Nat:"))
        meta_layout.addWidget(self.nat_filter)
        meta_layout.addWidget(QLabel("Club:"))
        meta_layout.addWidget(self.club_filter)
        meta_layout.addWidget(QLabel("Min CA:"))
        meta_layout.addWidget(self.min_ca)
        meta_layout.addStretch()
        parent_layout.addLayout(meta_layout)

    def _build_splitter(
        self,
        parent_layout: QVBoxLayout,
    ) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        filter_tabs = QTabWidget()
        self.tech_filter = FilterPanel(
            "Technical",
            TECHNICAL_ATTRS,
        )
        self.mental_filter = FilterPanel(
            "Mental",
            MENTAL_ATTRS,
        )
        self.phys_filter = FilterPanel(
            "Physical",
            PHYSICAL_ATTRS,
        )
        self.weight_panel = WeightPanel()

        filter_tabs.addTab(
            self.tech_filter,
            "Technical",
        )
        filter_tabs.addTab(self.mental_filter, "Mental")
        filter_tabs.addTab(self.phys_filter, "Physical")
        filter_tabs.addTab(
            self.weight_panel,
            "Scout Weights",
        )
        filter_tabs.setMaximumWidth(350)
        splitter.addWidget(filter_tabs)

        self._model = PlayerTableModel()
        self.player_table = QTableView()
        self.player_table.setModel(self._model)
        self.player_table.setAlternatingRowColors(True)
        self.player_table.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows,
        )
        self.player_table.setSortingEnabled(True)
        hdr = self.player_table.horizontalHeader()
        if hdr is not None:
            hdr.setStretchLastSection(False)
            hdr.setSectionResizeMode(
                QHeaderView.ResizeMode.Interactive,
            )
            hdr.resizeSection(_COL_NAME, 200)
            hdr.resizeSection(_COL_AGE, 45)
            hdr.resizeSection(_COL_CA, 45)
            hdr.resizeSection(_COL_PA, 45)
            fixed_count = len(_FIXED_COLS)
            for ci in range(
                fixed_count,
                len(_FIXED_COLS) + len(ALL_VISIBLE_ATTRS),
            ):
                hdr.resizeSection(ci, 40)
        vhdr = self.player_table.verticalHeader()
        if vhdr is not None:
            vhdr.setDefaultSectionSize(22)
            vhdr.setVisible(False)
        splitter.addWidget(self.player_table)

        splitter.setSizes([300, 900])
        parent_layout.addWidget(splitter, stretch=1)

    def _create_status_bar(self) -> None:
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Loading database...")

    def _create_overlay(self) -> None:
        """Create the loading overlay widget."""
        self._overlay = LoadingOverlay(self)
        self._overlay.hide()

    def resizeEvent(self, event: object) -> None:
        """Keep overlay sized to window."""
        super().resizeEvent(event)
        cw = self.centralWidget()
        if cw is not None:
            self._overlay.setGeometry(cw.geometry())

    def _show_overlay(self) -> None:
        cw = self.centralWidget()
        if cw is not None:
            self._overlay.setGeometry(cw.geometry())
        self._overlay.update_progress("Starting...", 0)
        self._overlay.show()
        self._overlay.raise_()

    def _hide_overlay(self) -> None:
        self._overlay.hide()

    def _auto_load(self) -> None:
        """Auto-load the default people_db.dat."""
        if DEFAULT_PEOPLE_DB.exists():
            self._load_binary_db_from_path(
                DEFAULT_PEOPLE_DB,
            )
        else:
            self.status.showMessage(
                "DB not found \u2014 use File > Load Binary DB",
            )

    def _load_binary_db(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select people_db.dat",
            str(Path.home()),
            "DAT files (*.dat);;All files (*)",
        )
        if not filepath:
            return
        self._load_binary_db_from_path(Path(filepath))

    def _load_binary_db_from_path(
        self,
        filepath: Path,
    ) -> None:
        """Parse and load a people_db.dat in background."""
        self._show_overlay()
        self._load_start = time.monotonic()

        win = self

        def _run() -> None:
            try:
                players = parse_people_db(
                    filepath,
                    progress_cb=win.progress_sig.emit,
                )
                win.done_sig.emit(players)
            except (
                OSError,
                ValueError,
                struct.error,
                zstandard.ZstdError,
            ) as e:
                win.error_sig.emit(str(e))

        self._load_thread = threading.Thread(
            target=_run,
            daemon=True,
        )
        self._load_thread.start()

    def _on_load_progress(
        self,
        stage: str,
        pct: int,
    ) -> None:
        elapsed = time.monotonic() - self._load_start
        if pct > _MIN_ETA_PCT:
            est_total = elapsed / (pct / 100)
            remaining = est_total - elapsed
            eta = f"~{remaining:.0f}s remaining"
        else:
            eta = ""
        self._overlay.update_progress(stage, pct, eta)

    def _on_load_finished(
        self,
        players: list[Player],
    ) -> None:
        if self.all_players:
            self.all_players = merge_players(
                players,
                self.all_players,
            )
        else:
            self.all_players = players
        self.filtered_players = self.all_players
        self._model.set_players(self.all_players)
        self._hide_overlay()
        self._update_data_status(len(players))

    def _on_load_error(self, msg: str) -> None:
        self._hide_overlay()
        QMessageBox.critical(
            self,
            "Error",
            f"Failed to parse: {msg}",
        )

    def _update_data_status(
        self,
        loaded_count: int,
    ) -> None:
        """Update status bar and info banner based on data."""
        has_ca = any(p.current_ability > 0 for p in self.all_players)
        has_attrs = any(bool(p.attributes) for p in self.all_players)
        self._info_banner.setVisible(
            not has_ca and not has_attrs,
        )
        total = len(self.all_players)
        parts = [f"Loaded {loaded_count:,} players"]
        parts.append(f"({total:,} total)")
        if has_ca:
            ca_count = sum(1 for p in self.all_players if p.current_ability > 0)
            parts.append(f"CA: {ca_count:,}")
        if has_attrs:
            attr_count = sum(1 for p in self.all_players if p.attributes)
            parts.append(f"Attrs: {attr_count:,}")
        if not has_ca and not has_attrs:
            parts.append(
                "\u2014 import HTML for attributes",
            )
        self.status.showMessage(" | ".join(parts))

    def _show_import_guide(self) -> None:
        """Show the HTML import instructions dialog."""
        QMessageBox.information(
            self,
            "How to Import Attributes",
            _IMPORT_GUIDE,
        )

    def _load_html(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select FM24 HTML export",
            str(Path.home()),
            "HTML files (*.html *.htm);;All files (*)",
        )
        if not filepath:
            return
        try:
            self.status.showMessage(
                "Parsing HTML export...",
            )
            QApplication.processEvents()
            players = parse_html_export(Path(filepath))
            if self.all_players:
                self.all_players = merge_players(
                    self.all_players,
                    players,
                )
            else:
                self.all_players = players
            self.filtered_players = self.all_players
            self._model.set_players(self.all_players)
            self._update_data_status(len(players))
        except (
            OSError,
            ValueError,
            UnicodeDecodeError,
        ) as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to parse HTML: {e}",
            )

    def _on_search_changed(self) -> None:
        """Restart the debounce timer on text change."""
        self._search_timer.start()

    def _do_search(self) -> None:
        """Execute name search (debounced)."""
        query = self.search_input.text().strip().lower()
        if not query:
            self.filtered_players = self.all_players
        else:
            self.filtered_players = [
                p for p in self.all_players if query in p.name.lower()
            ]
        self._model.set_players(self.filtered_players)
        self.status.showMessage(
            f"Showing {len(self.filtered_players):,} players",
        )

    def _apply_filters(self) -> None:
        min_attrs: dict[str, int] = {}
        min_attrs.update(self.tech_filter.get_filters())
        min_attrs.update(
            self.mental_filter.get_filters(),
        )
        min_attrs.update(self.phys_filter.get_filters())

        pos = self.pos_filter.text().strip()
        nat = self.nat_filter.text().strip()
        club = self.club_filter.text().strip()
        ca_text = self.min_ca.text().strip()
        min_ca = int(ca_text) if ca_text.isdigit() else None

        query = self.search_input.text().strip().lower()
        weights = self.weight_panel.get_weights()

        results: list[tuple[float, Player]] = []
        for p in self.all_players:
            if query and query not in p.name.lower():
                continue
            if not p.matches_filter(
                min_attrs=min_attrs or None,
                min_ca=min_ca,
                position_filter=pos or None,
                nationality_filter=nat or None,
                club_filter=club or None,
            ):
                continue
            score = p.weighted_score(weights) if weights else 0.0
            results.append((score, p))

        if weights:
            results.sort(
                key=lambda x: x[0],
                reverse=True,
            )
        else:
            results.sort(
                key=lambda x: x[1].current_ability,
                reverse=True,
            )

        self.filtered_players = [p for _, p in results]
        self._model.set_players(self.filtered_players)
        self.status.showMessage(
            f"Filtered: {len(self.filtered_players):,} players",
        )

    def _reset_filters(self) -> None:
        self.tech_filter.reset()
        self.mental_filter.reset()
        self.phys_filter.reset()
        self.search_input.clear()
        self.pos_filter.clear()
        self.nat_filter.clear()
        self.club_filter.clear()
        self.min_ca.clear()
        self.filtered_players = self.all_players
        self._model.set_players(self.all_players)
        self.status.showMessage("Filters reset")

    def _compare_selected(self) -> None:
        sel = self.player_table.selectionModel()
        if sel is None:
            return
        indexes = sel.selectedRows()
        if len(indexes) < _MIN_COMPARE_PLAYERS:
            QMessageBox.information(
                self,
                "Compare",
                "Select at least 2 rows to compare.",
            )
            return
        players = []
        for idx in sorted(
            indexes,
            key=lambda i: i.row(),
        ):
            p = self._model.get_player(idx.row())
            if p:
                players.append(p)
        if len(players) >= _MIN_COMPARE_PLAYERS:
            dlg = CompareDialog(players, self)
            dlg.exec()


def main() -> None:
    """Launch the FM24 Database Searcher GUI."""
    app = QApplication(sys.argv)
    app.setApplicationName("FM24 Database Searcher")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
