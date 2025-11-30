# Keyboard Coop Game

A fun 2-player cooperative word game where players take turns selecting adjacent letters on a QWERTY keyboard to form valid words.

## How to Play

1. **Setup**: Two players take turns at the same computer
2. **Turn System**: Player 1 starts by clicking any letter on the keyboard
3. **Adjacent Rule**: The next player must click a letter that is adjacent to the previously selected letter
4. **Word Formation**: Continue taking turns until you want to submit a word
5. **Scoring**: Press ENTER to submit the word. Valid words score points exponentially based on length:
   - 3 letters: 2 points
   - 4 letters: 4 points
   - 5 letters: 8 points
   - 6 letters: 16 points
   - And so on...

## Game Rules

- **Minimum Length**: Words must be at least 3 letters long
- **Adjacency**: Letters must be adjacent on a standard QWERTY keyboard
- **Valid Words**: Only dictionary words are accepted
- **Cooperative**: Both players share the same score - work together!

## Keyboard Adjacency

Each key is adjacent to its neighbors (including diagonals). For example:

- 'S' is adjacent to: Q, W, E, A, D, Z, X, C
- 'F' is adjacent to: E, R, T, D, G, C, V, B

## Controls

- **Mouse Click**: Select letters and buttons
- **ENTER Key**: Submit current word
- **R Key**: Reset the game
- **ENTER Button**: Submit current word (mouse)
- **RESET Button**: Reset the game (mouse)

## Installation

1. Make sure you have Python 3.6+ installed
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the game:
   ```bash
   python main.py
   ```

## Features

- Visual QWERTY keyboard layout
- Real-time adjacency highlighting
- Turn-based gameplay with player indicators
- Exponential scoring system
- Built-in dictionary validation
- Reset and restart functionality

## Strategy Tips

- Look for common word patterns and endings
- Try to set up your partner for success
- Longer words give exponentially more points
- Remember that some letters have more adjacent options than others

Enjoy playing together!
