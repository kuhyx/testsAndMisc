import { useCallback, useSyncExternalStore } from "react";
import { normalize } from "./paths.ts";

/**
 * Hash-based routing: the current directory lives in the URL hash (e.g.
 * `#/Media/2026/07`). Using the hash keeps the HTTP path at "/", so dufs
 * `render-spa` always serves the app shell and deep links never 404.
 */
function readHash(): string {
  const raw = window.location.hash.replace(/^#/, "");
  return normalize(raw === "" ? "/" : raw);
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => {
    window.removeEventListener("hashchange", onChange);
  };
}

export function useHashPath(): readonly [string, (path: string) => void] {
  const path = useSyncExternalStore(subscribe, readHash, () => "/");
  const navigate = useCallback((next: string) => {
    window.location.hash = normalize(next);
  }, []);
  return [path, navigate];
}
