"""Modifier data constants for the poker modifier application."""

from __future__ import annotations

from typing import TypeAlias

Modifier: TypeAlias = dict[str, str]

REGULAR_MODIFIERS: list[Modifier] = [
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
            "Make full house: everyone else pays 2 chips + takes 2 drinks."
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
            "Hearts and Diamonds are worth +1 rank (Jack becomes Queen, etc.)"
        ),
    },
    {
        "name": "Black Magic",
        "description": (
            "Spades and Clubs can be used as any suit for straights/flushes."
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
            "Deal each player a 3rd hole card. Discard one before the flop."
        ),
    },
    {
        "name": "Phantom Cards",
        "description": (
            "Deal 6 community cards, but randomly remove 1 before showdown."
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
            "Anyone who only calls (never raises) pays 1 chip penalty to pot."
        ),
    },
    # Information Warfare
    {
        "name": "Poker Face",
        "description": (
            "No talking, no expressions allowed. Pure silent poker this hand."
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
            "Take a drink before betting to get chip bonus to all your bets."
        ),
    },
    {
        "name": "Last Call",
        "description": (
            "Everyone must finish their current drink before the river card."
        ),
    },
    {
        "name": "Shot Clock",
        "description": "5 seconds to act or take a shot and auto-fold.",
    },
    {
        "name": "Drink Tax",
        "description": (
            "Each red card in your final hand = one sip (reveal after play)."
        ),
    },
    # Wild and Chaos Effects
    {
        "name": "Joker's Wild",
        "description": (
            "All Jacks become completely wild - any suit, any rank you choose."
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
            "Player with fewest chips gets their ante funded by richest player."
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
            "Take longer than 10 seconds to act = pay 1 chip to pot."
        ),
    },
    {
        "name": "Talk Tax",
        "description": (
            "Every word spoken during betting costs 1 chip to the pot."
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
            "Partners can show each other one hole card before betting starts."
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

ENDGAME_MODIFIERS: list[Modifier] = [
    # Classic Endgame Modifiers
    {
        "name": "Final Boss",
        "description": (
            "This is the last hand. Winner takes all remaining chips."
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
            "Winner gets double payout, but everyone else pays double penalty."
        ),
    },
    # High Stakes Endgame
    {
        "name": "All In Madness",
        "description": (
            "Everyone must go all-in. No calling, no folding allowed this hand."
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
            "Player with fewest chips gets to act last in ALL betting rounds."
        ),
    },
    # Dramatic Reversals
    {
        "name": "Underdog Victory",
        "description": (
            "Worst hand wins the pot instead of best hand this round."
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
            "3 seconds to act or auto-fold. No exceptions, no delays."
        ),
    },
    {
        "name": "Auction House",
        "description": (
            "Players bid chips to see each other's hole cards before betting."
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
            "Everyone must honestly rate their hand 1-10 before any betting."
        ),
    },
    {
        "name": "Poker Face Off",
        "description": (
            "Staring contest: losers must reveal one hole card to the table."
        ),
    },
    # Endgame Economics
    {
        "name": "Wealth Redistribution",
        "description": (
            "Before the hand, richest player gives 3 chips to poorest player."
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
            "Remove all face cards from the deck for this hand only."
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
            "Winner's name gets written down as 'Champion of the Session'."
        ),
    },
    {
        "name": "Legendary Hand",
        "description": (
            "This hand will be retold as a story. Play like legends."
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
            "Play the hand twice with same cards. Best average result wins."
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
