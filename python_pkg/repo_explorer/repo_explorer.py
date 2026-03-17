#!/usr/bin/env python3
"""Repo Explorer - browse and run any project in the monorepo via a GUI."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import font, ttk
from typing import TYPE_CHECKING, cast

from python_pkg.repo_explorer._discovery import (
    REPO_ROOT,
    _find_terminal,
    find_projects,
    get_description,
)
from python_pkg.repo_explorer._execution import ExecutionMixin

if TYPE_CHECKING:
    import subprocess

# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------


class RepoExplorer(ExecutionMixin, tk.Tk):
    """Main application window for browsing and running monorepo projects."""

    # Catppuccin Mocha palette
    _BG = "#1e1e2e"
    _SURFACE = "#313244"
    _TEXT = "#cdd6f4"
    _TEXT_DIM = "#6c7086"
    _ACCENT = "#89b4fa"
    _GREEN = "#a6e3a1"
    _RED = "#f38ba8"
    _TERMINAL_BG = "#11111b"
    _MAX_EXPAND = 60  # expand tree groups automatically when <= this many results
    _IDLE_FLUSH_TICKS = 2  # flush partial PTY buffer after this many 50 ms timeouts

    def __init__(self) -> None:
        """Initialise the window, build the UI and load all projects."""
        super().__init__()
        self.title("Repo Explorer")
        self.geometry("1200x750")
        self.configure(bg=self._BG)
        self._proc: subprocess.Popen[bytes] | None = None
        self._master_fd: int | None = None
        self._projects: list[dict[str, object]] = []
        self._terminal_args = _find_terminal()
        self._build_style()
        self._build_ui()
        self._load_projects()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_style(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")
        opts: dict[str, object]
        opts = {
            "background": self._BG,
            "foreground": self._TEXT,
            "fieldbackground": self._BG,
            "font": ("Monospace", 10),
            "rowheight": 24,
        }
        s.configure("Treeview", **opts)
        s.configure(
            "Treeview.Heading", background=self._SURFACE, foreground=self._ACCENT
        )
        s.map(
            "Treeview",
            background=[("selected", self._SURFACE)],
            foreground=[("selected", self._ACCENT)],
        )
        s.configure("TFrame", background=self._BG)
        s.configure("TLabel", background=self._BG, foreground=self._TEXT)
        s.configure(
            "TButton", background=self._SURFACE, foreground=self._TEXT, padding=4
        )
        s.map(
            "TButton",
            background=[("active", "#45475a"), ("disabled", self._BG)],
            foreground=[("disabled", self._TEXT_DIM)],
        )
        s.configure(
            "TEntry",
            fieldbackground=self._SURFACE,
            foreground=self._TEXT,
            insertcolor=self._TEXT,
        )
        s.configure("TPanedwindow", background=self._BG)
        s.configure("TSeparator", background=self._SURFACE)

    def _build_ui(self) -> None:
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        paned.add(self._build_left(paned), weight=1)
        paned.add(self._build_right(paned), weight=3)

    def _build_left(self, parent: ttk.PanedWindow) -> ttk.Frame:
        frame = ttk.Frame(parent)

        # Search bar
        sf = ttk.Frame(frame)
        sf.pack(fill=tk.X, padx=4, pady=(4, 2))
        ttk.Label(sf, text="Search:").pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_tree())
        ttk.Entry(sf, textvariable=self._search_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0)
        )

        # Project count label
        self._count_var = tk.StringVar(value="")
        ttk.Label(
            frame,
            textvariable=self._count_var,
            foreground=self._TEXT_DIM,
            font=("sans-serif", 8),
        ).pack(anchor=tk.W, padx=6)

        # Tree + scrollbar
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        scroll = ttk.Scrollbar(tree_frame, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda _: self._run_embedded())
        self._tree.bind("<Return>", lambda _: self._run_embedded())

        return frame

    def _build_right(self, parent: ttk.PanedWindow) -> ttk.Frame:
        frame = ttk.Frame(parent)

        # Description section
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.X, padx=6, pady=(4, 0))

        ttk.Label(
            info_frame,
            text="Project",
            font=("sans-serif", 11, "bold"),
            foreground=self._ACCENT,
        ).pack(anchor=tk.W)
        self._title_var = tk.StringVar(value="Select a project from the list")
        ttk.Label(
            info_frame,
            textvariable=self._title_var,
            font=("Monospace", 9),
            foreground=self._TEXT_DIM,
        ).pack(anchor=tk.W)

        self._desc_var = tk.StringVar(value="")
        ttk.Label(
            info_frame,
            textvariable=self._desc_var,
            wraplength=700,
            justify=tk.LEFT,
            foreground=self._GREEN,
        ).pack(anchor=tk.W, pady=(2, 0))

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=4)

        # Args + buttons row
        ctrl_frame = ttk.Frame(frame)
        ctrl_frame.pack(fill=tk.X, padx=6, pady=(0, 4))

        ttk.Label(ctrl_frame, text="Args:").pack(side=tk.LEFT)
        self._args_var = tk.StringVar()
        ttk.Entry(ctrl_frame, textvariable=self._args_var, width=30).pack(
            side=tk.LEFT, padx=(4, 12)
        )

        self._run_btn = ttk.Button(
            ctrl_frame,
            text="▶  Run here",
            command=self._run_embedded,
            state=tk.DISABLED,
        )
        self._run_btn.pack(side=tk.LEFT, padx=(0, 4))

        term_label = self._terminal_args[0] if self._terminal_args else "terminal"
        self._term_btn = ttk.Button(
            ctrl_frame,
            text=f"⧉  Open in {term_label}",
            command=self._run_in_terminal,
            state=tk.DISABLED,
        )
        self._term_btn.pack(side=tk.LEFT, padx=(0, 4))

        self._stop_btn = ttk.Button(
            ctrl_frame, text="■  Stop", command=self._stop, state=tk.DISABLED
        )
        self._stop_btn.pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(ctrl_frame, text="✕  Clear", command=self._clear).pack(side=tk.LEFT)

        # Status indicator
        self._status_var = tk.StringVar(value="")
        ttk.Label(
            ctrl_frame, textvariable=self._status_var, font=("sans-serif", 9)
        ).pack(side=tk.RIGHT)

        # stdin input row (for interactive embedded processes)
        stdin_frame = ttk.Frame(frame)
        stdin_frame.pack(fill=tk.X, padx=6, pady=(0, 4))
        ttk.Label(stdin_frame, text="Send input:").pack(side=tk.LEFT)
        self._stdin_var = tk.StringVar()
        stdin_entry = ttk.Entry(stdin_frame, textvariable=self._stdin_var)
        stdin_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        stdin_entry.bind("<Return>", self._send_stdin)
        ttk.Button(stdin_frame, text="↵ Send", command=self._send_stdin).pack(
            side=tk.LEFT
        )

        # Output terminal
        term_frame = ttk.Frame(frame)
        term_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        mono = font.Font(family="Monospace", size=9)
        self._output = tk.Text(
            term_frame,
            bg=self._TERMINAL_BG,
            fg=self._TEXT,
            font=mono,
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.FLAT,
            insertbackground=self._TEXT,
        )
        out_scroll = ttk.Scrollbar(term_frame, command=self._output.yview)
        self._output.configure(yscrollcommand=out_scroll.set)
        out_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._output.tag_config("stderr", foreground=self._RED)
        self._output.tag_config("info", foreground=self._ACCENT)
        self._output.tag_config("success", foreground=self._GREEN)
        self._output.tag_config("error", foreground=self._RED)

        return frame

    # ------------------------------------------------------------------
    # Project discovery / tree population
    # ------------------------------------------------------------------

    def _load_projects(self) -> None:
        self._projects = find_projects(REPO_ROOT)
        self._populate_tree(self._projects)

    def _populate_tree(self, projects: list[dict[str, object]]) -> None:
        self._tree.delete(*self._tree.get_children())

        groups: dict[str, list[dict[str, object]]] = {}
        for p in projects:
            rel = cast("Path", p["rel"])
            parts = rel.parts
            group = parts[0] if len(parts) > 1 else "(root)"
            groups.setdefault(group, []).append(p)

        icons = {
            "python_pkg": "🐍",
            "C": "⚙️",
            "CPP": "⚙️",
            "articles": "📰",
            "TS": "📜",
            "Bash": "🐚",
        }
        for group, items in sorted(groups.items()):
            icon = icons.get(group, "📁")
            gid = self._tree.insert("", tk.END, text=f"{icon} {group}", tags=("group",))
            for item in items:
                rel2 = cast("Path", item["rel"])
                label = cast(
                    "str",
                    "/".join(rel2.parts[1:]) if len(rel2.parts) > 1 else item["name"],
                )
                path_str = str(item["path"])
                self._tree.insert(gid, tk.END, text=f"  {label}", values=[path_str])

        self._tree.tag_configure("group", foreground=self._TEXT_DIM)
        # Expand all groups if result set is small enough
        if len(projects) <= self._MAX_EXPAND:
            for gid in self._tree.get_children():
                self._tree.item(gid, open=True)

        n = len(projects)
        self._count_var.set(f"{n} project{'s' if n != 1 else ''}")

    def _filter_tree(self) -> None:
        q = self._search_var.get().lower()
        if not q:
            self._populate_tree(self._projects)
            return
        filtered = [
            p
            for p in self._projects
            if q in str(p["rel"]).lower() or q in str(p["name"]).lower()
        ]
        self._populate_tree(filtered)

    # ------------------------------------------------------------------
    # Selection / info panel
    # ------------------------------------------------------------------

    def _selected_path(self) -> Path | None:
        sel = self._tree.selection()
        if not sel:
            return None
        vals = self._tree.item(sel[0], "values")
        if not vals:
            return None
        return Path(vals[0])

    def _on_select(self, _event: object) -> None:
        path = self._selected_path()
        if path is None:
            self._run_btn.configure(state=tk.DISABLED)
            self._term_btn.configure(state=tk.DISABLED)
            return
        self._title_var.set(str(path.relative_to(REPO_ROOT)))
        self._desc_var.set(get_description(path))
        self._run_btn.configure(state=tk.NORMAL)
        self._term_btn.configure(
            state=tk.NORMAL if self._terminal_args else tk.DISABLED
        )

    # ------------------------------------------------------------------
    # Execution methods provided by ExecutionMixin
    # ------------------------------------------------------------------


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    RepoExplorer().mainloop()
