import type { DirEntry, EntryKind } from "./types.ts";
import { basename, encodePath, joinPath, normalize } from "../lib/paths.ts";

const DAV_NS = "DAV:";

/** Client over the dufs WebDAV + HTTP API (same-origin; browser supplies auth). */
export interface DufsClient {
  /** List a directory via WebDAV PROPFIND (works under dufs `render-spa`). */
  list(dirPath: string): Promise<DirEntry[]>;
  /** Same-origin URL to fetch/stream a file's raw bytes. */
  fileUrl(path: string): string;
  /** URL of the generated thumbnail for a media entry (see generate_thumbnails.sh). */
  thumbUrl(path: string): string;
  upload(dirPath: string, file: File): Promise<void>;
  remove(path: string): Promise<void>;
  readText(path: string): Promise<string>;
  writeText(path: string, content: string): Promise<void>;
}

/** Parse a dufs PROPFIND multistatus XML body into entries under `dirPath`. */
export function parsePropfind(xml: string, dirPath: string): DirEntry[] {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  const self = normalize(dirPath);
  const responses = Array.from(doc.getElementsByTagNameNS(DAV_NS, "response"));
  const entries: DirEntry[] = [];
  for (const res of responses) {
    const hrefEl = res.getElementsByTagNameNS(DAV_NS, "href")[0];
    const rawHref = hrefEl?.textContent;
    if (rawHref === null || rawHref === undefined || rawHref === "") continue;
    // href is URL-encoded and absolute; decode and normalize.
    const path = normalize(decodeURIComponent(rawHref));
    if (path === self) continue; // skip the directory itself
    const isDir =
      res.getElementsByTagNameNS(DAV_NS, "collection").length > 0;
    const kind: EntryKind = isDir ? "dir" : "file";
    const sizeText = res
      .getElementsByTagNameNS(DAV_NS, "getcontentlength")[0]
      ?.textContent;
    const size = sizeText !== null && sizeText !== undefined ? Number(sizeText) : 0;
    const mtimeText = res
      .getElementsByTagNameNS(DAV_NS, "getlastmodified")[0]
      ?.textContent;
    const mtimeMs =
      mtimeText !== null && mtimeText !== undefined
        ? Date.parse(mtimeText) || 0
        : 0;
    entries.push({
      name: basename(path),
      path,
      kind,
      size: Number.isFinite(size) ? size : 0,
      mtimeMs,
    });
  }
  return entries;
}

/** Sort: directories first, then by name (locale, case-insensitive). */
export function sortEntries(entries: readonly DirEntry[]): DirEntry[] {
  return [...entries].sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  });
}

export function createDufsClient(fetchImpl: typeof fetch = fetch): DufsClient {
  async function request(path: string, init: RequestInit): Promise<Response> {
    const res = await fetchImpl(encodePath(path), {
      credentials: "same-origin",
      ...init,
    });
    if (!res.ok) {
      throw new Error(`${init.method ?? "GET"} ${path} → ${res.status}`);
    }
    return res;
  }

  return {
    async list(dirPath) {
      const res = await request(dirPath, {
        method: "PROPFIND",
        headers: { Depth: "1" },
      });
      return sortEntries(parsePropfind(await res.text(), dirPath));
    },
    fileUrl(path) {
      return encodePath(path);
    },
    thumbUrl(path) {
      return encodePath(`/.thumbs${normalize(path)}.jpg`);
    },
    async upload(dirPath, file) {
      await request(joinPath(dirPath, file.name), {
        method: "PUT",
        body: file,
      });
    },
    async remove(path) {
      await request(path, { method: "DELETE" });
    },
    async readText(path) {
      return (await request(path, { method: "GET" })).text();
    },
    async writeText(path, content) {
      await request(path, { method: "PUT", body: content });
    },
  };
}
