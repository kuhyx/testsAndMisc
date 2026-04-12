import { describe, it, expect, vi, afterEach } from 'vitest';
import { fetchJson } from './fetchJson';

describe('fetchJson', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('returns parsed JSON on success', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: 42 }),
    });
    const result = await fetchJson<{ data: number }>('http://example.com/api');
    expect(result).toEqual({ data: 42 });
    expect(globalThis.fetch).toHaveBeenCalledWith('http://example.com/api', { cache: 'no-store' });
  });

  it('passes through custom init options', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    });
    await fetchJson('http://example.com/api', { headers: { 'X-Custom': 'yes' } });
    expect(globalThis.fetch).toHaveBeenCalledWith('http://example.com/api', {
      cache: 'no-store',
      headers: { 'X-Custom': 'yes' },
    });
  });

  it('throws with status and parsed body on non-ok response', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve(JSON.stringify({ message: 'Not found' })),
    });
    try {
      await fetchJson('http://example.com/api');
      expect.fail('should have thrown');
    } catch (err: unknown) {
      const e = err as { message: string; status: number; body: unknown };
      expect(e.message).toBe('HTTP 404');
      expect(e.status).toBe(404);
      expect(e.body).toEqual({ message: 'Not found' });
    }
  });

  it('handles empty text body on error', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve(''),
    });
    try {
      await fetchJson('http://example.com/api');
      expect.fail('should have thrown');
    } catch (err: unknown) {
      const e = err as { message: string; status: number; body: unknown };
      expect(e.status).toBe(500);
      expect(e.body).toBeNull();
    }
  });

  it('handles non-JSON text body on error', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      text: () => Promise.resolve('Bad Gateway'),
    });
    try {
      await fetchJson('http://example.com/api');
      expect.fail('should have thrown');
    } catch (err: unknown) {
      const e = err as { message: string; status: number; body: unknown };
      expect(e.status).toBe(502);
      expect(e.body).toBeNull();
    }
  });

  it('parses waitSec from 429 response with details.message', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      text: () => Promise.resolve(JSON.stringify({
        details: { message: 'You reached your request limit. Wait 56 seconds.' },
      })),
    });
    try {
      await fetchJson('http://example.com/api');
      expect.fail('should have thrown');
    } catch (err: unknown) {
      const e = err as { waitSec?: number; status: number };
      expect(e.status).toBe(429);
      expect(e.waitSec).toBe(56);
    }
  });

  it('parses waitSec from 429 response with top-level message', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      text: () => Promise.resolve(JSON.stringify({
        message: 'Wait 30 seconds please.',
      })),
    });
    try {
      await fetchJson('http://example.com/api');
      expect.fail('should have thrown');
    } catch (err: unknown) {
      const e = err as { waitSec?: number; status: number };
      expect(e.status).toBe(429);
      expect(e.waitSec).toBe(30);
    }
  });

  it('parses waitSec from 429 response with error field', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      text: () => Promise.resolve(JSON.stringify({
        error: 'Rate limited. Wait 10 second.',
      })),
    });
    try {
      await fetchJson('http://example.com/api');
      expect.fail('should have thrown');
    } catch (err: unknown) {
      const e = err as { waitSec?: number; status: number };
      expect(e.status).toBe(429);
      expect(e.waitSec).toBe(10);
    }
  });

  it('does not set waitSec on 429 when no seconds in message', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      text: () => Promise.resolve(JSON.stringify({
        message: 'Too many requests',
      })),
    });
    try {
      await fetchJson('http://example.com/api');
      expect.fail('should have thrown');
    } catch (err: unknown) {
      const e = err as { waitSec?: number; status: number };
      expect(e.status).toBe(429);
      expect(e.waitSec).toBeUndefined();
    }
  });

  it('handles 429 with null body', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      text: () => Promise.resolve(''),
    });
    try {
      await fetchJson('http://example.com/api');
      expect.fail('should have thrown');
    } catch (err: unknown) {
      const e = err as { waitSec?: number; status: number };
      expect(e.status).toBe(429);
      expect(e.waitSec).toBeUndefined();
    }
  });
});
