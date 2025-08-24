import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type Score = {
  fullTime?: { home?: number | null; away?: number | null };
  halfTime?: { home?: number | null; away?: number | null };
  winner?: string | null;
};

type Match = {
  id: number;
  utcDate: string;
  status: string;
  stage?: string;
  group?: string;
  matchday?: number;
  homeTeam: string;
  awayTeam: string;
  score: Score;
  competition?: string;
  venue?: string;
  referees?: string[];
};

type ApiResponse = {
  count: number;
  matches: Match[];
  fetchedAt: string;
};

function useFetchOnce<T>(fn: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const result = await fn();
        if (mounted) {
          setData(result);
          setError(null);
        }
      } catch (e: any) {
        if (mounted) setError(e?.message || 'Failed to fetch');
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [fn]);

  return { data, error, loading } as const;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { cache: 'no-store', ...init });
  if (!res.ok) {
    const text = await res.text();
    let body: any = null;
    try { body = text ? JSON.parse(text) : null; } catch { /* noop */ }
    const err: any = new Error(`HTTP ${res.status}`);
    err.status = res.status;
    err.body = body;
    // Try to derive wait seconds for 429 from body.details.message like: "You reached your request limit. Wait 56 seconds."
    if (res.status === 429) {
      const msg: string | undefined = body?.details?.message || body?.message || body?.error;
      const m = msg ? msg.match(/(\d+)\s*seconds?/) : null;
      if (m) err.waitSec = Number(m[1]);
    }
    throw err;
  }
  return res.json();
}

function MatchCard({ m }: { m: Match }) {
  const kickoff = useMemo(() => new Date(m.utcDate), [m.utcDate]);
  const time = kickoff.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const date = kickoff.toLocaleDateString();
  const ftHome = m.score.fullTime?.home ?? '-';
  const ftAway = m.score.fullTime?.away ?? '-';
  const statusNice = m.status.replace('_', ' ');

  return (
    <div className="card">
      <div className="row teams">
        <span className="home">{m.homeTeam}</span>
        <span className="score">{ftHome} : {ftAway}</span>
        <span className="away">{m.awayTeam}</span>
      </div>
      <div className="row meta">
        <span>{statusNice}</span>
        <span>{date} {time}</span>
        {m.group && <span>{m.group}</span>}
        {m.stage && <span>{m.stage}</span>}
      </div>
    </div>
  );
}

function useBackoffUntilSuccess<T>(fn: () => Promise<T>, opts?: { baseDelaySec?: number; maxDelaySec?: number; factor?: number }) {
  const base = Math.max(1, opts?.baseDelaySec ?? 30);
  const max = Math.max(base, opts?.maxDelaySec ?? 300);
  const factor = Math.max(1.1, opts?.factor ?? 2);

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [retryInSec, setRetryInSec] = useState<number | null>(null);

  const delayRef = useRef<number>(base);
  const tRetryRef = useRef<number | null>(null);
  const tTickRef = useRef<number | null>(null);
  const inFlightRef = useRef<boolean>(false);

  useEffect(() => {
    let mounted = true;
    const clearTimers = () => {
      if (tRetryRef.current) { window.clearTimeout(tRetryRef.current); tRetryRef.current = null; }
      if (tTickRef.current) { window.clearInterval(tTickRef.current); tTickRef.current = null; }
    };
    const scheduleRetry = (sec: number) => {
      clearTimers();
      const clamped = Math.min(Math.max(1, Math.floor(sec)), max);
      setRetryInSec(clamped);
      // countdown ticker
      tTickRef.current = window.setInterval(() => {
        setRetryInSec(v => (v && v > 0 ? v - 1 : 0));
      }, 1000);
      tRetryRef.current = window.setTimeout(() => {
        if (!mounted) return;
        clearTimers();
        run();
      }, clamped * 1000);
    };
    const run = async () => {
      if (inFlightRef.current) return; // avoid overlapping calls
      try {
        inFlightRef.current = true;
        setLoading(true);
        const result = await fn();
        if (!mounted) return;
        clearTimers();
        setData(result);
        setError(null);
      } catch (e: any) {
        if (!mounted) return;
        // 429: backoff and retry
        if (e?.status === 429) {
          const suggested = Number(e?.waitSec) || delayRef.current || base;
          const next = Math.min(max, Math.max(base, suggested));
          delayRef.current = Math.min(max, Math.ceil(next * factor));
          setError(`Rate limited. Retrying in ${next}s...`);
          scheduleRetry(next);
          return;
        }
        setError(e?.message || 'Failed to fetch');
      } finally {
        inFlightRef.current = false;
        if (mounted) setLoading(false);
      }
    };
    run();
    return () => { mounted = false; clearTimers(); };
  }, [fn, base, max, factor]);

  return { data, error, loading, retryInSec } as const;
}

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
