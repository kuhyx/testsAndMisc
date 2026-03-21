"""Tests for python_pkg.repo_explorer.repo_explorer."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import tkinter as tk
from typing import Any
from unittest.mock import MagicMock, patch

# ── Helper to create a RepoExplorer without a real display ───────────


def _make_explorer(**overrides: Any) -> Any:
    """Build a RepoExplorer instance without a real Tk display.

    Mocks tk.Tk.__init__ and all GUI construction so no X server is needed.
    """
    with (
        patch("tkinter.Tk.__init__", return_value=None),
        patch(
            "python_pkg.repo_explorer.repo_explorer._find_terminal",
            return_value=overrides.pop("terminal_args", ["kitty", "--"]),
        ),
        patch(
            "python_pkg.repo_explorer.repo_explorer.find_projects",
            return_value=overrides.pop("projects", []),
        ),
        patch.object(
            _get_cls(),
            "title",
        ),
        patch.object(
            _get_cls(),
            "geometry",
        ),
        patch.object(
            _get_cls(),
            "configure",
        ),
        patch.object(
            _get_cls(),
            "_build_style",
        ),
        patch.object(
            _get_cls(),
            "_build_ui",
        ),
        patch.object(
            _get_cls(),
            "_load_projects",
        ),
    ):
        from python_pkg.repo_explorer.repo_explorer import RepoExplorer

        app = RepoExplorer()

    # Supply mock widgets needed by later tests
    app._tree = MagicMock()
    app._count_var = MagicMock()
    app._title_var = MagicMock()
    app._desc_var = MagicMock()
    app._run_btn = MagicMock()
    app._term_btn = MagicMock()
    app._stop_btn = MagicMock()
    app._args_var = MagicMock()
    app._stdin_var = MagicMock()
    app._status_var = MagicMock()
    app._output = MagicMock()
    app._search_var = MagicMock()
    return app


def _get_cls() -> type:
    from python_pkg.repo_explorer.repo_explorer import RepoExplorer

    return RepoExplorer


# ── __init__ ─────────────────────────────────────────────────────────


class TestRepoExplorerInit:
    def test_initial_state(self) -> None:
        app = _make_explorer()
        assert app._proc is None
        assert app._master_fd is None

    def test_no_terminal(self) -> None:
        app = _make_explorer(terminal_args=[])
        assert app._terminal_args == []


# ── _build_style ─────────────────────────────────────────────────────


class TestBuildStyle:
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Style")
    def test_build_style(self, mock_style_cls: MagicMock) -> None:
        app = _make_explorer()
        mock_style = MagicMock()
        mock_style_cls.return_value = mock_style
        app._build_style()
        mock_style.theme_use.assert_called_once_with("clam")
        assert mock_style.configure.call_count >= 5


# ── _build_ui / _build_left / _build_right ────────────────────────────


class TestBuildUI:
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Scrollbar")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Treeview")
    @patch("python_pkg.repo_explorer.repo_explorer.font.Font")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Button")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Entry")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Separator")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Label")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Frame")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.PanedWindow")
    @patch("python_pkg.repo_explorer.repo_explorer.tk.Text")
    @patch("python_pkg.repo_explorer.repo_explorer.tk.StringVar")
    def test_build_ui_with_terminal(
        self,
        mock_stringvar: MagicMock,
        mock_text: MagicMock,
        mock_paned: MagicMock,
        mock_frame: MagicMock,
        mock_label: MagicMock,
        mock_sep: MagicMock,
        mock_entry: MagicMock,
        mock_button: MagicMock,
        mock_font: MagicMock,
        mock_treeview: MagicMock,
        mock_scrollbar: MagicMock,
    ) -> None:
        app = _make_explorer()
        mock_sv = MagicMock()
        mock_stringvar.return_value = mock_sv
        paned = MagicMock()
        mock_paned.return_value = paned

        tree = MagicMock()
        mock_treeview.return_value = tree
        text = MagicMock()
        mock_text.return_value = text

        app.pack = MagicMock()
        app._build_ui()

    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Scrollbar")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Treeview")
    @patch("python_pkg.repo_explorer.repo_explorer.font.Font")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Button")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Entry")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Separator")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Label")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.Frame")
    @patch("python_pkg.repo_explorer.repo_explorer.ttk.PanedWindow")
    @patch("python_pkg.repo_explorer.repo_explorer.tk.Text")
    @patch("python_pkg.repo_explorer.repo_explorer.tk.StringVar")
    def test_build_ui_no_terminal(
        self,
        mock_stringvar: MagicMock,
        mock_text: MagicMock,
        mock_paned: MagicMock,
        mock_frame: MagicMock,
        mock_label: MagicMock,
        mock_sep: MagicMock,
        mock_entry: MagicMock,
        mock_button: MagicMock,
        mock_font: MagicMock,
        mock_treeview: MagicMock,
        mock_scrollbar: MagicMock,
    ) -> None:
        app = _make_explorer(terminal_args=[])
        mock_sv = MagicMock()
        mock_stringvar.return_value = mock_sv
        paned = MagicMock()
        mock_paned.return_value = paned

        tree = MagicMock()
        mock_treeview.return_value = tree
        text = MagicMock()
        mock_text.return_value = text

        app.pack = MagicMock()
        app._build_ui()


# ── _load_projects ───────────────────────────────────────────────────


class TestLoadProjects:
    @patch("python_pkg.repo_explorer.repo_explorer.find_projects")
    def test_load_projects(self, mock_find: MagicMock) -> None:
        app = _make_explorer()
        mock_find.return_value = [
            {"path": Path("/a"), "rel": PurePosixPath("a"), "name": "a"}
        ]
        object.__setattr__(app, "_populate_tree", MagicMock())
        app._load_projects()
        assert len(app._projects) == 1
        app._populate_tree.assert_called_once()


# ── _populate_tree ───────────────────────────────────────────────────


class TestPopulateTree:
    def test_groups_and_icons(self) -> None:
        app = _make_explorer()
        app._tree.insert.return_value = "group_id"
        projects = [
            {
                "path": Path("/r/python_pkg/proj1"),
                "rel": PurePosixPath("python_pkg/proj1"),
                "name": "proj1",
            },
            {
                "path": Path("/r/C/proj2"),
                "rel": PurePosixPath("C/proj2"),
                "name": "proj2",
            },
            {
                "path": Path("/r/unknown/proj3"),
                "rel": PurePosixPath("unknown/proj3"),
                "name": "proj3",
            },
        ]
        app._populate_tree(projects)
        app._tree.delete.assert_called_once()
        assert app._count_var.set.call_count == 1

    def test_root_level_project(self) -> None:
        app = _make_explorer()
        app._tree.insert.return_value = "group_id"
        projects = [
            {
                "path": Path("/r/single"),
                "rel": PurePosixPath("single"),
                "name": "single",
            },
        ]
        app._populate_tree(projects)
        # group should be "(root)" for single-part rel
        call_args = app._tree.insert.call_args_list
        group_text = call_args[0][1]["text"]
        assert "(root)" in group_text

    def test_expand_when_small(self) -> None:
        app = _make_explorer()
        app._tree.insert.return_value = "gid"
        app._tree.get_children.return_value = ["gid"]
        projects = [
            {"path": Path("/r/x/y"), "rel": PurePosixPath("x/y"), "name": "y"},
        ]
        app._populate_tree(projects)
        app._tree.item.assert_called()

    def test_no_expand_when_large(self) -> None:
        app = _make_explorer()
        app._tree.insert.return_value = "gid"
        many = [
            {
                "path": Path(f"/r/g/p{i}"),
                "rel": PurePosixPath(f"g/p{i}"),
                "name": f"p{i}",
            }
            for i in range(70)
        ]
        app._populate_tree(many)
        app._tree.item.assert_not_called()

    def test_singular_count(self) -> None:
        app = _make_explorer()
        app._tree.insert.return_value = "gid"
        projects = [
            {"path": Path("/r/g/p"), "rel": PurePosixPath("g/p"), "name": "p"},
        ]
        app._populate_tree(projects)
        app._count_var.set.assert_called_with("1 project")

    def test_plural_count(self) -> None:
        app = _make_explorer()
        app._tree.insert.return_value = "gid"
        projects = [
            {
                "path": Path(f"/r/g/p{i}"),
                "rel": PurePosixPath(f"g/p{i}"),
                "name": f"p{i}",
            }
            for i in range(3)
        ]
        app._populate_tree(projects)
        app._count_var.set.assert_called_with("3 projects")

    def test_all_icon_groups(self) -> None:
        """Cover all known icon group names."""
        app = _make_explorer()
        app._tree.insert.return_value = "gid"
        groups = ["python_pkg", "C", "CPP", "articles", "TS", "Bash"]
        projects = [
            {
                "path": Path(f"/r/{g}/proj"),
                "rel": PurePosixPath(f"{g}/proj"),
                "name": "proj",
            }
            for g in groups
        ]
        app._populate_tree(projects)

    def test_deep_rel_path_label(self) -> None:
        """Rel with >1 parts should join parts[1:]."""
        app = _make_explorer()
        app._tree.insert.return_value = "gid"
        projects = [
            {"path": Path("/r/a/b/c"), "rel": PurePosixPath("a/b/c"), "name": "c"},
        ]
        app._populate_tree(projects)
        # The leaf insert should have label "b/c"
        leaf_call = app._tree.insert.call_args_list[-1]
        assert "b/c" in leaf_call[1]["text"]


# ── _filter_tree ─────────────────────────────────────────────────────


class TestFilterTree:
    def test_empty_query_repopulates(self) -> None:
        app = _make_explorer()
        app._search_var.get.return_value = ""
        object.__setattr__(app, "_populate_tree", MagicMock())
        app._filter_tree()
        app._populate_tree.assert_called_once_with(app._projects)

    def test_filter_by_rel(self) -> None:
        app = _make_explorer()
        app._projects = [
            {"path": Path("/r/a"), "rel": PurePosixPath("alpha"), "name": "a"},
            {"path": Path("/r/b"), "rel": PurePosixPath("beta"), "name": "b"},
        ]
        app._search_var.get.return_value = "alph"
        object.__setattr__(app, "_populate_tree", MagicMock())
        app._filter_tree()
        filtered = app._populate_tree.call_args[0][0]
        assert len(filtered) == 1
        assert filtered[0]["name"] == "a"

    def test_filter_by_name(self) -> None:
        app = _make_explorer()
        app._projects = [
            {"path": Path("/r/x"), "rel": PurePosixPath("x"), "name": "xray"},
            {"path": Path("/r/y"), "rel": PurePosixPath("y"), "name": "yankee"},
        ]
        app._search_var.get.return_value = "yankee"
        object.__setattr__(app, "_populate_tree", MagicMock())
        app._filter_tree()
        filtered = app._populate_tree.call_args[0][0]
        assert len(filtered) == 1

    def test_filter_no_match(self) -> None:
        app = _make_explorer()
        app._projects = [
            {"path": Path("/r/x"), "rel": PurePosixPath("x"), "name": "x"},
        ]
        app._search_var.get.return_value = "zzz"
        object.__setattr__(app, "_populate_tree", MagicMock())
        app._filter_tree()
        filtered = app._populate_tree.call_args[0][0]
        assert filtered == []


# ── _selected_path ───────────────────────────────────────────────────


class TestSelectedPath:
    def test_no_selection(self) -> None:
        app = _make_explorer()
        app._tree.selection.return_value = ()
        assert app._selected_path() is None

    def test_no_values(self) -> None:
        app = _make_explorer()
        app._tree.selection.return_value = ("item1",)
        app._tree.item.return_value = ()
        assert app._selected_path() is None

    def test_with_values(self) -> None:
        app = _make_explorer()
        app._tree.selection.return_value = ("item1",)
        app._tree.item.return_value = ("/some/path",)
        result = app._selected_path()
        assert result == Path("/some/path")


# ── _on_select ───────────────────────────────────────────────────────


class TestOnSelect:
    @patch("python_pkg.repo_explorer.repo_explorer.get_description")
    def test_path_none_disables_buttons(self, mock_desc: MagicMock) -> None:
        app = _make_explorer()
        app._tree.selection.return_value = ()
        app._on_select(MagicMock())
        app._run_btn.configure.assert_called_with(state=tk.DISABLED)
        app._term_btn.configure.assert_called_with(state=tk.DISABLED)

    @patch("python_pkg.repo_explorer.repo_explorer.get_description")
    @patch("python_pkg.repo_explorer.repo_explorer.REPO_ROOT", Path("/root"))
    def test_path_selected_with_terminal(self, mock_desc: MagicMock) -> None:
        app = _make_explorer()
        app._tree.selection.return_value = ("item1",)
        app._tree.item.return_value = ("/root/sub/proj",)
        mock_desc.return_value = "A project"
        app._on_select(MagicMock())
        app._run_btn.configure.assert_called_with(state=tk.NORMAL)
        app._term_btn.configure.assert_called_with(state=tk.NORMAL)

    @patch("python_pkg.repo_explorer.repo_explorer.get_description")
    @patch("python_pkg.repo_explorer.repo_explorer.REPO_ROOT", Path("/root"))
    def test_path_selected_no_terminal(self, mock_desc: MagicMock) -> None:
        app = _make_explorer(terminal_args=[])
        app._tree.selection.return_value = ("item1",)
        app._tree.item.return_value = ("/root/sub/proj",)
        mock_desc.return_value = "A project"
        app._on_select(MagicMock())
        app._term_btn.configure.assert_called_with(state=tk.DISABLED)


# ── main guard ───────────────────────────────────────────────────────


class TestMainGuard:
    def test_main_block_exists(self) -> None:
        """Verify the main guard exists (excluded from coverage)."""
        import inspect

        import python_pkg.repo_explorer.repo_explorer as mod

        source = inspect.getsource(mod)
        assert 'if __name__ == "__main__":' in source
