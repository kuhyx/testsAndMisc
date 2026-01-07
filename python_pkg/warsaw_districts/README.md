# Warsaw Districts Anki Generator

Generate Anki flashcards for learning the 18 districts (dzielnice) of Warsaw, Poland.

## Features

- Generates flashcards for all 18 Warsaw districts
- Front of card: Map showing only the district in question with its borders highlighted
- Back of card: District name in Polish
- Anki-compatible output format (semicolon-separated)
- Compatible with AnkiWeb and AnkiDroid

## Installation

```bash
pip install matplotlib
```

## Usage

### Generate flashcards

```bash
# From the repository root
python -m python_pkg.warsaw_districts.warsaw_districts_anki
```

This creates:
- `warsaw_districts_anki.txt` - Anki import file
- `warsaw_districts_images/` - Directory with 18 PNG map images

### Custom options

```bash
# Custom output file and image directory
python -m python_pkg.warsaw_districts.warsaw_districts_anki \
    --output my_cards.txt \
    --image-dir my_maps

# Custom deck name
python -m python_pkg.warsaw_districts.warsaw_districts_anki \
    --deck-name "Warszawa - Dzielnice"
```

## Importing into Anki

1. Open Anki
2. File → Import
3. Select the generated `warsaw_districts_anki.txt` file
4. Copy all images from `warsaw_districts_images/` to your Anki profile's `collection.media` folder
   - On Linux: `~/.local/share/Anki2/[Profile]/collection.media/`
   - On Windows: `%APPDATA%\Anki2\[Profile]\collection.media\`
   - On macOS: `~/Library/Application Support/Anki2/[Profile]/collection.media/`
5. Click Import

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

## Output Format

The generated file uses Anki's standard import format:

```
#separator:semicolon
#html:true
#deck:Warsaw Districts
#tags:geography warsaw poland
#columns:Front;Back

<img src="Bemowo.png">;Bemowo
<img src="Białołęka.png">;Białołęka
...
```

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
