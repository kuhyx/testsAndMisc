import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useListing } from "./use-listing.ts";
import type { DufsClient } from "../api/dufs-client.ts";
import type { DirEntry } from "../api/types.ts";

function entry(name: string, kind: "dir" | "file"): DirEntry {
  return { name, path: `/${name}`, kind, size: 0, mtimeMs: 0 };
}

function mkClient(list: DufsClient["list"]): DufsClient {
  return {
    list,
    fileUrl: (p: string) => p,
    thumbUrl: (p: string) => p,
    upload: vi.fn(),
    remove: vi.fn(),
    readText: vi.fn(),
    writeText: vi.fn(),
  };
}

describe("useListing", () => {
  it("loads entries and hides app-owned files", async () => {
    const client = mkClient(() =>
      Promise.resolve([
        entry("index.html", "file"),
        entry(".thumbs", "dir"),
        entry("real.jpg", "file"),
      ]),
    );
    const { result } = renderHook(() => useListing(client, "/"));
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.entries.map((e) => e.name)).toEqual(["real.jpg"]);
    expect(result.current.error).toBeNull();
  });

  it("exposes an Error message", async () => {
    const client = mkClient(() => Promise.reject(new Error("boom")));
    const { result } = renderHook(() => useListing(client, "/"));
    await waitFor(() => {
      expect(result.current.error).toBe("boom");
    });
  });

  it("stringifies a non-Error rejection", async () => {
    // eslint-disable-next-line @typescript-eslint/prefer-promise-reject-errors
    const client = mkClient(() => Promise.reject("weird"));
    const { result } = renderHook(() => useListing(client, "/"));
    await waitFor(() => {
      expect(result.current.error).toBe("weird");
    });
  });

  it("reload re-fetches the current path", async () => {
    const list = vi.fn(() => Promise.resolve([entry("a.jpg", "file")]));
    const client = mkClient(list);
    const { result } = renderHook(() => useListing(client, "/"));
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    act(() => {
      result.current.reload();
    });
    await waitFor(() => {
      expect(list).toHaveBeenCalledTimes(2);
    });
  });

  it("ignores a resolution that arrives after unmount", async () => {
    let settle: (v: DirEntry[]) => void = () => undefined;
    const pending = new Promise<DirEntry[]>((resolve) => {
      settle = resolve;
    });
    const client = mkClient(() => pending);
    const { unmount } = renderHook(() => useListing(client, "/"));
    unmount();
    await act(async () => {
      settle([entry("late.jpg", "file")]);
      await pending;
    });
  });

  it("ignores a rejection that arrives after unmount", async () => {
    let fail: (e: unknown) => void = () => undefined;
    const pending = new Promise<DirEntry[]>((_, reject) => {
      fail = reject;
    });
    const client = mkClient(() => pending);
    const { unmount } = renderHook(() => useListing(client, "/"));
    unmount();
    await act(async () => {
      fail(new Error("late"));
      await pending.catch(() => undefined);
    });
  });
});
