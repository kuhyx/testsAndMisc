# Champions League Live Scores (React + TS)

This app displays live and today's UEFA Champions League results. It uses:
- React + TypeScript (Vite) for the frontend
- A tiny Express proxy server that calls football-data.org to fetch match data

## Setup

1) Create a `.env` file in `TS/champions_leauge_scores/`:

```
FOOTBALL_DATA_API_KEY=your_api_token_here
PORT=8787
```

Sign up at https://www.football-data.org/ to get a free API token. Free tier has rate limits.

2) Install dependencies and run both servers:

```
npm install
npm run dev
```

- Frontend: http://localhost:5173
- API Proxy: http://localhost:8787

## Notes
- Live endpoint: `GET /api/live`
- Today endpoint: `GET /api/matches` (uses today's date by default)
- Edit polling intervals in `src/App.tsx` if needed.

## License
MIT