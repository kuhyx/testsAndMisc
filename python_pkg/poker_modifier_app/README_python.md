# Texas Hold'em Modifier App - Python Version

A desktop application built with Python and tkinter that randomly applies modifiers to Texas Hold'em poker games with configurable probability.

## Requirements

- Python 3.6+
- tkinter (usually comes with Python)

## How to Run

```bash
python poker_modifier_app.py
```

## Features

- **Configurable Probability**: Adjust the chance of getting a modifier (0-100%) with a slider
- **50+ Poker & Drinking Modifiers**: Real poker variations with drinking game twists!
- **Statistics Tracking**: Keep track of rounds played and modifiers applied
- **Modern GUI**: Clean, poker-themed interface with visual feedback
- **Easy to Extend**: Simple methods to add new modifiers

## How to Use

1. Run the Python script
2. Adjust the "Modifier Probability" slider to set the chance of getting a modifier
3. Click "Start Round" to begin a new round
4. The app will randomly decide whether to apply a modifier based on your probability setting
5. If a modifier is chosen, a random modifier will be selected and displayed

## Modifiers Included

### Classic Poker Modifiers

- **High Stakes**: All bets are doubled
- **Wild Card**: Next card can be used as any card
- **Bluff Master**: See one opponent's card before betting
- **All-In Fever**: If someone goes all-in, everyone must match or fold
- **Lucky Sevens**: Any hand with a 7 beats a pair
- **Reverse Psychology**: Lowest hand wins
- **Split Pot**: Pot split between top 2 hands
- **Texas Twister**: Each player gets an extra hole card
- **Blind Luck**: Play blind until the river
- **Community Boost**: Extra community card revealed
- **Minimum Madness**: Minimum bet tripled
- **Suit Supremacy**: Random suit cards worth +1 rank
- **Quick Draw**: Betting time cut in half
- **Royal Treatment**: Face cards worth double
- **Chip Challenge**: Winner gets extra house chips

## Modifiers Included

### Classic Poker Modifiers

- **High Stakes**: All bets are doubled
- **Wild Card**: Next card can be used as any card
- **Bluff Master**: See one opponent's card before betting
- **All-In Fever**: If someone goes all-in, everyone must match or fold
- **Lucky Sevens**: Any hand with a 7 beats a pair
- **Reverse Psychology**: Lowest hand wins
- **Split Pot**: Pot split between top 2 hands
- **Texas Twister**: Each player gets an extra hole card
- **Blind Luck**: Play blind until the river
- **Community Boost**: Extra community card revealed
- **Minimum Madness**: Minimum bet tripled
- **Suit Supremacy**: Random suit cards worth +1 rank
- **Quick Draw**: Betting time cut in half
- **Royal Treatment**: Face cards worth double
- **Chip Challenge**: Winner gets extra house chips

### Drinking Game Modifiers

- **Red or Black**: Guess community card colors for double winnings
- **Pocket Rockets**: Pocket Aces trigger drinks for everyone else
- **Rainbow Flop**: 3-suit flop boosts flush draws
- **Suited Connectors**: Beat any pocket pair
- **Drink or Fold**: Choose to drink and stay in or fold
- **Shot Clock**: 10 seconds per decision or auto-fold
- **Double Down**: Pay double to see opponent's cards
- **Bad Beat Jackpot**: Losing with full house+ makes others drink
- **Chaser Round**: Previous loser gets bonus stack
- **Face Card Frenzy**: Each face card = take a sip
- **Burn Card Reveal**: Matching burn cards = drinks + chips
- **Pair Tax**: Pocket pairs cost extra or drink
- **Kicker Clash**: Lowest kicker in tie drinks
- **Color Blind**: Red cards +1, black cards -1
- **Sip and Tell**: Drink and honestly rate your hand
- **Last Call**: Final betting round, no more cards
- **Drink the River**: River helps you = others drink
- **Tipsy Tells**: Must make exaggerated expressions
- **House Rules**: Deuces wild but drink when used
- **Side Bet Madness**: Bet on what flop will contain
- **Fold Penalty**: Folders drink and sit out next hand
- **Straight Shooter**: Complete straight = pick someone to finish drink
- **Flush Rush**: First flush wins side pot from all
- **Ace High Drama**: Ace high wins double but finish drink
- **Bluff Check**: Caught bluffing = drink + penalty
- **Small Ball**: Only minimum bets allowed
- **Position Power**: Button sees everyone's first card
- **Community Chest**: 6 community cards total
- **Heads Up**: Only top 2 hands after flop continue
- **Dealer's Choice**: Dealer picks wild suits
- **Ante Up**: Double ante or take two drinks
- **Showdown Shuffle**: Simultaneous card reveal
- **Lucky Draw**: Extra card, choose best 2
- **Betting Blind**: First round before looking at cards
- **Chip and a Chair**: Short stack sees early community card
- **All Red**: Red cards boost hand level
- **Mississippi Stud**: Fold after flop for half bet back

## Code Structure

- `PokerModifierApp`: Main application class
- `setup_gui()`: Creates the tkinter interface
- `start_round()`: Main game logic for starting rounds
- `apply_random_modifier()`: Selects and displays a random modifier
- `show_no_modifier()`: Displays when no modifier is chosen
- `add_modifier()`: Method to add new modifiers
- `get_stats()`: Returns current statistics

## Customization

You can easily add new modifiers programmatically:

```python
app = PokerModifierApp()
app.add_modifier("Your Modifier Name", "Description of what it does")
app.run()
```

## GUI Components

- **Title**: Application header
- **Settings Panel**: Probability slider
- **Result Display**: Shows modifier or "no modifier" message
- **Start Button**: Triggers new round
- **Statistics**: Displays rounds played and modifiers applied
