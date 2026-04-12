import { useCallback } from 'react';
import { fetchJson } from './fetchJson';
import { MatchCard, type Match } from './MatchCard';
import { useBackoffUntilSuccess } from './useBackoffUntilSuccess';

export type ApiResponse = {
  count: number;
  matches: Match[];
  fetchedAt: string;
};

export default function App() {
  const fetchLive = useCallback(() => fetchJson<ApiResponse>('http://localhost:8787/api/live', { headers: { 'cache-control': 'no-cache' } }), []);
  const fetchToday = useCallback(() => fetchJson<ApiResponse>('http://localhost:8787/api/matches', { headers: { 'cache-control': 'no-cache' } }), []);
  const live = useBackoffUntilSuccess<ApiResponse>(fetchLive);
  const today = useBackoffUntilSuccess<ApiResponse>(fetchToday);

  return (
    <div className="app">
      <h1>UEFA Champions League — Live Scores</h1>
      <section>
        <h2>Live right now</h2>
        {live.loading && <p>Loading…</p>}
  {live.error && <p className="error">{live.error}{typeof live.retryInSec === 'number' ? ` (${live.retryInSec}s)` : ''}</p>}
        {!live.loading && !live.error && live.data?.matches?.length === 0 && <p>No live matches.</p>}
        <div className="grid">
          {live.data?.matches?.map(m => <MatchCard key={m.id} m={m} />)}
        </div>
      </section>
      <section>
        <h2>Today</h2>
        {today.loading && <p>Loading…</p>}
  {today.error && <p className="error">{today.error}{typeof today.retryInSec === 'number' ? ` (${today.retryInSec}s)` : ''}</p>}
        <div className="grid">
          {today.data?.matches?.map(m => <MatchCard key={m.id} m={m} />)}
        </div>
      </section>
      <style>{`
        :root{ color-scheme: light dark; }
        body, html, #root { margin: 0; height: 100%; }
        .app { max-width: 900px; margin: 0 auto; padding: 1rem; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
        h1 { font-size: 1.6rem; margin: 0 0 1rem; }
        h2 { font-size: 1.2rem; margin: 1.2rem 0 .6rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: .75rem; }
        .card { border: 1px solid #4444; border-radius: 10px; padding: .75rem; background: #1112; backdrop-filter: blur(2px); }
        .row { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
        .teams { font-weight: 600; }
        .score { font-variant-numeric: tabular-nums; font-size: 1.2rem; }
        .meta { opacity: .8; font-size: .85rem; margin-top: .5rem; }
        .error { color: #d33; }
      `}</style>
    </div>
  );
}
