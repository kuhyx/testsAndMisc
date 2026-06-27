import { describe, it, expect, vi, beforeEach } from "vitest";
import { uploadFiles } from "./uploadFiles";

describe("uploadFiles", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("uploads multiple files sequentially and returns results", async () => {
    const mockResult = {
      filename: "stored.txt",
      originalname: "test.txt",
      size: 5,
      savedAt: "2024-01-01",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResult),
      }),
    );

    const files = [
      new File(["hello"], "a.txt"),
      new File(["world"], "b.txt"),
    ];
    const results = await uploadFiles(files);

    expect(fetch).toHaveBeenCalledTimes(2);
    expect(results).toHaveLength(2);
    expect(results[0]).toEqual(mockResult);
  });

  it("throws when server returns non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        statusText: "Bad Request",
      }),
    );

    const files = [new File(["x"], "fail.txt")];
    await expect(uploadFiles(files)).rejects.toThrow(
      "Upload failed for fail.txt: Bad Request",
    );
  });

  it("returns empty array for empty input", async () => {
    vi.stubGlobal("fetch", vi.fn());
    const results = await uploadFiles([]);
    expect(results).toEqual([]);
    expect(fetch).not.toHaveBeenCalled();
  });
});
