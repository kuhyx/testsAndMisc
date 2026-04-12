import { useEffect, useRef, useState } from 'react';

export function useBackoffUntilSuccess<T>(fn: () => Promise<T>, opts?: { baseDelaySec?: number; maxDelaySec?: number; factor?: number }) {
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
      tTickRef.current = window.setInterval(() => {
        setRetryInSec(v => Math.max(0, Number(v) - 1));
      }, 1000);
      tRetryRef.current = window.setTimeout(() => {
        clearTimers();
        run();
      }, clamped * 1000);
    };
    const run = async () => {
      if (inFlightRef.current) return;
      try {
        inFlightRef.current = true;
        setLoading(true);
        const result = await fn();
        if (!mounted) return;
        clearTimers();
        setData(result);
        setError(null);
      } catch (e: unknown) {
        if (!mounted) return;
        const httpErr = e as { status?: number; waitSec?: number; message?: string };
        if (httpErr?.status === 429) {
          const suggested = Number(httpErr?.waitSec) || delayRef.current;
          const next = Math.min(max, Math.max(base, suggested));
          delayRef.current = Math.min(max, Math.ceil(next * factor));
          setError(`Rate limited. Retrying in ${next}s...`);
          scheduleRetry(next);
          return;
        }
        setError(httpErr?.message || 'Failed to fetch');
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
