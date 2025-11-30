# Lichess Bot (minimal)

A small Lichess BOT that accepts standard challenges and plays quick random legal moves using python-chess. It demonstrates the Lichess Board API basics with a simple, readable implementation.

## Features

- Connects to Lichess Board API via streaming NDJSON
- Accepts only standard chess challenges (bullet/blitz/rapid/classical)
- Spawns a thread per active game
- Plays random legal moves (swap in a stronger engine later)
- Simple logging and basic retries on transient network errors

## Requirements

- Python 3.9+
- A Lichess account that is activated as a BOT
- A Lichess API access token with at least the scopes:
  - bot:play
  - challenge:read
  - challenge:write

Install dependencies:

```bash
pip install -r PYTHON/lichess_bot/requirements.txt
```

## Activate BOT and get a token

1. Create or use an existing Lichess account for your bot.
2. Activate it as a BOT (one-time): https://lichess.org/api#tag/Bot
   - If not already BOT, you need to convert the account; follow Lichess docs.
3. Create a personal API token: https://lichess.org/account/oauth/token/create
   - Grant scopes: bot:play, challenge:read, challenge:write

Export the token in your shell (recommended):

```bash
export LICHESS_TOKEN="your_bot_token_here"
```

## Run

From the repo root:

```bash
python -m PYTHON.lichess_bot.main
```

Optional flags:

- `--log-level INFO|DEBUG|WARNING|ERROR` (default: INFO)
- `--decline-correspondence` (declines correspondence challenges)

You can also use the helper script:

```bash
bash PYTHON/lichess_bot/run.sh
```

## Notes

- The engine is intentionally weak (random moves). Swap it with a UCI engine or implement a better search in `engine.py`.
- Network calls hit real Lichess endpoints. Keep the bot polite; respect rate limits.

## Development

- Small unit tests are in `tests/` and only cover local helpers (no network). Run:

```bash
python -m pytest PYTHON/lichess_bot/tests -q
```

If you add tests requiring third-party packages, install them in your environment first.
