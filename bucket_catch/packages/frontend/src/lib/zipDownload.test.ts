import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { MockInstance } from "vitest";
import { zipDownload } from "./zipDownload";

describe("zipDownload", () => {
  let createUrlSpy: MockInstance<typeof URL.createObjectURL>;
  let revokeUrlSpy: MockInstance<typeof URL.revokeObjectURL>;
  let clickSpy: MockInstance<typeof HTMLAnchorElement.prototype.click>;

  beforeEach(() => {
    createUrlSpy = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:mock-url");
    revokeUrlSpy = vi
      .spyOn(URL, "revokeObjectURL")
      .mockImplementation(() => undefined);
    clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a zip blob, triggers download, and cleans up", async () => {
    const appendSpy = vi.spyOn(document.body, "appendChild");
    const removeSpy = vi.spyOn(document.body, "removeChild");

    const file = new File(["hello"], "hello.txt");
    await zipDownload([file]);

    expect(createUrlSpy).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeUrlSpy).toHaveBeenCalledWith("blob:mock-url");
    expect(appendSpy).toHaveBeenCalled();
    expect(removeSpy).toHaveBeenCalled();
  });

  it("sets download attribute and href on the anchor", async () => {
    const anchors: HTMLAnchorElement[] = [];
    // Bound before the spy replaces it, so the implementation below can build
    // a real element without recursing into its own mock.
    const realCreateElement = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = realCreateElement(tag);
      if (el instanceof HTMLAnchorElement) anchors.push(el);
      return el;
    });
    // Restore after spy above since we used bind trick. That discards the
    // handles from beforeEach, so re-spy and keep the new ones.
    vi.restoreAllMocks();
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock-url");
    const localRevokeSpy = vi
      .spyOn(URL, "revokeObjectURL")
      .mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
      () => undefined,
    );

    const file = new File(["x"], "data.bin");
    await zipDownload([file]);

    expect(localRevokeSpy).toHaveBeenCalledWith("blob:mock-url");
  });

  it("works with multiple files", async () => {
    const files = [
      new File(["a"], "a.txt"),
      new File(["b"], "b.txt"),
      new File(["c"], "c.png", { type: "image/png" }),
    ];
    await expect(zipDownload(files)).resolves.toBeUndefined();
    expect(createUrlSpy).toHaveBeenCalledTimes(1);
    expect(revokeUrlSpy).toHaveBeenCalledTimes(1);
  });
});
