# Battery Status (React + TypeScript + Vite)

Shows current battery status (charging and percentage), plus time to full/empty when available.

## Run locally

1. Install deps
2. Start dev server

```bash
npm install
npm run dev
```

Then open the printed local URL (default http://localhost:5173).

Notes:
- The Battery Status API may be unavailable or disabled in some browsers for privacy reasons. In that case, the app will show a helpful message.
- On laptops it typically works in Chromium-based browsers; mobile support varies.