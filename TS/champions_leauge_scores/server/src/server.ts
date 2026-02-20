import express, { Request, Response } from 'express';
import axios from 'axios';
import cors from 'cors';
import dotenv from 'dotenv';

dotenv.config();

const PORT = Number(process.env.PORT || 8787);
const API_BASE = 'https://api.football-data.org/v4';
const API_TOKEN = process.env.FOOTBALL_DATA_API_KEY;

if (!API_TOKEN) {

  console.warn('[server] FOOTBALL_DATA_API_KEY is not set. Live data will not work until you set it.');
}

const app = express();
app.use(cors());
app.disable('etag');
app.use((_req, res, next) => {
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('Expires', '0');
  next();
});

// Simple request/response logging middleware
app.use((req, res, next) => {
  const start = process.hrtime.bigint();
  const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  const MAX_LOG_BODY = 2000; // chars
  const clip = (s: string) => (s && s.length > MAX_LOG_BODY ? `${s.slice(0, MAX_LOG_BODY)}…(+${s.length - MAX_LOG_BODY})` : s);

  // Attach id so downstream handlers could use it if needed
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (res as any).locals = { ...(res as any).locals, requestId: id };

  // Patch res.json and res.send to capture response payload
  const originalJson = res.json.bind(res);
  const originalSend = res.send.bind(res);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (res as any).json = (body: unknown) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    try { (res as any).locals.bodyForLog = body; } catch { /* ignore */ }
    return originalJson(body);
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (res as any).send = (body: unknown) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    try { (res as any).locals.bodyForLog = body; } catch { /* ignore */ }
    return originalSend(body);
  };


  console.log(`[#${id}] -> ${req.method} ${req.originalUrl}` + (Object.keys(req.query || {}).length ? ` query=${JSON.stringify(req.query)}` : ''));

  res.on('finish', () => {
    const durMs = Number(process.hrtime.bigint() - start) / 1_000_000;
    let bodyPreview = '';
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const body = (res as any).locals?.bodyForLog;
      if (body !== undefined) {
        const str = typeof body === 'string' ? body : JSON.stringify(body);
        bodyPreview = ` body=${clip(str)}`;
      }
    } catch { /* ignore */ }

    console.log(`[#${id}] <- ${req.method} ${req.originalUrl} ${res.statusCode} ${durMs.toFixed(1)}ms${bodyPreview}`);
  });

  next();
});

