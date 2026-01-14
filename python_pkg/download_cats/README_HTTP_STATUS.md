# HTTP Status Code Anki Deck Generator

Generate Anki flashcards for HTTP status codes with cat images from [http.cat](https://http.cat).

## Features

- 📚 Comprehensive coverage of HTTP status codes (1xx - 5xx)
- 🐱 Fun cat images for each status code
- 🔄 Bidirectional flashcards for better memorization:
  - Code → Description + Image
  - Description + Image → Code
- 💾 Smart caching to avoid re-downloading images
- 🎨 Dark mode support in Anki

## Installation

Dependencies are already included in the main `requirements.txt`:
- `requests` - For downloading images
- `genanki` - For creating Anki packages

## Usage

### Basic Usage

Generate an Anki deck with default settings:

```bash
python python_pkg/download_cats/http_status_anki.py
```

This creates `http_status_codes.apkg` in the current directory.

### Custom Output

Specify a custom output file:

```bash
python python_pkg/download_cats/http_status_anki.py --output my_deck.apkg
```

### Custom Deck Name

Set a custom name for the Anki deck:

```bash
python python_pkg/download_cats/http_status_anki.py --deck-name "My HTTP Status Cards"
```

### Force Re-download

Download images even if cached versions exist:

```bash
python python_pkg/download_cats/http_status_anki.py --no-cache
```

### Verbose Logging

Enable detailed logging:

```bash
python python_pkg/download_cats/http_status_anki.py --verbose
```

## How It Works

1. **Downloads Images**: Fetches cat images from https://http.cat/[status_code].jpg
2. **Caches Locally**: Saves images to `python_pkg/download_cats/http_cat_cache/` to avoid re-downloading
3. **Creates Bidirectional Cards**:
   - **Front**: Status code (e.g., "200")
   - **Back**: Description ("OK") + Cat image
   - **Reverse**: Description + Image → Status code
4. **Exports to Anki**: Creates a `.apkg` file that can be imported into Anki

## Supported Status Codes

The script includes 79 HTTP status codes across all categories:

- **1xx Informational**: 100, 101, 102, 103
- **2xx Success**: 200, 201, 202, 203, 204, 205, 206, 207, 208, 226
- **3xx Redirection**: 300, 301, 302, 303, 304, 305, 307, 308
- **4xx Client Error**: 400-499 (including fun ones like 418 "I'm a teapot")
- **5xx Server Error**: 500-599 (including various server/proxy errors)

## Importing into Anki

1. Run the script to generate the `.apkg` file
2. Open Anki
3. Click "Import File"
4. Select the generated `.apkg` file
5. Start studying!

## Cache Location

Images are cached at: `python_pkg/download_cats/http_cat_cache/`

This directory is automatically created and is ignored by git.

## Testing

Run the comprehensive test suite:

```bash
python -m pytest python_pkg/download_cats/tests/test_http_status_anki.py -v
```

## License

Same as the parent repository.
