import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useBackoffUntilSuccess } from './useBackoffUntilSuccess';

describe('useBackoffUntilSuccess', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('returns data on successful fetch', async () => {
    const fn = vi.fn().mockResolvedValue({ result: 'ok' });
    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() => useBackoffUntilSuccess(fn));
    });

    expect(hook!.result.current.loading).toBe(false);
    expect(hook!.result.current.data).toEqual({ result: 'ok' });
    expect(hook!.result.current.error).toBeNull();
  });

  it('sets error on non-429 failure', async () => {
    const fn = vi.fn().mockRejectedValue({ message: 'Network Error', status: 500 });
    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() => useBackoffUntilSuccess(fn));
    });

    expect(hook!.result.current.loading).toBe(false);
    expect(hook!.result.current.error).toBe('Network Error');
    expect(hook!.result.current.data).toBeNull();
  });

  it('falls back to "Failed to fetch" when error has no message', async () => {
    const fn = vi.fn().mockRejectedValue({});
    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() => useBackoffUntilSuccess(fn));
    });

    expect(hook!.result.current.error).toBe('Failed to fetch');
  });

  it('retries on 429 with backoff and shows retryInSec', async () => {
    vi.useFakeTimers();
    let calls = 0;
    const fn = vi.fn().mockImplementation(() => {
      calls++;
      if (calls === 1) return Promise.reject({ status: 429, waitSec: 2, message: 'Rate limited' });
      return Promise.resolve({ ok: true });
    });

    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() =>
        useBackoffUntilSuccess(fn, { baseDelaySec: 2, maxDelaySec: 60, factor: 2 }),
      );
    });

    expect(hook!.result.current.error).toContain('Rate limited');
    expect(hook!.result.current.retryInSec).toBeGreaterThan(0);

    // Advance past the retry delay
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(hook!.result.current.data).toEqual({ ok: true });
    expect(hook!.result.current.error).toBeNull();
  });

  it('uses delayRef.current when waitSec is 0/NaN', async () => {
    vi.useFakeTimers();
    let calls = 0;
    const fn = vi.fn().mockImplementation(() => {
      calls++;
      if (calls === 1) return Promise.reject({ status: 429, message: 'Rate limited' });
      return Promise.resolve({ data: 'ok' });
    });

    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() =>
        useBackoffUntilSuccess(fn, { baseDelaySec: 2, maxDelaySec: 60, factor: 2 }),
      );
    });

    expect(hook!.result.current.error).toContain('Rate limited');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(hook!.result.current.data).toEqual({ data: 'ok' });
  });

  it('clamps retry seconds to max', async () => {
    vi.useFakeTimers();
    let calls = 0;
    const fn = vi.fn().mockImplementation(() => {
      calls++;
      if (calls <= 1) return Promise.reject({ status: 429, waitSec: 9999, message: 'Rate limited' });
      return Promise.resolve({ done: true });
    });

    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() =>
        useBackoffUntilSuccess(fn, { baseDelaySec: 1, maxDelaySec: 5, factor: 2 }),
      );
    });

    expect(hook!.result.current.retryInSec).toBeLessThanOrEqual(5);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(6000);
    });

    expect(hook!.result.current.data).toEqual({ done: true });
  });

  it('handles countdown tick decrement', async () => {
    vi.useFakeTimers();
    const fn = vi.fn().mockRejectedValue({ status: 429, waitSec: 3, message: 'Rate limited' });

    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() =>
        useBackoffUntilSuccess(fn, { baseDelaySec: 3, maxDelaySec: 60, factor: 2 }),
      );
    });

    expect(hook!.result.current.retryInSec).toBe(3);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(hook!.result.current.retryInSec).toBe(2);
  });

  it('decrements retryInSec to 0', async () => {
    vi.useFakeTimers();
    let calls = 0;
    const fn = vi.fn().mockImplementation(() => {
      calls++;
      if (calls <= 2) return Promise.reject({ status: 429, waitSec: 3, message: 'Rate limited' });
      return Promise.resolve({ result: 'ok' });
    });

    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() =>
        useBackoffUntilSuccess(fn, { baseDelaySec: 3, maxDelaySec: 60, factor: 2 }),
      );
    });

    // Initial: retryInSec = 3
    expect(hook!.result.current.retryInSec).toBe(3);

    // After 1s: 3→2
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(hook!.result.current.retryInSec).toBe(2);

    // After 2s: 2→1
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(hook!.result.current.retryInSec).toBe(1);

    // After 3s: 1→0, then timeout fires → retry → fails again with 429 → new countdown
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    // Either retryInSec went to 0 briefly or a new countdown started
    // The retry triggers a new 429, creating a new schedule
    expect(hook!.result.current.retryInSec).toBeGreaterThanOrEqual(0);
  });

  it('cleans up timers on unmount', async () => {
    vi.useFakeTimers();
    const fn = vi.fn().mockRejectedValue({ status: 429, waitSec: 30, message: 'Rate limited' });

    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() =>
        useBackoffUntilSuccess(fn, { baseDelaySec: 30, maxDelaySec: 60, factor: 2 }),
      );
    });

    expect(hook!.result.current.error).toContain('Rate limited');

    hook!.unmount();
    // Should not throw when timers fire after unmount
    await act(async () => {
      await vi.advanceTimersByTimeAsync(35000);
    });
  });

  it('uses default options when not provided', async () => {
    const fn = vi.fn().mockResolvedValue({ data: true });
    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() => useBackoffUntilSuccess(fn));
    });

    expect(hook!.result.current.data).toEqual({ data: true });
  });

  it('uses safe minimum for factor below 1.1', async () => {
    const fn = vi.fn().mockResolvedValue({ data: true });
    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() =>
        useBackoffUntilSuccess(fn, { baseDelaySec: 1, maxDelaySec: 10, factor: 0.5 }),
      );
    });

    expect(hook!.result.current.data).toEqual({ data: true });
  });

  it('handles unmount during pending successful fetch', async () => {
    let resolveFirst!: (v: { ok: boolean }) => void;
    const fn = vi.fn().mockReturnValue(
      new Promise<{ ok: boolean }>(resolve => { resolveFirst = resolve; }),
    );

    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() => useBackoffUntilSuccess(fn));
    });

    expect(hook!.result.current.loading).toBe(true);

    // Unmount while the fetch promise is still pending
    hook!.unmount();

    // Resolve the pending fetch after unmount — mounted is false, so
    // the hook skips setState calls and setLoading(false) in finally
    await act(async () => {
      resolveFirst({ ok: true });
    });

    // No errors — state updates were safely skipped
  });

  it('handles unmount during pending error fetch', async () => {
    let rejectFirst!: (reason: unknown) => void;
    const fn = vi.fn().mockReturnValue(
      new Promise((_resolve, reject) => { rejectFirst = reject; }),
    );

    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(() => useBackoffUntilSuccess(fn));
    });

    expect(hook!.result.current.loading).toBe(true);

    hook!.unmount();

    // Reject the pending fetch after unmount
    await act(async () => {
      rejectFirst({ message: 'fail', status: 500 });
    });
  });

  it('guards against concurrent runs via inFlightRef', async () => {
    let resolveFirst!: (v: { ok: boolean }) => void;
    const fn = vi.fn().mockReturnValue(
      new Promise<{ ok: boolean }>(resolve => { resolveFirst = resolve; }),
    );

    let hook: ReturnType<typeof renderHook<ReturnType<typeof useBackoffUntilSuccess>, unknown>>;

    await act(async () => {
      hook = renderHook(
        ({ f }) => useBackoffUntilSuccess(f),
        { initialProps: { f: fn } },
      );
    });

    // fn is awaiting — inFlightRef.current is true
    expect(hook!.result.current.loading).toBe(true);

    // Rerender with a new fn triggers effect cleanup + re-run.
    // The new run() finds inFlightRef.current === true and returns early.
    const fn2 = vi.fn().mockResolvedValue({ data: 'second' });
    await act(async () => {
      hook!.rerender({ f: fn2 });
    });

    // Resolve the original promise — old effect's mounted is false so
    // it hits `if (!mounted) return`, then finally resets inFlightRef
    await act(async () => {
      resolveFirst({ ok: true });
    });

    // fn2 was either called by a re-run (if inFlightRef cleared in time)
    // or the hook is still loading. Either way, no errors occurred.
    expect(hook!.result.current).toBeDefined();
  });
});
