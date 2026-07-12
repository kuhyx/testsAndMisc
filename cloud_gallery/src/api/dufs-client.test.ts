import { describe, it, expect, vi } from "vitest";
import {
  createDufsClient,
  parsePropfind,
  sortEntries,
} from "./dufs-client.ts";
import type { DirEntry } from "./types.ts";

const PROPFIND_XML = `<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:">
  <D:response>
    <D:href>/Media/2026/07/</D:href>
    <D:propstat><D:prop><D:resourcetype><D:collection/></D:resourcetype></D:prop></D:propstat>
  </D:response>
  <D:response>
    <D:href>/Media/2026/07/sub/</D:href>
    <D:propstat><D:prop>
      <D:resourcetype><D:collection/></D:resourcetype>
      <D:getlastmodified>Sat, 12 Jul 2026 03:00:00 GMT</D:getlastmodified>
    </D:prop></D:propstat>
  </D:response>
  <D:response>
    <D:href>/Media/2026/07/a%20b.jpg</D:href>
    <D:propstat><D:prop>
      <D:resourcetype/>
      <D:getcontentlength>2048</D:getcontentlength>
      <D:getlastmodified>Sat, 12 Jul 2026 03:00:00 GMT</D:getlastmodified>
    </D:prop></D:propstat>
  </D:response>
  <D:response><D:href></D:href></D:response>
</D:multistatus>`;

describe("parsePropfind", () => {
  it("parses entries, skips self, decodes names, reads size/mtime", () => {
    const entries = parsePropfind(PROPFIND_XML, "/Media/2026/07");
    // self ("/Media/2026/07/") and the empty-href entry are dropped
    expect(entries.map((e) => e.name)).toEqual(["sub", "a b.jpg"]);
    const file = entries.find((e) => e.name === "a b.jpg");
    expect(file?.kind).toBe("file");
    expect(file?.size).toBe(2048);
    expect(file?.mtimeMs).toBeGreaterThan(0);
    expect(entries.find((e) => e.name === "sub")?.kind).toBe("dir");
  });
  it("handles missing size/mtime as zero", () => {
    const xml = `<D:multistatus xmlns:D="DAV:"><D:response><D:href>/x.bin</D:href><D:propstat><D:prop><D:resourcetype/></D:prop></D:propstat></D:response></D:multistatus>`;
    const [entry] = parsePropfind(xml, "/");
    expect(entry?.size).toBe(0);
    expect(entry?.mtimeMs).toBe(0);
  });
});

describe("sortEntries", () => {
  it("dirs first then case-insensitive name", () => {
    const mk = (name: string, kind: "dir" | "file"): DirEntry => ({
      name,
      path: `/${name}`,
      kind,
      size: 0,
      mtimeMs: 0,
    });
    const sorted = sortEntries([
      mk("banana.jpg", "file"),
      mk("Apple", "dir"),
      mk("apple.png", "file"),
      mk("Zeta", "dir"),
    ]);
    expect(sorted.map((e) => e.name)).toEqual([
      "Apple",
      "Zeta",
      "apple.png",
      "banana.jpg",
    ]);
  });
});

function jsonResponse(body: string, ok = true, status = 200): Response {
  return {
    ok,
    status,
    text: () => Promise.resolve(body),
  } as unknown as Response;
}

describe("createDufsClient", () => {
  it("list() PROPFINDs, sorts, and returns entries", async () => {
    const fetchImpl = vi.fn(() => Promise.resolve(jsonResponse(PROPFIND_XML)));
    const client = createDufsClient(fetchImpl as unknown as typeof fetch);
    const entries = await client.list("/Media/2026/07");
    const [url, init] = fetchImpl.mock.calls[0] ?? [];
    expect(url).toBe("/Media/2026/07");
    expect((init as RequestInit).method).toBe("PROPFIND");
    expect(entries.length).toBe(2);
  });

  it("builds file and thumbnail URLs (encoded)", () => {
    const client = createDufsClient(vi.fn() as unknown as typeof fetch);
    expect(client.fileUrl("/Media/a b.jpg")).toBe("/Media/a%20b.jpg");
    expect(client.thumbUrl("/Media/a b.jpg")).toBe(
      "/.thumbs/Media/a%20b.jpg.jpg",
    );
  });

  it("upload PUTs to dir/name, remove DELETEs, writeText PUTs, readText GETs", async () => {
    const fetchImpl = vi.fn(() => Promise.resolve(jsonResponse("content")));
    const client = createDufsClient(fetchImpl as unknown as typeof fetch);
    const file = new File(["x"], "n.txt");
    await client.upload("/dir", file);
    await client.remove("/dir/n.txt");
    await client.writeText("/dir/n.txt", "hi");
    const text = await client.readText("/dir/n.txt");
    expect(text).toBe("content");
    const methods = fetchImpl.mock.calls.map(
      (c) => (c[1] as RequestInit).method,
    );
    expect(methods).toEqual(["PUT", "DELETE", "PUT", "GET"]);
    expect(fetchImpl.mock.calls[0]?.[0]).toBe("/dir/n.txt");
  });

  it("throws on non-ok responses", async () => {
    const fetchImpl = vi.fn(() =>
      Promise.resolve(jsonResponse("", false, 404)),
    );
    const client = createDufsClient(fetchImpl as unknown as typeof fetch);
    await expect(client.remove("/nope")).rejects.toThrow("404");
  });
});
