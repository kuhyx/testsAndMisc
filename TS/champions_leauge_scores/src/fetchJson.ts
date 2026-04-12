export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { cache: 'no-store', ...init });
  if (!res.ok) {
    const text = await res.text();
    let body: unknown = null;
    try { body = text ? JSON.parse(text) : null; } catch { /* noop */ }
    const err: { message: string; status: number; body: unknown; waitSec?: number } = { message: `HTTP ${res.status}`, status: res.status, body };
    if (res.status === 429) {
      const details = body as Record<string, unknown> | null;
      const msg: string | undefined = (details?.message as string) || (details?.error as string) || (details?.details as Record<string, unknown>)?.message as string | undefined;
      const m = msg ? msg.match(/(\d+)\s*seconds?/) : null;
      if (m) err.waitSec = Number(m[1]);
    }
    throw err;
  }
  return res.json();
}