// Axios interceptors to log outgoing requests and incoming responses
axios.interceptors.request.use(
  (config) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (config as any).metadata = { start: Date.now() };

    console.log(`[axios ->] ${String(config.method || 'GET').toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {

    console.warn('[axios req error]', error?.message || error);
    return Promise.reject(error);
  }
);

axios.interceptors.response.use(
  (response) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const started = (response.config as any).metadata?.start || Date.now();
    const dur = Date.now() - started;
    let dataStr = '';
    try {
      dataStr = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
    } catch { /* ignore */ }
    const size = dataStr?.length || 0;
    const MAX_LOG_BODY = 2000;
    const clip = (s: string) => (s && s.length > MAX_LOG_BODY ? `${s.slice(0, MAX_LOG_BODY)}…(+${s.length - MAX_LOG_BODY})` : s);

    console.log(`[axios <-] ${response.status} ${String(response.config.method || 'GET').toUpperCase()} ${response.config.url} ${dur}ms ~${size}B data=${clip(dataStr)}`);
    return response;
  },
  (error) => {
    const cfg = error?.config || {};
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const started = (cfg as any).metadata?.start || Date.now();
    const dur = Date.now() - started;
    const status = error?.response?.status;
    let dataStr = '';
    try {
      const d = error?.response?.data;
      dataStr = typeof d === 'string' ? d : JSON.stringify(d);
    } catch { /* ignore */ }
    const MAX_LOG_BODY = 2000;
    const clip = (s: string) => (s && s.length > MAX_LOG_BODY ? `${s.slice(0, MAX_LOG_BODY)}…(+${s.length - MAX_LOG_BODY})` : s);

    console.warn(`[axios ! ] ${status ?? 'ERR'} ${String(cfg.method || 'GET').toUpperCase()} ${cfg.url} ${dur}ms data=${dataStr ? clip(dataStr) : (error?.message || 'error')}`);
    return Promise.reject(error);
  }
);

app.get('/health', (_req: Request, res: Response) => res.json({ ok: true }));

function buildHeaders() {
  return {
    'X-Auth-Token': API_TOKEN || '',
  } as Record<string, string>;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizeMatch(m: Record<string, any>) {
  return {
    id: m.id,
    utcDate: m.utcDate,
    status: m.status,
    stage: m.stage,
    group: m.group,
    matchday: m.matchday,
    homeTeam: m.homeTeam?.name,
    awayTeam: m.awayTeam?.name,
    score: m.score,
    competition: m.competition?.name || 'UEFA Champions League',
    venue: m.venue,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    referees: m.referees?.map((r: Record<string, any>) => r.name).filter(Boolean) || [],
  };
}

app.get('/api/live', async (_req: Request, res: Response) => {
  try {
    if (!API_TOKEN) {
      const demo = [{
        id: 1,
        utcDate: new Date().toISOString(),
        status: 'LIVE',
        stage: 'GROUP_STAGE',
        group: 'Group A',
        matchday: 1,
        homeTeam: { name: 'Demo FC' },
        awayTeam: { name: 'Sample United' },
        score: { fullTime: { home: 1, away: 0 }, halfTime: { home: 1, away: 0 } },
        competition: { name: 'UEFA Champions League' },
      }];
      return res.json({ count: demo.length, matches: demo.map(normalizeMatch), fetchedAt: new Date().toISOString(), demo: true });
    }
    const url = `${API_BASE}/competitions/CL/matches`;
    const { data } = await axios.get(url, { headers: buildHeaders(), params: { status: 'LIVE' } });
    const matches = (data.matches || []).map(normalizeMatch);
    res.json({ count: matches.length, matches, fetchedAt: new Date().toISOString() });
  } catch (err: unknown) {
    const axErr = err as { response?: { status?: number; data?: unknown }; message?: string };
    const status = axErr?.response?.status || 500;
    res.status(status).json({ error: 'Failed to fetch live matches', details: axErr?.response?.data || axErr?.message });
  }
});

app.get('/api/matches', async (req: Request, res: Response) => {
  try {
    const date = (req.query.date as string) || new Date().toISOString().slice(0, 10);
    if (!API_TOKEN) {
      const demo = [{
        id: 2,
        utcDate: new Date().toISOString(),
        status: 'TIMED',
        stage: 'GROUP_STAGE',
        group: 'Group B',
        matchday: 1,
        homeTeam: { name: 'Placeholder City' },
        awayTeam: { name: 'Mock Rovers' },
        score: { fullTime: { home: null, away: null }, halfTime: { home: null, away: null } },
        competition: { name: 'UEFA Champions League' },
      }];
      return res.json({ count: demo.length, matches: demo.map(normalizeMatch), fetchedAt: new Date().toISOString(), date, demo: true });
    }
    const url = `${API_BASE}/competitions/CL/matches`;
    const { data } = await axios.get(url, {
      headers: buildHeaders(),
      params: { dateFrom: date, dateTo: date },
    });
    const matches = (data.matches || []).map(normalizeMatch);
    res.json({ count: matches.length, matches, fetchedAt: new Date().toISOString() });
  } catch (err: unknown) {
    const axErr = err as { response?: { status?: number; data?: unknown }; message?: string };
    const status = axErr?.response?.status || 500;
    res.status(status).json({ error: 'Failed to fetch matches', details: axErr?.response?.data || axErr?.message });
  }
});

app.listen(PORT, () => {

  console.log(`[server] Listening on http://localhost:${PORT}`);
});
