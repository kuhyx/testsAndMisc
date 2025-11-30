import json
import logging
import os
import random
import sys

import pygame

logging.basicConfig(level=logging.INFO)

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1366
SCREEN_HEIGHT = 768
BACKGROUND_COLOR = (30, 30, 40)
KEYBOARD_COLOR = (60, 60, 70)
KEY_COLOR = (80, 80, 90)
KEY_HOVER_COLOR = (100, 100, 110)
KEY_SELECTED_COLOR = (150, 150, 200)
KEY_AVAILABLE_COLOR = (100, 150, 100)
TEXT_COLOR = (255, 255, 255)
PLAYER_COLORS = [(255, 100, 100), (100, 100, 255)]

# Keyboard layout
KEYBOARD_LAYOUT = [
    ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
    ["z", "x", "c", "v", "b", "n", "m"],
]

# Key adjacency mapping
KEY_ADJACENCY = {
    "q": ["w", "a", "s"],
    "w": ["q", "e", "a", "s", "d"],
    "e": ["w", "r", "s", "d", "f"],
    "r": ["e", "t", "d", "f", "g"],
    "t": ["r", "y", "f", "g", "h"],
    "y": ["t", "u", "g", "h", "j"],
    "u": ["y", "i", "h", "j", "k"],
    "i": ["u", "o", "j", "k", "l"],
    "o": ["i", "p", "k", "l"],
    "p": ["o", "l"],
    "a": ["q", "w", "s", "z", "x"],
    "s": ["q", "w", "e", "a", "d", "z", "x", "c"],
    "d": ["w", "e", "r", "s", "f", "x", "c", "v"],
    "f": ["e", "r", "t", "d", "g", "c", "v", "b"],
    "g": ["r", "t", "y", "f", "h", "v", "b", "n"],
    "h": ["t", "y", "u", "g", "j", "b", "n", "m"],
    "j": ["y", "u", "i", "h", "k", "n", "m"],
    "k": ["u", "i", "o", "j", "l", "m"],
    "l": ["i", "o", "p", "k"],
    "z": ["a", "s", "x"],
    "x": ["a", "s", "d", "z", "c"],
    "c": ["s", "d", "f", "x", "v"],
    "v": ["d", "f", "g", "c", "b"],
    "b": ["f", "g", "h", "v", "n"],
    "n": ["g", "h", "j", "b", "m"],
    "m": ["h", "j", "k", "n"],
}


class KeyboardCoopGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Keyboard Coop Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 20)

        # Load dictionary
        self.dictionary = self.load_dictionary()

        # Initialize game state
        self.current_player = 0
        self.current_word = ""
        self.selected_letters = []
        self.score = 0
        self.game_over = False
        self.message = "Player 1: Choose any letter to start!"

        # Generate random keyboard layout and adjacency
        self.generate_random_keyboard()

        # Key positions
        self.key_positions = self.calculate_key_positions()

    def load_dictionary(self):
        """Load dictionary from words_dictionary.json file."""
        try:
            dictionary_path = os.path.join(
                os.path.dirname(__file__), "words_dictionary.json"
            )
            with open(dictionary_path, encoding="utf-8") as f:
                dictionary_data = json.load(f)
            # Convert to set for faster lookup (we only need the keys)
            return set(dictionary_data.keys())
        except FileNotFoundError:
            logging.warning(
                "words_dictionary.json not found, using fallback dictionary"
            )
            # Fallback to a smaller dictionary if file not found
            return {
                "cat",
                "dog",
                "car",
                "bat",
                "rat",
                "hat",
                "mat",
                "sat",
                "fat",
                "pat",
                "the",
                "and",
                "for",
                "are",
                "but",
                "not",
                "you",
                "all",
                "can",
                "had",
                "her",
                "was",
                "one",
                "our",
                "out",
                "day",
                "get",
                "has",
                "him",
                "his",
                "how",
                "man",
                "new",
                "now",
                "old",
                "see",
                "two",
                "way",
                "who",
                "boy",
                "work",
                "know",
                "place",
                "year",
                "live",
                "me",
                "back",
                "give",
                "good",
            }
        except json.JSONDecodeError:
            logging.warning(
                "Error reading words_dictionary.json, " "using fallback dictionary"
            )
            return {
                "cat",
                "dog",
                "car",
                "bat",
                "rat",
                "hat",
                "mat",
                "sat",
                "fat",
                "pat",
                "the",
                "and",
                "for",
                "are",
                "but",
                "not",
                "you",
                "all",
                "can",
                "had",
                "work",
                "know",
                "place",
                "year",
                "live",
                "me",
                "back",
                "give",
                "good",
            }

    def generate_random_keyboard(self):
        """Generate a random keyboard layout and calculate adjacencies."""
        # All 26 letters
        all_letters = list("abcdefghijklmnopqrstuvwxyz")
        random.shuffle(all_letters)

        # Create random layout with same structure as QWERTY (10-9-7)
        self.keyboard_layout = [
            all_letters[0:10],  # Top row: 10 keys
            all_letters[10:19],  # Middle row: 9 keys
            all_letters[19:26],  # Bottom row: 7 keys
        ]

        # Update available letters
        self.available_letters = set(all_letters)

        # Calculate adjacencies based on new layout
        self.calculate_adjacencies()

    def calculate_adjacencies(self):
        """Calculate adjacencies based on current keyboard layout."""
        self.key_adjacency = {}

        for row_idx, row in enumerate(self.keyboard_layout):
            for col_idx, letter in enumerate(row):
                adjacents = []

                # Check all 8 directions (including diagonals)
                directions = [
                    (-1, -1),
                    (-1, 0),
                    (-1, 1),  # Above
                    (0, -1),
                    (0, 1),  # Same row
                    (1, -1),
                    (1, 0),
                    (1, 1),  # Below
                ]

                for dr, dc in directions:
                    new_row = row_idx + dr
                    new_col = col_idx + dc

                    # Check bounds
                    if 0 <= new_row < len(self.keyboard_layout):
                        if 0 <= new_col < len(self.keyboard_layout[new_row]):
                            adjacents.append(self.keyboard_layout[new_row][new_col])

                self.key_adjacency[letter] = adjacents

    def calculate_key_positions(self):
        """Calculate the position of each key on screen."""
        positions = {}
        key_width = 60
        key_height = 60
        key_spacing = 8
        start_x = 50
        start_y = 320

        for row_idx, row in enumerate(self.keyboard_layout):
            row_offset = row_idx * 30  # Offset for layout
            for col_idx, key in enumerate(row):
                x = start_x + col_idx * (key_width + key_spacing) + row_offset
                y = start_y + row_idx * (key_height + key_spacing)
                positions[key] = pygame.Rect(x, y, key_width, key_height)

        return positions

    def get_key_at_position(self, pos):
        """Get the key at the given mouse position."""
        for key, rect in self.key_positions.items():
            if rect.collidepoint(pos):
                return key
        return None

    def is_valid_move(self, letter):
        """Check if the letter is a valid move."""
        if not self.selected_letters:
            return True  # First move can be any letter

        last_letter = self.selected_letters[-1]
        return letter in self.key_adjacency[last_letter]

    def is_valid_word(self, word):
        """Check if the word is in the dictionary."""
        return word.lower() in self.dictionary

    def calculate_score(self, word_length):
        """Calculate score exponentially based on word length."""
        if word_length < 3:
            return 0
        return 2 ** (word_length - 2)

    def handle_letter_click(self, letter):
        """Handle clicking on a letter."""
        if letter in self.available_letters and self.is_valid_move(letter):
            self.selected_letters.append(letter)
            self.current_word += letter

            # Update available letters to include adjacent letters AND the same letter
            adjacent_letters = (
                set(self.key_adjacency[letter])
                if letter in self.key_adjacency
                else set()
            )
            adjacent_letters.add(letter)  # Allow selecting the same letter again
            self.available_letters = adjacent_letters

            # Switch player
            self.current_player = 1 - self.current_player
            self.message = (
                f"Player {self.current_player + 1}: Choose an adjacent letter!"
            )

            # If no valid moves available, force word submission
            if not self.available_letters:
                self.submit_word()

    def submit_word(self):
        """Submit the current word and check if it's valid."""
        if len(self.current_word) >= 3 and self.is_valid_word(self.current_word):
            points = self.calculate_score(len(self.current_word))
            self.score += points
            self.message = (
                f"'{self.current_word}' is valid! +{points} points "
                f"(Total: {self.score}) - New keyboard!"
            )

            # Randomize keyboard layout after scoring
            self.generate_random_keyboard()
            self.key_positions = self.calculate_key_positions()

        elif len(self.current_word) < 3:
            self.message = f"'{self.current_word}' is too short! (minimum 3 letters)"
        else:
            self.message = f"'{self.current_word}' is not a valid word!"

        # Reset for next word
        self.current_word = ""
        self.selected_letters = []
        self.current_player = 0

    def reset_game(self):
        """Reset the game to initial state."""
        self.current_player = 0
        self.current_word = ""
        self.selected_letters = []
        self.score = 0
        self.game_over = False
        self.message = "Player 1: Choose any letter to start!"

        # Generate new random keyboard layout
        self.generate_random_keyboard()
        self.key_positions = self.calculate_key_positions()

    def draw_keyboard(self):
        """Draw the virtual keyboard."""
        mouse_pos = pygame.mouse.get_pos()

        for letter, rect in self.key_positions.items():
            # Determine key color
            if letter in self.selected_letters:
                color = KEY_SELECTED_COLOR
            elif letter in self.available_letters:
                color = KEY_AVAILABLE_COLOR
            elif rect.collidepoint(mouse_pos) and letter in self.available_letters:
                color = KEY_HOVER_COLOR
            else:
                color = KEY_COLOR

            # Draw key
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, TEXT_COLOR, rect, 2)

            # Draw letter
            text = self.small_font.render(letter.upper(), True, TEXT_COLOR)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)

    def draw_ui(self):
        """Draw the user interface."""
        # Title
        title = self.large_font.render("Keyboard Coop Game", True, TEXT_COLOR)
        self.screen.blit(title, (30, 20))

        # Current word
        word_text = self.font.render(
            f"Current Word: {self.current_word.upper()}", True, TEXT_COLOR
        )
        self.screen.blit(word_text, (30, 50))

        # Score
        score_text = self.font.render(f"Score: {self.score}", True, TEXT_COLOR)
        self.screen.blit(score_text, (30, 75))

        # Current player
        player_color = PLAYER_COLORS[self.current_player]
        player_text = self.font.render(
            f"Current Player: {self.current_player + 1}", True, player_color
        )
        self.screen.blit(player_text, (30, 100))

        # Message
        message_text = self.font.render(self.message, True, TEXT_COLOR)
        self.screen.blit(message_text, (30, 125))

        # Instructions - Move to right side and make more compact
        instructions = [
            "Instructions:",
            "• Take turns selecting adjacent letters",
            "• Click letters or use keyboard to select",
            "• Same letter can be selected consecutively",
            "• Press ENTER to submit word (min 3 letters)",
            "• Press R to reset game",
            "• Score increases exponentially",
            "• Keyboard randomizes after each valid word!",
        ]

        start_x = 750
        for i, instruction in enumerate(instructions):
            inst_text = self.small_font.render(instruction, True, TEXT_COLOR)
            self.screen.blit(inst_text, (start_x, 20 + i * 22))

        # Enter button - smaller and repositioned
        enter_rect = pygame.Rect(750, 190, 120, 40)
        pygame.draw.rect(self.screen, KEY_COLOR, enter_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, enter_rect, 2)
        enter_text = self.small_font.render("ENTER", True, TEXT_COLOR)
        enter_text_rect = enter_text.get_rect(center=enter_rect.center)
        self.screen.blit(enter_text, enter_text_rect)

        # Reset button - smaller and repositioned
        reset_rect = pygame.Rect(880, 190, 120, 40)
        pygame.draw.rect(self.screen, KEY_COLOR, reset_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, reset_rect, 2)
        reset_text = self.small_font.render("RESET", True, TEXT_COLOR)
        reset_text_rect = reset_text.get_rect(center=reset_rect.center)
        self.screen.blit(reset_text, reset_text_rect)

        return enter_rect, reset_rect

    def handle_click(self, pos):
        """Handle mouse clicks."""
        # Check if clicked on a key
        key = self.get_key_at_position(pos)
        if key:
            self.handle_letter_click(key)

        # Check UI buttons
        enter_rect = pygame.Rect(750, 190, 120, 40)
        reset_rect = pygame.Rect(880, 190, 120, 40)

        if enter_rect.collidepoint(pos):
            self.submit_word()
        elif reset_rect.collidepoint(pos):
            self.reset_game()

    def run(self):
        """Main game loop."""
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.submit_word()
                    elif event.key == pygame.K_r:
                        self.reset_game()
                    else:
                        # Handle letter key presses
                        key_name = pygame.key.name(event.key)
                        if len(key_name) == 1 and key_name.isalpha():
                            self.handle_letter_click(key_name.lower())

            # Clear screen
            self.screen.fill(BACKGROUND_COLOR)

            # Draw everything
            self.draw_keyboard()
            self.draw_ui()

            # Update display
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = KeyboardCoopGame()
    game.run()
