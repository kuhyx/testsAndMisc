# Warsaw Streets Anki Generator

Generate Anki flashcards for learning major Warsaw streets.

## Features

- Generates flashcards for major Warsaw streets (primary, secondary, tertiary roads)
- Uses real street data from OpenStreetMap
- Front of card: Map showing Warsaw with the street highlighted
- Back of card: Street name in Polish
- Self-contained .apkg file with embedded images

## Data Source

Street data is fetched from OpenStreetMap via the Overpass API.

## Installation

```bash
pip install matplotlib genanki geopandas requests shapely
```

## Usage

```bash
# Generate flashcards (fetches data from OSM)
./run.sh

# Or run directly
python -m warsaw_streets_anki
```

## Notes

- Only includes named streets tagged as primary, secondary, or tertiary highways
- Streets are filtered to remove duplicates and very short segments
- The first run will download data from Overpass API (may take a minute)
