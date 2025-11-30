"""Texas Hold'em poker game modifier application."""

import logging
import random
import tkinter as tk
from tkinter import ttk

logging.basicConfig(level=logging.INFO)


class PokerModifierApp:
    """GUI application for poker game modifiers."""

    def __init__(self) -> None:
        """Initialize the poker modifier app with default settings."""
        self.modifiers = [
            # Hand Bonus Modifiers (Balatro-inspired)
            {
                "name": "Pair Bonus",
                "description": (
                    "Any pocket pair: everyone else pays you 1 chip, "
                    "even if you lose the hand."
                ),
            },
            {
                "name": "Flush Fever",
                "description": (
                    "Make a flush: collect 1 chip from each other player "
                    "(separate from main pot)."
                ),
            },
            {
                "name": "Straight Shot",
                "description": (
                    "Complete a straight: choose one player "
                    "to pay you half the current pot size."
                ),
            },
            {
                "name": "Full House Party",
                "description": (
                    "Make full house: everyone else pays 2 chips " "+ takes 2 drinks."
                ),
            },
            {
                "name": "High Card Hero",
                "description": (
                    "Win with just high card: collect your normal winnings "
                    "+ 1 chip from each player."
                ),
            },
            # Card Enhancement Modifiers
            {
                "name": "Face Card Power",
                "description": "All face cards (J, Q, K) count as Aces for this hand.",
            },
            {
                "name": "Red Suit Boost",
                "description": (
                    "Hearts and Diamonds are worth +1 rank "
                    "(Jack becomes Queen, etc.)"
                ),
            },
            {
                "name": "Black Magic",
                "description": (
                    "Spades and Clubs can be used as any suit " "for straights/flushes."
                ),
            },
            {
                "name": "Lucky Sevens",
                "description": "All 7s become wild cards that can be any rank.",
            },
            {
                "name": "Steel Cards",
                "description": (
                    "Random rank chosen: {steel_rank}. "
                    "All {steel_rank}s beat everything this hand!"
                ),
            },
            # Ante-Based Effects (Clear Money Source)
            {
                "name": "Bonus Pool",
                "description": (
                    "Everyone puts 2 chips in bonus pool. "
                    "First person to make any pair wins it all."
                ),
            },
            # Deck Manipulation (Balatro-style)
            {
                "name": "Deck Shuffle",
                "description": (
                    "After dealing hole cards, shuffle deck "
                    "and redeal all community cards."
                ),
            },
            {
                "name": "Extra Draw",
                "description": (
                    "Deal each player a 3rd hole card. " "Discard one before the flop."
                ),
            },
            {
                "name": "Phantom Cards",
                "description": (
                    "Deal 6 community cards, " "but randomly remove 1 before showdown."
                ),
            },
            # Special Betting Rules (Realistic Economics)
            {
                "name": "Escalation",
                "description": (
                    "Each raise must be at least 2x the previous raise "
                    "(not just matching)."
                ),
            },
            # Position and Action Modifiers
            {
                "name": "Button Bonus",
                "description": "Dealer button acts last in ALL rounds",
            },
            {
                "name": "Call Penalty",
                "description": (
                    "Anyone who only calls (never raises) "
                    "pays 1 chip penalty to pot."
                ),
            },
            # Information Warfare
            {
                "name": "Poker Face",
                "description": (
                    "No talking, no expressions allowed. "
                    "Pure silent poker this hand."
                ),
            },
            {
                "name": "Truth or Consequences",
                "description": (
                    "If asked 'good hand or bad hand?' "
                    "you must answer truthfully or pay penalty."
                ),
            },
            {
                "name": "Open Book",
                "description": "Everyone plays with one hole card face-up.",
            },
            # Drinking Game Integration
            {
                "name": "Liquid Courage",
                "description": (
                    "Take a drink before betting " "to get chip bonus to all your bets."
                ),
            },
            {
                "name": "Last Call",
                "description": (
                    "Everyone must finish their current drink " "before the river card."
                ),
            },
            {
                "name": "Shot Clock",
                "description": "5 seconds to act or take a shot and auto-fold.",
            },
            {
                "name": "Drink Tax",
                "description": (
                    "Each red card in your final hand = one sip " "(reveal after play)."
                ),
            },
            # Wild and Chaos Effects
            {
                "name": "Joker's Wild",
                "description": (
                    "All Jacks become completely wild - "
                    "any suit, any rank you choose."
                ),
            },
            {
                "name": "Suit Swap",
                "description": "Hearts become Spades, Diamonds become Clubs this hand.",
            },
            {
                "name": "Rank Revolution",
                "description": "2s beat Aces this hand. All other ranks stay the same.",
            },
            {
                "name": "Time Warp",
                "description": (
                    "Play the hand completely backwards: showdown first, "
                    "then remove random cards from table!"
                ),
            },
            # Economic Effects (Clear Money Sources)
            {
                "name": "Poverty Mode",
                "description": "All bets limited to 1 chip maximum this hand.",
            },
            {
                "name": "High Roller",
                "description": "Minimum bet is 5x the entry this hand.",
            },
            {
                "name": "Charity Case",
                "description": (
                    "Player with fewest chips gets their ante "
                    "funded by richest player."
                ),
            },
            # Penalty-Based Modifiers (Clear Consequences)
            {
                "name": "Fold Tax",
                "description": "Anyone who folds pays 5 chip to the pot immediately.",
            },
            {
                "name": "Bluff Fine",
                "description": "Get caught bluffing = pay 2 chips to next hand's pot.",
            },
            {
                "name": "Speed Fine",
                "description": (
                    "Take longer than 10 seconds to act " "= pay 1 chip to pot."
                ),
            },
            {
                "name": "Talk Tax",
                "description": (
                    "Every word spoken during betting " "costs 1 chip to the pot."
                ),
            },
            # Skill Challenges (With Clear Rewards/Penalties)
            {
                "name": "Memory Challenge",
                "description": (
                    "Dealer names all community cards in order. "
                    "Success = collect 1 chip from each. "
                    "Fail = pay 1 chip to each."
                ),
            },
            {
                "name": "Quick Draw",
                "description": (
                    "Everyone pays 1 chip to quick-draw pot. "
                    "First to correctly announce their hand wins the pot."
                ),
            },
            {
                "name": "Bluff Bonus",
                "description": (
                    "Successfully bluff with 7-high or worse "
                    "= collect 2 chips from each other player."
                ),
            },
            {
                "name": "Prediction Pool",
                "description": (
                    "Everyone puts 1 chip in pool. "
                    "Guess the river card exactly = win the pool."
                ),
            },
            # Partnership Modifiers
            {
                "name": "Buddy System",
                "description": (
                    "Each player chooses a partner. "
                    "Partners share fate - both win or both lose."
                ),
            },
            {
                "name": "Duo Power",
                "description": (
                    "Partners can combine their hole cards - "
                    "each player plays with 4 cards total."
                ),
            },
            {
                "name": "Shared Vision",
                "description": (
                    "Partners can show each other one hole card "
                    "before betting starts."
                ),
            },
            {
                "name": "Tag Team",
                "description": (
                    "Partners alternate who plays each betting round "
                    "(pre-flop, flop, turn, river)."
                ),
            },
            {
                "name": "Power Couple",
                "description": (
                    "If both partners make it to showdown, they both get +1 chip bonus "
                    "from other players (revealed at end of round)."
                ),
            },
        ]

        # Separate endgame modifiers for special handling
        self.endgame_modifiers = [
            # Classic Endgame Modifiers
            {
                "name": "Final Boss",
                "description": (
                    "This is the last hand. " "Winner takes all remaining chips."
                ),
            },
            {
                "name": "Sudden Death",
                "description": "Anyone who folds is eliminated from the game.",
            },
            {
                "name": "Comeback Kid",
                "description": (
                    "Player with the worst hand can't lose chips this round "
                    "(reveal at the end of round)."
                ),
            },
            {
                "name": "Double or Nothing",
                "description": (
                    "Winner gets double payout, "
                    "but everyone else pays double penalty."
                ),
            },
            # High Stakes Endgame
            {
                "name": "All In Madness",
                "description": (
                    "Everyone must go all-in. "
                    "No calling, no folding allowed this hand."
                ),
            },
            {
                "name": "Chip Volcano",
                "description": (
                    "Everyone puts half their remaining chips in the center. "
                    "Winner takes the mountain."
                ),
            },
            {
                "name": "Last Stand",
                "description": (
                    "Player with fewest chips gets to act last "
                    "in ALL betting rounds."
                ),
            },
            # Dramatic Reversals
            {
                "name": "Underdog Victory",
                "description": (
                    "Worst hand wins the pot " "instead of best hand this round."
                ),
            },
            # Winner Takes All Variants
            {
                "name": "Crown Jewels",
                "description": (
                    "Winner of this hand becomes the 'King' - "
                    "all other players pay tribute (2 chips each)."
                ),
            },
            {
                "name": "Championship Belt",
                "description": (
                    "Winner takes 75% of all chips on the table. "
                    "Remaining 25% goes for the second best."
                ),
            },
            # Elimination Mechanics
            {
                "name": "Battle Royale",
                "description": "Lowest hand is eliminated. If tied, both eliminated.",
            },
            {
                "name": "Survivor",
                "description": (
                    "Only players who improve their hand from pre-flop to river "
                    "survive to next round."
                ),
            },
            # Time Pressure Endgame
            {
                "name": "Speed Round",
                "description": (
                    "3 seconds to act or auto-fold. " "No exceptions, no delays."
                ),
            },
            {
                "name": "Auction House",
                "description": (
                    "Players bid chips to see each other's hole cards "
                    "before betting."
                ),
            },
            {
                "name": "Lightning Round",
                "description": (
                    "Deal all 5 community cards at once. "
                    "Betting happens after each card revealed."
                ),
            },
            # Psychological Warfare
            {
                "name": "Confession Booth",
                "description": (
                    "Each player must truthfully state "
                    "their biggest bluff this session."
                ),
            },
            {
                "name": "Truth Serum",
                "description": (
                    "Everyone must honestly rate their hand 1-10 " "before any betting."
                ),
            },
            {
                "name": "Poker Face Off",
                "description": (
                    "Staring contest: losers must reveal " "one hole card to the table."
                ),
            },
            # Endgame Economics
            {
                "name": "Wealth Redistribution",
                "description": (
                    "Before the hand, richest player "
                    "gives 3 chips to poorest player."
                ),
            },
            {
                "name": "Emergency Fund",
                "description": (
                    "All players with less than 5 chips "
                    "get emergency funding from the pot."
                ),
            },
            {
                "name": "Final Ante",
                "description": (
                    "Everyone must put in their last 2 chips "
                    "before seeing cards. No backing out."
                ),
            },
            # Apocalypse Modifiers
            {
                "name": "Nuclear Option",
                "description": (
                    "Dealer burns the top 3 cards. "
                    "Play with whatever's left in the deck."
                ),
            },
            {
                "name": "Meteor Strike",
                "description": (
                    "Remove all face cards from the deck " "for this hand only."
                ),
            },
            {
                "name": "Solar Flare",
                "description": "All suits become the same suit (dealer's choice).",
            },
            # Legacy Modifiers
            {
                "name": "Hall of Fame",
                "description": (
                    "Winner's name gets written down " "as 'Champion of the Session'."
                ),
            },
            {
                "name": "Legendary Hand",
                "description": (
                    "This hand will be retold as a story. " "Play like legends."
                ),
            },
            {
                "name": "Photo Finish",
                "description": (
                    "Take a photo of the winning hand - "
                    "it goes in the poker hall of fame."
                ),
            },
            # Chaos Theory
            {
                "name": "Butterfly Effect",
                "description": (
                    "One random decision by dealer changes everything: "
                    "flip a coin for each community card to reverse it."
                ),
            },
            {
                "name": "Time Paradox",
                "description": (
                    "Play the hand twice with same cards. " "Best average result wins."
                ),
            },
            {
                "name": "Multiverse",
                "description": (
                    "Deal 2 separate boards. Players choose "
                    "which board to play after seeing both."
                ),
            },
        ]

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
            logging.debug("Debug mode enabled")
        else:
            self.force_endgame_button.pack_forget()
            self.force_endgame = False
            logging.debug("Debug mode disabled")

    def toggle_force_endgame(self) -> None:
        """Toggle forced endgame mode for testing."""
        self.force_endgame = not self.force_endgame
        if self.force_endgame:
            self.force_endgame_button.config(text="Stop Force Endgame", bg="#4CAF50")
            logging.debug("Forcing endgame modifiers")
        else:
            self.force_endgame_button.config(text="Force Endgame", bg="#ff6b6b")
            logging.debug("Normal modifier selection restored")

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
        random_value = random.random() * 100
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
        selected_modifier = random.choice(modifier_pool).copy()

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
            steel_rank = random.choice(ranks)
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

        logging.info("Game reset to initial state")

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
        logging.info("Texas Hold'em Modifier App started!")
        logging.info(
            "Available methods: app.get_stats(), app.add_modifier(name, description)"
        )
        logging.info(
            "Debug features: Toggle debug mode to access force endgame controls"
        )
        logging.info(f"Default game length: {self.total_game_rounds} rounds")
        endgame_pct = int(self.endgame_threshold * 100)
        endgame_rounds = int(self.total_game_rounds * self.endgame_threshold)
        logging.info(f"Endgame threshold: {endgame_pct}% ({endgame_rounds} rounds)")
        self.root.mainloop()


if __name__ == "__main__":
    app = PokerModifierApp()
    app.run()
