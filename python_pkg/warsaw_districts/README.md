# Warsaw Districts Anki Generator

Generate Anki flashcards for learning the 18 districts (dzielnice) of Warsaw, Poland.

## Features

- Generates flashcards for all 18 Warsaw districts
- Front of card: Map showing only the district in question with its borders highlighted
- Back of card: District name in Polish
- Self-contained .apkg file with embedded images
- Compatible with AnkiWeb and AnkiDroid

## Installation

Install dependencies using your preferred method:

### Using pyenv (recommended)
```bash
pyenv install 3.10  # or later
pyenv shell 3.10
pip install matplotlib genanki
```

### Using pipx
```bash
pipx install --python python3.10 matplotlib genanki
```

### Using system package manager (Arch Linux)
```bash
sudo pacman -S python-matplotlib
pip install genanki
```

### Using pip directly
```bash
pip install matplotlib genanki
```

## Usage

### Generate flashcards

```bash
# From the repository root
python -m python_pkg.warsaw_districts.warsaw_districts_anki
```

This creates:
- `warsaw_districts.apkg` - Self-contained Anki package with all images embedded

### Custom options

```bash
# Custom output file
python -m python_pkg.warsaw_districts.warsaw_districts_anki --output my_cards.apkg

# Custom deck name
python -m python_pkg.warsaw_districts.warsaw_districts_anki --deck-name "Warszawa - Dzielnice"
```

## Importing into Anki

1. Open Anki
2. File → Import
3. Select the generated `warsaw_districts.apkg` file
4. Click Import

That's it! All images are already embedded in the .apkg file.

## Warsaw Districts

The generator includes all 18 official districts of Warsaw:

1. Bemowo
2. Białołęka
3. Bielany
4. Mokotów
5. Ochota
6. Praga-Południe
7. Praga-Północ
8. Rembertów
9. Śródmieście
10. Targówek
11. Ursus
12. Ursynów
13. Wawer
14. Wesoła
15. Wilanów
16. Włochy
17. Wola
18. Żoliborz

## Development

### Running tests

```bash
pytest python_pkg/warsaw_districts/tests/
```

### Code quality

```bash
ruff check python_pkg/warsaw_districts/
```

## License

Same as the parent repository.
