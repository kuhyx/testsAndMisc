import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import request from 'supertest';
import type { Request, Response } from 'express';

vi.mock('axios', () => {
  const interceptors = {
    request: { use: vi.fn() },
    response: { use: vi.fn() },
  };
  return {
    default: {
      get: vi.fn(),
      interceptors,
    },
  };
});

vi.mock('dotenv', () => ({ default: { config: vi.fn() } }));

describe('server', () => {
  let app: typeof import('./server').app;
  let normalizeMatch: typeof import('./server').normalizeMatch;
  let buildHeaders: typeof import('./server').buildHeaders;
  let clipStr: typeof import('./server').clipStr;
  let axiosRequestOnFulfilled: typeof import('./server').axiosRequestOnFulfilled;
  let axiosRequestOnRejected: typeof import('./server').axiosRequestOnRejected;
  let axiosResponseOnFulfilled: typeof import('./server').axiosResponseOnFulfilled;
  let axiosResponseOnRejected: typeof import('./server').axiosResponseOnRejected;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let axiosMock: any;

  beforeEach(async () => {
    vi.resetModules();
    delete process.env.FOOTBALL_DATA_API_KEY;
    axiosMock = (await import('axios')).default;
    const server = await import('./server');
    app = server.app;
    normalizeMatch = server.normalizeMatch;
    buildHeaders = server.buildHeaders;
    clipStr = server.clipStr;
    axiosRequestOnFulfilled = server.axiosRequestOnFulfilled;
    axiosRequestOnRejected = server.axiosRequestOnRejected;
    axiosResponseOnFulfilled = server.axiosResponseOnFulfilled;
    axiosResponseOnRejected = server.axiosResponseOnRejected;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('clipStr', () => {
    it('returns short strings unchanged', () => {
      expect(clipStr('hello', 10)).toBe('hello');
    });

    it('clips long strings', () => {
      const long = 'a'.repeat(100);
      const result = clipStr(long, 10);
      expect(result).toBe('a'.repeat(10) + '…(+90)');
    });

    it('returns empty string as-is', () => {
      expect(clipStr('', 10)).toBe('');
    });
  });

  describe('axiosRequestOnFulfilled', () => {
    it('sets metadata.start and returns config', () => {
      const config = { method: 'get', url: '/test' };
      const result = axiosRequestOnFulfilled(config);
      expect(result).toBe(config);
      expect(config).toHaveProperty('metadata');
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      expect((config as any).metadata.start).toBeTypeOf('number');
    });

    it('defaults method to GET in log', () => {
      const config = { url: '/test' };
      const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
      axiosRequestOnFulfilled(config);
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('[axios ->] GET /test'));
      spy.mockRestore();
    });
  });

  describe('axiosRequestOnRejected', () => {
    it('rejects with the error', async () => {
      const err = { message: 'bad request' };
      await expect(axiosRequestOnRejected(err)).rejects.toBe(err);
    });

    it('logs error without message', async () => {
      const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await expect(axiosRequestOnRejected({} as any)).rejects.toEqual({});
      expect(spy).toHaveBeenCalledWith('[axios req error]', {});
      spy.mockRestore();
    });
  });

  describe('axiosResponseOnFulfilled', () => {
    it('returns the response and logs', () => {
      const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
      const response = {
        status: 200,
        config: { method: 'get', url: '/api/test', metadata: { start: Date.now() - 100 } },
        data: { key: 'value' },
      };
      const result = axiosResponseOnFulfilled(response);
      expect(result).toBe(response);
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('[axios <-] 200 GET /api/test'));
      spy.mockRestore();
    });

    it('handles string data', () => {
      const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
      axiosResponseOnFulfilled({
        status: 200,
        config: { method: 'post', url: '/test' },
        data: 'plain text',
      });
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('data=plain text'));
      spy.mockRestore();
    });

    it('clips large data', () => {
      const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
      axiosResponseOnFulfilled({
        status: 200,
        config: { method: 'get', url: '/test' },
        data: 'x'.repeat(3000),
      });
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('…(+1000)'));
      spy.mockRestore();
    });

    it('handles non-serializable data', () => {
      const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
      const circular = {} as Record<string, unknown>;
      circular.self = circular;
      axiosResponseOnFulfilled({
        status: 200,
        config: { method: 'get', url: '/test' },
        data: circular,
      });
      expect(spy).toHaveBeenCalled();
      spy.mockRestore();
    });

    it('defaults method to GET when missing', () => {
      const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
      axiosResponseOnFulfilled({
        status: 200,
        config: { url: '/test' },
        data: '',
      });
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('GET'));
      spy.mockRestore();
    });
  });

  describe('axiosResponseOnRejected', () => {
    it('rejects and logs error with response status', async () => {
      const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const err = {
        config: { method: 'get', url: '/fail', metadata: { start: Date.now() } },
        response: { status: 500, data: { msg: 'error' } },
        message: 'AxiosError',
      };
      await expect(axiosResponseOnRejected(err)).rejects.toBe(err);
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('[axios ! ] 500'));
      spy.mockRestore();
    });

    it('logs ERR when no response status', async () => {
      const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const err = { message: 'Network Error' };
      await expect(axiosResponseOnRejected(err)).rejects.toBe(err);
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('ERR'));
      spy.mockRestore();
    });

    it('handles string response data', async () => {
      const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const err = {
        config: { method: 'get', url: '/fail' },
        response: { status: 429, data: 'Rate limited' },
      };
      await expect(axiosResponseOnRejected(err)).rejects.toBe(err);
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('data=Rate limited'));
      spy.mockRestore();
    });

    it('uses error message when no data', async () => {
      const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const err = { config: {}, message: 'timeout' };
      await expect(axiosResponseOnRejected(err)).rejects.toBe(err);
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('data=timeout'));
      spy.mockRestore();
    });

    it('clips large response data', async () => {
      const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const err = {
        config: {},
        response: { status: 400, data: 'y'.repeat(3000) },
      };
      await expect(axiosResponseOnRejected(err)).rejects.toBe(err);
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('…(+1000)'));
      spy.mockRestore();
    });

    it('falls back to "error" when no message and no data', async () => {
      const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      await expect(axiosResponseOnRejected({})).rejects.toEqual({});
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('data=error'));
      spy.mockRestore();
    });

    it('handles non-serializable error response data', async () => {
      const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const circular: Record<string, unknown> = {};
      circular.self = circular;
      const err = {
        config: { method: 'get', url: '/fail' },
        response: { status: 500, data: circular },
        message: 'Circular data error',
      };
      await expect(axiosResponseOnRejected(err)).rejects.toBe(err);
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('data=Circular data error'));
      spy.mockRestore();
    });
  });

  describe('logging middleware', () => {
    it('logs request with query parameters', async () => {
      const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
      await request(app).get('/health?foo=bar');
      expect(spy.mock.calls.some(c => typeof c[0] === 'string' && c[0].includes('query='))).toBe(true);
      spy.mockRestore();
    });

    it('captures res.send body in log', async () => {
      const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
      await request(app).get('/health');
      const logLines = spy.mock.calls.map(c => c[0]).filter(s => typeof s === 'string');
      expect(logLines.some(l => l.includes('body='))).toBe(true);
      spy.mockRestore();
    });

    it('logs without body when response uses res.end() directly', async () => {
      const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
      // Register a route that bypasses json/send — bodyForLog stays undefined
      app.get('/_test_no_body', (_req: Request, res: Response) => {
        res.status(204).end();
      });
      await request(app).get('/_test_no_body');
      const responseLine = spy.mock.calls
        .map(c => c[0])
        .filter(s => typeof s === 'string')
        .find(l => l.includes('<-') && l.includes('/_test_no_body'));
      expect(responseLine).toBeDefined();
      // No body= in log since bodyForLog was undefined
      expect(responseLine).not.toContain('body=');
      spy.mockRestore();
    });

    it('handles non-serializable bodyForLog in finish handler', async () => {
      const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
      const circular: Record<string, unknown> = {};
      circular.self = circular;
      // Register a route that manually sets a circular object as bodyForLog
      app.get('/_test_circular', (_req: Request, res: Response) => {
        res.locals.bodyForLog = circular;
        res.status(200).end();
      });
      await request(app).get('/_test_circular');
      // Should not throw — the catch in the finish handler absorbs the error
      expect(spy).toHaveBeenCalled();
      spy.mockRestore();
    });
  });

  describe('GET /health', () => {
    it('returns { ok: true }', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ ok: true });
    });
  });

  describe('buildHeaders', () => {
    it('returns auth header with empty token when no API key', () => {
      const headers = buildHeaders();
      expect(headers['X-Auth-Token']).toBe('');
    });
  });

  describe('normalizeMatch', () => {
    it('normalizes a full match object', () => {
      const raw = {
        id: 1, utcDate: '2024-01-01T00:00:00Z', status: 'FINISHED',
        stage: 'GROUP_STAGE', group: 'Group A', matchday: 1,
        homeTeam: { name: 'Team A' }, awayTeam: { name: 'Team B' },
        score: { fullTime: { home: 2, away: 1 } },
        competition: { name: 'UEFA Champions League' },
        venue: 'Stadium X',
        referees: [{ name: 'Ref One' }, { name: 'Ref Two' }],
      };
      const result = normalizeMatch(raw);
      expect(result).toEqual({
        id: 1, utcDate: '2024-01-01T00:00:00Z', status: 'FINISHED',
        stage: 'GROUP_STAGE', group: 'Group A', matchday: 1,
        homeTeam: 'Team A', awayTeam: 'Team B',
        score: { fullTime: { home: 2, away: 1 } },
        competition: 'UEFA Champions League', venue: 'Stadium X',
        referees: ['Ref One', 'Ref Two'],
      });
    });

    it('handles null referees', () => {
      const result = normalizeMatch({
        id: 2, utcDate: '', status: 'TIMED',
        homeTeam: { name: 'A' }, awayTeam: { name: 'B' },
        score: {}, referees: null,
      });
      expect(result.referees).toEqual([]);
    });

    it('handles undefined referees', () => {
      const result = normalizeMatch({
        id: 3, utcDate: '', status: 'TIMED',
        homeTeam: { name: 'A' }, awayTeam: { name: 'B' }, score: {},
      });
      expect(result.referees).toEqual([]);
    });

    it('filters out referees with falsy names', () => {
      const result = normalizeMatch({
        id: 4, utcDate: '', status: 'TIMED',
        homeTeam: { name: 'A' }, awayTeam: { name: 'B' }, score: {},
        referees: [{ name: 'Good Ref' }, { name: '' }, { name: null }, {}],
      });
      expect(result.referees).toEqual(['Good Ref']);
    });

    it('defaults competition name when missing', () => {
      const result = normalizeMatch({
        id: 5, utcDate: '', status: 'TIMED',
        homeTeam: { name: 'A' }, awayTeam: { name: 'B' }, score: {},
      });
      expect(result.competition).toBe('UEFA Champions League');
    });

    it('uses competition name when present', () => {
      const result = normalizeMatch({
        id: 6, utcDate: '', status: 'TIMED',
        homeTeam: { name: 'A' }, awayTeam: { name: 'B' }, score: {},
        competition: { name: 'Europa League' },
      });
      expect(result.competition).toBe('Europa League');
    });
  });

  describe('GET /api/live (demo mode, no API_TOKEN)', () => {
    it('returns demo data', async () => {
      const res = await request(app).get('/api/live');
      expect(res.status).toBe(200);
      expect(res.body.demo).toBe(true);
      expect(res.body.matches.length).toBe(1);
      expect(res.body.matches[0].homeTeam).toBe('Demo FC');
      expect(res.body.count).toBe(1);
      expect(res.body.fetchedAt).toBeTruthy();
    });
  });

  describe('GET /api/matches (demo mode)', () => {
    it('returns demo data', async () => {
      const res = await request(app).get('/api/matches');
      expect(res.status).toBe(200);
      expect(res.body.demo).toBe(true);
      expect(res.body.matches[0].homeTeam).toBe('Placeholder City');
    });

    it('returns demo data with custom date', async () => {
      const res = await request(app).get('/api/matches?date=2024-12-25');
      expect(res.status).toBe(200);
      expect(res.body.date).toBe('2024-12-25');
    });
  });

  describe('with API token', () => {
    beforeEach(async () => {
      vi.resetModules();
      process.env.FOOTBALL_DATA_API_KEY = 'test-token';
      axiosMock = (await import('axios')).default;
      const server = await import('./server');
      app = server.app;
      normalizeMatch = server.normalizeMatch;
      buildHeaders = server.buildHeaders;
    });

    afterEach(() => {
      delete process.env.FOOTBALL_DATA_API_KEY;
    });

    it('buildHeaders returns the token', () => {
      expect(buildHeaders()['X-Auth-Token']).toBe('test-token');
    });

    it('GET /api/live proxies to football-data.org', async () => {
      axiosMock.get.mockResolvedValue({
        data: {
          matches: [{
            id: 100, utcDate: '2024-09-17T20:00:00Z', status: 'LIVE',
            stage: 'GROUP_STAGE',
            homeTeam: { name: 'Barcelona' }, awayTeam: { name: 'Milan' },
            score: { fullTime: { home: 1, away: 0 } },
            competition: { name: 'UEFA Champions League' },
          }],
        },
      });
      const res = await request(app).get('/api/live');
      expect(res.status).toBe(200);
      expect(res.body.matches[0].homeTeam).toBe('Barcelona');
      expect(res.body.count).toBe(1);
    });

    it('GET /api/live returns empty matches when API returns none', async () => {
      axiosMock.get.mockResolvedValue({ data: { matches: [] } });
      const res = await request(app).get('/api/live');
      expect(res.status).toBe(200);
      expect(res.body.matches).toEqual([]);
      expect(res.body.count).toBe(0);
    });

    it('GET /api/live returns empty when data.matches undefined', async () => {
      axiosMock.get.mockResolvedValue({ data: {} });
      const res = await request(app).get('/api/live');
      expect(res.status).toBe(200);
      expect(res.body.matches).toEqual([]);
    });

    it('GET /api/live returns error status on axios error', async () => {
      axiosMock.get.mockRejectedValue({
        response: { status: 503, data: { message: 'Service Unavailable' } },
        message: 'Request failed',
      });
      const res = await request(app).get('/api/live');
      expect(res.status).toBe(503);
      expect(res.body.error).toBe('Failed to fetch live matches');
    });

    it('GET /api/live returns 500 when error has no response', async () => {
      axiosMock.get.mockRejectedValue({ message: 'Network Error' });
      const res = await request(app).get('/api/live');
      expect(res.status).toBe(500);
      expect(res.body.details).toBe('Network Error');
    });

    it('GET /api/matches proxies with date', async () => {
      axiosMock.get.mockResolvedValue({
        data: {
          matches: [{
            id: 200, utcDate: '2024-12-25T18:00:00Z', status: 'TIMED',
            homeTeam: { name: 'PSG' }, awayTeam: { name: 'Liverpool' },
            score: { fullTime: { home: null, away: null } },
          }],
        },
      });
      const res = await request(app).get('/api/matches?date=2024-12-25');
      expect(res.status).toBe(200);
      expect(res.body.matches[0].homeTeam).toBe('PSG');
      expect(axiosMock.get).toHaveBeenCalledWith(
        expect.stringContaining('/competitions/CL/matches'),
        expect.objectContaining({ params: { dateFrom: '2024-12-25', dateTo: '2024-12-25' } }),
      );
    });

    it('GET /api/matches uses today as default', async () => {
      axiosMock.get.mockResolvedValue({ data: { matches: [] } });
      await request(app).get('/api/matches');
      const today = new Date().toISOString().slice(0, 10);
      expect(axiosMock.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ params: { dateFrom: today, dateTo: today } }),
      );
    });

    it('GET /api/matches returns empty when data.matches undefined', async () => {
      axiosMock.get.mockResolvedValue({ data: {} });
      const res = await request(app).get('/api/matches');
      expect(res.status).toBe(200);
      expect(res.body.matches).toEqual([]);
    });

    it('GET /api/matches returns error on axios failure', async () => {
      axiosMock.get.mockRejectedValue({
        response: { status: 429, data: { message: 'Rate limit exceeded' } },
        message: 'Request failed',
      });
      const res = await request(app).get('/api/matches');
      expect(res.status).toBe(429);
      expect(res.body.error).toBe('Failed to fetch matches');
    });

    it('GET /api/matches returns 500 when error has no response', async () => {
      axiosMock.get.mockRejectedValue({ message: 'Timeout' });
      const res = await request(app).get('/api/matches');
      expect(res.status).toBe(500);
      expect(res.body.details).toBe('Timeout');
    });
  });

  describe('response headers', () => {
    it('sets cache-control headers', async () => {
      const res = await request(app).get('/health');
      expect(res.headers['cache-control']).toBe('no-store, no-cache, must-revalidate, proxy-revalidate');
      expect(res.headers['pragma']).toBe('no-cache');
      expect(res.headers['expires']).toBe('0');
    });

    it('sets CORS headers', async () => {
      const res = await request(app).get('/health');
      expect(res.headers['access-control-allow-origin']).toBe('*');
    });
  });
});
