"""GUI setup methods for the poker modifier application."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from poker_modifier_app.poker_modifier_app import PokerModifierApp


class PokerGuiMixin:
    """Mixin providing GUI setup methods for PokerModifierApp."""

    self: PokerModifierApp

    def setup_gui(self) -> None:
        """Create and configure the main GUI window."""
        self._setup_main_window()
        main_frame = self._create_main_frame()
        self._create_title(main_frame)
        self._create_settings_frame(main_frame)
        self._create_result_display(main_frame)
        self._create_buttons(main_frame)
        self._create_statistics_frame(main_frame)

    def _setup_main_window(self) -> None:
        """Initialize the main Tk window."""
        self.root = tk.Tk()
        self.root.title("🃏 Texas Hold'em Modifier")
        self.root.geometry("650x750")
        self.root.configure(bg="#0f4c3a")
        self.root.resizable(True, True)
        style = ttk.Style()
        style.theme_use("clam")

    def _create_main_frame(self) -> tk.Frame:
        """Create and return the main container frame."""
        main_frame = tk.Frame(self.root, bg="#0f4c3a", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        return main_frame

    def _create_title(self, parent: tk.Frame) -> None:
        """Create the title label."""
        title_label = tk.Label(
            parent,
            text="🃏 Texas Hold'em Modifier",
            font=("Arial", 24, "bold"),
            fg="#ffd700",
            bg="#0f4c3a",
        )
        title_label.pack(pady=(0, 20))

    def _create_settings_frame(self, parent: tk.Frame) -> None:
        """Create the settings frame.

        Includes probability, debug, and game length controls.
        """
        settings_frame = tk.LabelFrame(
            parent,
            text="Settings",
            font=("Arial", 12, "bold"),
            fg="#ffd700",
            bg="#1a6b4d",
            relief=tk.RIDGE,
            bd=2,
        )
        settings_frame.pack(fill=tk.X, pady=(0, 20), padx=10, ipady=10)

        self._create_probability_controls(settings_frame)
        self._create_debug_controls(settings_frame)
        self._create_length_controls(settings_frame)

    def _create_probability_controls(self, parent: tk.Widget) -> None:
        """Create the probability slider and label."""
        prob_frame = tk.Frame(parent, bg="#1a6b4d")
        prob_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            prob_frame,
            text="Modifier Probability:",
            font=("Arial", 11, "bold"),
            fg="white",
            bg="#1a6b4d",
        ).pack(side=tk.LEFT)

        self.prob_var = tk.IntVar(value=30)
        self.prob_scale = tk.Scale(
            prob_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.prob_var,
            command=self.update_prob_display,
            bg="#1a6b4d",
            fg="white",
            highlightbackground="#1a6b4d",
            troughcolor="#0f4c3a",
            activebackground="#ffd700",
        )
        self.prob_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))

        self.prob_label = tk.Label(
            prob_frame,
            text="30%",
            font=("Arial", 11, "bold"),
            fg="#ffd700",
            bg="#1a6b4d",
            width=5,
        )
        self.prob_label.pack(side=tk.RIGHT)

    def _create_debug_controls(self, parent: tk.Widget) -> None:
        """Create the debug mode checkbox and force endgame button."""
        debug_frame = tk.Frame(parent, bg="#1a6b4d")
        debug_frame.pack(fill=tk.X, padx=10, pady=5)

        self.debug_var = tk.BooleanVar(value=False)
        debug_check = tk.Checkbutton(
            debug_frame,
            text="Debug Mode",
            variable=self.debug_var,
            command=self.toggle_debug_mode,
            bg="#1a6b4d",
            fg="white",
            selectcolor="#0f4c3a",
            activebackground="#1a6b4d",
            activeforeground="#ffd700",
            font=("Arial", 10, "bold"),
        )
        debug_check.pack(side=tk.LEFT, padx=(0, 15))

        self.force_endgame_button = tk.Button(
            debug_frame,
            text="Force Endgame",
            command=self.toggle_force_endgame,
            bg="#ff6b6b",
            fg="white",
            font=("Arial", 9, "bold"),
            relief=tk.RAISED,
            bd=2,
        )
        # Initially hidden

    def _create_length_controls(self, parent: tk.Widget) -> None:
        """Create the game length slider and label."""
        length_frame = tk.Frame(parent, bg="#1a6b4d")
        length_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            length_frame,
            text="Total Game Rounds:",
            font=("Arial", 11, "bold"),
            fg="white",
            bg="#1a6b4d",
        ).pack(side=tk.LEFT)

        self.length_var = tk.IntVar(value=20)
        self.length_scale = tk.Scale(
            length_frame,
            from_=5,
            to=50,
            orient=tk.HORIZONTAL,
            variable=self.length_var,
            command=self.update_length_display,
            bg="#1a6b4d",
            fg="white",
            highlightbackground="#1a6b4d",
            troughcolor="#0f4c3a",
            activebackground="#ffd700",
        )
        self.length_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))

        self.length_label = tk.Label(
            length_frame,
            text="20",
            font=("Arial", 11, "bold"),
            fg="#ffd700",
            bg="#1a6b4d",
            width=5,
        )
        self.length_label.pack(side=tk.RIGHT)

    def _create_result_display(self, parent: tk.Frame) -> None:
        """Create the result display frame."""
        self.result_frame = tk.Frame(
            parent, bg="#2d2d2d", relief=tk.RIDGE, bd=3, height=150
        )
        self.result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20), padx=10)
        self.result_frame.pack_propagate(False)

        self.result_label = tk.Label(
            self.result_frame,
            text="Click 'Start Round' to begin!",
            font=("Arial", 14),
            fg="#cccccc",
            bg="#2d2d2d",
            wraplength=500,
            justify=tk.CENTER,
        )
        self.result_label.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

    def _create_buttons(self, parent: tk.Frame) -> None:
        """Create the start and reset buttons."""
        button_frame = tk.Frame(parent, bg="#0f4c3a")
        button_frame.pack(fill=tk.X, pady=(0, 20), padx=10)

        self.start_button = tk.Button(
            button_frame,
            text="Start Round",
            font=("Arial", 18, "bold"),
            bg="#ffd700",
            fg="#0f4c3a",
            activebackground="#ffed4e",
            activeforeground="#0f4c3a",
            relief=tk.RAISED,
            bd=3,
            command=self.start_round,
            cursor="hand2",
        )
        self.start_button.pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(0, 5)
        )

        self.reset_button = tk.Button(
            button_frame,
            text="Reset Game",
            font=("Arial", 14, "bold"),
            bg="#ff6b6b",
            fg="white",
            activebackground="#ff5252",
            activeforeground="white",
            relief=tk.RAISED,
            bd=3,
            command=self.reset_game,
            cursor="hand2",
        )
        self.reset_button.pack(side=tk.RIGHT, ipady=10, padx=(5, 0))

    def _create_statistics_frame(self, parent: tk.Frame) -> None:
        """Create the statistics display frame with rounds, modifiers, and phase."""
        stats_frame = tk.Frame(parent, bg="#0f4c3a")
        stats_frame.pack(fill=tk.X, padx=10)

        # Rounds played
        rounds_frame = tk.LabelFrame(
            stats_frame,
            text="Rounds Played",
            font=("Arial", 10, "bold"),
            fg="#cccccc",
            bg="#1a6b4d",
            relief=tk.RIDGE,
            bd=2,
        )
        rounds_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        self.rounds_label = tk.Label(
            rounds_frame,
            text="0",
            font=("Arial", 20, "bold"),
            fg="#ffd700",
            bg="#1a6b4d",
        )
        self.rounds_label.pack(pady=10)

        # Modifiers applied
        mods_frame = tk.LabelFrame(
            stats_frame,
            text="Modifiers Applied",
            font=("Arial", 10, "bold"),
            fg="#cccccc",
            bg="#1a6b4d",
            relief=tk.RIDGE,
            bd=2,
        )
        mods_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 3))

        self.mods_label = tk.Label(
            mods_frame, text="0", font=("Arial", 20, "bold"), fg="#ffd700", bg="#1a6b4d"
        )
        self.mods_label.pack(pady=10)

        # Game phase indicator
        phase_frame = tk.LabelFrame(
            stats_frame,
            text="Game Phase",
            font=("Arial", 10, "bold"),
            fg="#cccccc",
            bg="#1a6b4d",
            relief=tk.RIDGE,
            bd=2,
        )
        phase_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(3, 0))

        self.phase_label = tk.Label(
            phase_frame,
            text="Early",
            font=("Arial", 16, "bold"),
            fg="#4CAF50",
            bg="#1a6b4d",
        )
        self.phase_label.pack(pady=10)
