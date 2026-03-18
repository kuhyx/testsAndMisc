"""Texas Hold'em poker game modifier application."""

import logging
import secrets
import tkinter as tk

from python_pkg.poker_modifier_app._poker_gui import PokerGuiMixin
from python_pkg.poker_modifier_app._poker_modifiers import (
    ENDGAME_MODIFIERS,
    REGULAR_MODIFIERS,
)

_logger = logging.getLogger(__name__)

# Use cryptographically secure random number generator
_rng = secrets.SystemRandom()


class PokerModifierApp(PokerGuiMixin):
    """GUI application for poker game modifiers."""

    def __init__(self) -> None:
        """Initialize the poker modifier app with default settings."""
        self.modifiers = list(REGULAR_MODIFIERS)
        self.endgame_modifiers = list(ENDGAME_MODIFIERS)

        # Remove endgame modifiers from regular modifier list
        endgame_modifier_names = [mod["name"] for mod in self.endgame_modifiers]
        self.modifiers = [
            mod for mod in self.modifiers if mod["name"] not in endgame_modifier_names
        ]

        # Game state tracking
        self.rounds_played = 0
        self.modifiers_applied = 0
        self.total_game_rounds = 20  # Default game length
        self.endgame_threshold = 0.8  # Start endgame modifiers at 80% of total rounds
        self.debug_mode = False
        self.force_endgame = False

        self.setup_gui()

    def update_prob_display(self, value: str) -> None:
        """Update the probability percentage display."""
        self.prob_label.config(text=f"{value}%")

    def update_length_display(self, value: str) -> None:
        """Update the game length display."""
        self.length_label.config(text=str(value))
        self.total_game_rounds = int(value)

    def toggle_debug_mode(self) -> None:
        """Toggle debug mode and show/hide debug controls."""
        self.debug_mode = self.debug_var.get()
        if self.debug_mode:
            self.force_endgame_button.pack(side=tk.LEFT, padx=(0, 10))
            _logger.debug("Debug mode enabled")
        else:
            self.force_endgame_button.pack_forget()
            self.force_endgame = False
            _logger.debug("Debug mode disabled")

    def toggle_force_endgame(self) -> None:
        """Toggle forced endgame mode for testing."""
        self.force_endgame = not self.force_endgame
        if self.force_endgame:
            self.force_endgame_button.config(text="Stop Force Endgame", bg="#4CAF50")
            _logger.debug("Forcing endgame modifiers")
        else:
            self.force_endgame_button.config(text="Force Endgame", bg="#ff6b6b")
            _logger.debug("Normal modifier selection restored")

    def is_endgame(self) -> bool:
        """Determine if we're in endgame phase."""
        if self.debug_mode and self.force_endgame:
            return True

        endgame_round = int(self.total_game_rounds * self.endgame_threshold)
        return self.rounds_played >= endgame_round

    def start_round(self) -> None:
        """Start a new poker round and determine if modifier should be applied."""
        # Button animation effect
        self.start_button.config(relief=tk.SUNKEN)
        self.root.after(100, lambda: self.start_button.config(relief=tk.RAISED))

        # Update round counter
        self.rounds_played += 1
        self.rounds_label.config(text=str(self.rounds_played))

        # Update game phase indicator
        self.update_phase_indicator()

        # Get current probability
        modifier_chance = self.prob_var.get()

        # Determine if modifier should be applied
        random_value = _rng.random() * 100
        should_apply_modifier = random_value < modifier_chance

        if should_apply_modifier:
            self.apply_random_modifier()
        else:
            self.show_no_modifier()

    def update_phase_indicator(self) -> None:
        """Update the game phase indicator based on current round."""
        if self.is_endgame():
            self.phase_label.config(text="Endgame", fg="#ff6b6b")
        elif self.rounds_played >= self.total_game_rounds * 0.6:
            self.phase_label.config(text="Late", fg="#ffa500")
        elif self.rounds_played >= self.total_game_rounds * 0.3:
            self.phase_label.config(text="Mid", fg="#ffeb3b")
        else:
            self.phase_label.config(text="Early", fg="#4CAF50")

    def apply_random_modifier(self) -> None:
        """Apply a random modifier and update display."""
        # Update modifier counter
        self.modifiers_applied += 1
        self.mods_label.config(text=str(self.modifiers_applied))

        # Determine which modifier pool to use
        if self.is_endgame():
            modifier_pool = self.endgame_modifiers
            modifier_type = "🏁 ENDGAME"
            bg_color = "#4a2d2d"  # Darker red for endgame
        else:
            modifier_pool = self.modifiers
            modifier_type = "🎲"
            bg_color = "#2d4a2d"  # Green for normal

        # Select random modifier from appropriate pool
        selected_modifier = _rng.choice(modifier_pool).copy()

        # Special handling for Steel Cards - randomize the rank
        if selected_modifier["name"] == "Steel Cards":
            ranks = [
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
                "9",
                "10",
                "Jack",
                "Queen",
                "King",
                "Ace",
            ]
            steel_rank = _rng.choice(ranks)
            selected_modifier["description"] = selected_modifier["description"].format(
                steel_rank=steel_rank
            )

        # Update result frame styling for modifier
        self.result_frame.config(
            bg=bg_color, highlightbackground="#ffd700", highlightthickness=2
        )

        # Update display with modifier info
        modifier_text = (
            f"{modifier_type} {selected_modifier['name']}\n\n"
            f"{selected_modifier['description']}"
        )

        # Add endgame indicator if applicable
        if self.is_endgame():
            rounds_left = self.total_game_rounds - self.rounds_played
            if rounds_left > 0:
                modifier_text += f"\n\n⚠️ Endgame Phase - {rounds_left} rounds left"
            else:
                modifier_text += "\n\n⚠️ FINAL ROUND!"

        self.result_label.config(
            text=modifier_text, fg="#ffd700", bg=bg_color, font=("Arial", 14, "bold")
        )

    def show_no_modifier(self) -> None:
        """Show no modifier message."""
        # Update result frame styling for no modifier
        self.result_frame.config(
            bg="#2d2d2d", highlightbackground="#666666", highlightthickness=1
        )

        # Update display
        self.result_label.config(
            text="No modifier this round\n\nPlay normally",
            fg="#cccccc",
            bg="#2d2d2d",
            font=("Arial", 14),
        )

    def reset_game(self) -> None:
        """Reset the game to initial state."""
        self.rounds_played = 0
        self.modifiers_applied = 0
        self.force_endgame = False

        # Update displays
        self.rounds_label.config(text="0")
        self.mods_label.config(text="0")
        self.phase_label.config(text="Early", fg="#4CAF50")

        # Reset result frame
        self.result_frame.config(
            bg="#2d2d2d", highlightbackground="#666666", highlightthickness=1
        )
        self.result_label.config(
            text="Click 'Start Round' to begin!",
            fg="#cccccc",
            bg="#2d2d2d",
            font=("Arial", 14),
        )

        # Reset force endgame button if visible
        if self.debug_mode:
            self.force_endgame_button.config(text="Force Endgame", bg="#ff6b6b")

        _logger.info("Game reset to initial state")

    def add_modifier(self, name: str, description: str) -> None:
        """Add a new modifier to the list."""
        self.modifiers.append({"name": name, "description": description})

    def get_stats(self) -> dict[str, int | float | bool]:
        """Get current statistics."""
        modifier_rate = (
            0
            if self.rounds_played == 0
            else (self.modifiers_applied / self.rounds_played) * 100
        )
        rounds_remaining = max(0, self.total_game_rounds - self.rounds_played)

        return {
            "rounds_played": self.rounds_played,
            "modifiers_applied": self.modifiers_applied,
            "modifier_rate": round(modifier_rate, 1),
            "total_game_rounds": self.total_game_rounds,
            "rounds_remaining": rounds_remaining,
            "is_endgame": self.is_endgame(),
            "debug_mode": self.debug_mode,
            "force_endgame": self.force_endgame,
        }

    def run(self) -> None:
        """Start the application."""
        _logger.info("Texas Hold'em Modifier App started!")
        _logger.info(
            "Available methods: app.get_stats(), app.add_modifier(name, description)"
        )
        _logger.info(
            "Debug features: Toggle debug mode to access force endgame controls"
        )
        _logger.info("Default game length: %s rounds", self.total_game_rounds)
        endgame_pct = int(self.endgame_threshold * 100)
        endgame_rounds = int(self.total_game_rounds * self.endgame_threshold)
        _logger.info("Endgame threshold: %s%% (%s rounds)", endgame_pct, endgame_rounds)
        self.root.mainloop()


if __name__ == "__main__":
    app = PokerModifierApp()
    app.run()
