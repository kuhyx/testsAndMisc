# Polish License Plates Anki Generator

Generate Anki flashcards for learning Polish car license plate codes.

## Overview

This package generates Anki-compatible flashcard decks for all Polish vehicle registration plate codes. Each code is mapped to its corresponding location (city or powiat).

Polish license plates use a system where:

- First letter indicates the **voivodeship** (province)
- Following 1-2 letters indicate the specific **city** or **powiat** (county)

## Features

- **444 license plate codes** covering all Polish voivodeships, cities, and powiats
- **Bidirectional flashcards**:
  - Code → Location (e.g., `WY` → `Warszawa Wola`)
  - Location → Code (e.g., `Warszawa Wola` → `WY`)
- **888 total flashcards** for comprehensive learning
- Visual license plate styling in flashcards (yellow background, monospace font)
- Dark mode support
- Self-contained `.apkg` file - no manual setup required

## Data Source

License plate data is automatically extracted from Wikipedia's authoritative table:

- **Source**: [Vehicle registration plates of Poland](https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Poland)
- **Update**: Run `python -m python_pkg.polish_license_plates.fetch_license_plates` to refresh data

This ensures the codes are always based on the most current public information.

## Usage

### Generate Flashcards

```bash
# Generate with default settings
python -m python_pkg.polish_license_plates.polish_license_plates_anki

# Specify custom output file
python -m python_pkg.polish_license_plates.polish_license_plates_anki \
    --output my_plates.apkg

# Use custom deck name
python -m python_pkg.polish_license_plates.polish_license_plates_anki \
    --deck-name "My Polish Plates"
```

### Update License Plate Data

To fetch the latest data from Wikipedia:

```bash
# Use cached data if available (default)
python -m python_pkg.polish_license_plates.fetch_license_plates

# Force refresh from Wikipedia (ignore cache)
python -m python_pkg.polish_license_plates.fetch_license_plates --force
```

**Caching**: Downloaded Wikipedia data is cached for 7 days in `.wikipedia_cache/` to avoid unnecessary requests. Use `--force` to bypass the cache.

This will update `license_plate_data.py` with the current codes from Wikipedia.

**Requirements**: `pip install requests beautifulsoup4 lxml`

### Import into Anki

1. Open Anki
2. File → Import
3. Select the generated `.apkg` file
4. Click Import

## Examples

### License Plate Codes by Voivodeship

| Voivodeship         | First Letter | Example Codes                                    |
| ------------------- | ------------ | ------------------------------------------------ |
| Dolnośląskie        | D            | DA (Wrocław), DB (Wałbrzych), DJ (Jelenia Góra)  |
| Kujawsko-Pomorskie  | C            | CB (Bydgoszcz), CT (Toruń), CG (Grudziądz)       |
| Lubelskie           | L            | LL (Lublin), LC (Chełm), LZ (Zamość)             |
| Lubuskie            | F            | FZ (Zielona Góra), FG (Gorzów Wielkopolski)      |
| Łódzkie             | E            | ED (Łódź), EP (Piotrków Trybunalski)             |
| Małopolskie         | K            | KR (Kraków), KT (Tarnów), KN (Nowy Sącz)         |
| Mazowieckie         | W            | WA-WZ (Warsaw), WR (Radom), WS (Siedlce)         |
| Opolskie            | O            | OP (Opole), OK (Kędzierzyn-Koźle)                |
| Podkarpackie        | R            | RR (Rzeszów), RP (Przemyśl), RK (Krosno)         |
| Podlaskie           | B            | BI (Białystok), BL (Łomża), BSU (Suwałki)        |
| Pomorskie           | G            | GD (Gdańsk), GDY (Gdynia), GS (Słupsk)           |
| Śląskie             | S            | SK (Katowice), SC (Chorzów), SB (Bielsko-Biała)  |
| Świętokrzyskie      | T            | TK (Kielce), TSK (Skarżysko-Kamienna)            |
| Warmińsko-Mazurskie | N            | NO (Olsztyn), NE (Elbląg), NG (Giżycko)          |
| Wielkopolskie       | P            | PO (Poznań), PKA (Kalisz), PIA (Piła)            |
| Zachodniopomorskie  | Z            | ZS (Szczecin), ZKO (Koszalin), ZSW (Świnoujście) |

### Warsaw (Warszawa) Codes

Warsaw has an extensive range of codes (WA-WZ):

- WA: Warszawa (general)
- WB: Warszawa Bemowo
- WC: Ciechanów
- WD: Warszawa Praga Południe
- WE: Warszawa Praga Północ
- WH: Warszawa Mokotów
- WY: Warszawa Wola
- And many more...

## Data

The package includes 444 license plate codes covering:

- All 16 Polish voivodeships
- Major cities with powiat rights (e.g., Kraków, Gdańsk, Poznań)
- All powiats (counties) across Poland

## Testing

Run the test suite:

```bash
python -m pytest python_pkg/polish_license_plates/tests/ -v
```

All 17 tests validate:

- Data integrity (444 codes, no duplicates)
- Correct voivodeship prefixes
- Major cities present
- Anki package generation
- Bidirectional card templates
- CLI functionality

## Technical Details

- **Package format**: Anki `.apkg` (SQLite database)
- **Card model**: Bidirectional with two templates per note
- **Styling**: Custom CSS with license plate visual design
- **Tags**: `geography`, `poland`, `license-plates`, `transportation`

## Requirements

- Python 3.10+
- genanki (for Anki package generation)

## License

Part of the testsAndMisc repository.
