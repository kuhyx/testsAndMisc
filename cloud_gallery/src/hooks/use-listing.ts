import { useCallback, useEffect, useState } from "react";
import type { DufsClient } from "../api/dufs-client.ts";
import type { DirEntry } from "../api/types.ts";

/** Names the app owns in the cloud root — hidden from the browsing grid. */
const APP_FILES = new Set([
  "index.html",
  "assets",
  "favicon.ico",
  "vite.svg",
  ".thumbs",
  "_thumbs",
]);

export interface Listing {
  readonly entries: readonly DirEntry[];
  readonly loading: boolean;
  readonly error: string | null;
  readonly reload: () => void;
}

interface Loaded {
  readonly path: string;
  readonly entries: readonly DirEntry[];
  readonly error: string | null;
}

export function useListing(client: DufsClient, path: string): Listing {
  const [loaded, setLoaded] = useState<Loaded>({
    path: "",
    entries: [],
    error: null,
  });
  const [nonce, setNonce] = useState(0);
  const reload = useCallback(() => {
    setNonce((n) => n + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    client
      .list(path)
      .then((all) => {
        if (cancelled) return;
        setLoaded({
          path,
          entries: all.filter((e) => !APP_FILES.has(e.name)),
          error: null,
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoaded({
          path,
          entries: [],
          error: err instanceof Error ? err.message : String(err),
        });
      });
    return () => {
      cancelled = true;
    };
  }, [client, path, nonce]);

  // Loading is derived (no synchronous setState in the effect): we are loading
  // whenever the last completed load is for a different path than the current.
  const loading = loaded.path !== path;
  return {
    entries: loading ? [] : loaded.entries,
    loading,
    error: loading ? null : loaded.error,
    reload,
  };
}
