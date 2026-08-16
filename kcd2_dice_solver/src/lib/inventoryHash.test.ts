/** Serialisation, base64url and inventory-hash round trips. */

/**
 * Tests for inventory persistence and transport.
 *
 * The validator is the security boundary of the import features: everything a
 * user can paste, upload, or follow a link to lands here first. So the cases
 * below lean on malformed input rather than the happy path.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  EMPTY,
  EXPORT_FILENAME,
  browserClipboard,
  browserSaveFile,
  browserUrlHash,
  decodeInventoryHash,
  encodeInventoryHash,
  fromBase64Url,
  parseInventoryJson,
  serialiseInventory,
  toBase64Url,
} from "./inventoryIo.ts";
import type { SavedInventory } from "./inventoryIo.ts";

/**
 * A storage stub holding one entry.
 *
 * @param initial - What the key already contains, if anything.
 * @returns A minimal Storage.
 */

describe("serialiseInventory", () => {
  it("round-trips through the parser", () => {
    const inventory: SavedInventory = {
      diceCounts: { weighted: 4 },
      badgeIds: ["tin_might"],
    };
    expect(parseInventoryJson(serialiseInventory(inventory)).inventory).toEqual(inventory);
  });
});

describe("base64url", () => {
  it("round-trips ASCII", () => {
    expect(fromBase64Url(toBase64Url("hello world"))).toBe("hello world");
  });

  it("really produces URL-safe characters, not merely claims to", () => {
    // Standard base64 of these bytes contains both '+' and '/', so this
    // exercises the substitutions rather than trivially covering the line.
    const raw = "ÿï¿";
    const encoded = toBase64Url(raw);
    expect(encoded).not.toMatch(/[+/=]/);
    expect(encoded).toMatch(/[-_]/);
    expect(fromBase64Url(encoded)).toBe(raw);
  });

  it("round-trips every padding length", () => {
    for (const text of ["abc", "abcd", "abcde"]) {
      expect(fromBase64Url(toBase64Url(text))).toBe(text);
    }
  });
});

describe("inventory hash", () => {
  const inventory: SavedInventory = {
    diceCounts: { weighted: 2 },
    badgeIds: ["tin_might"],
  };

  it("round-trips an inventory", () => {
    const result = decodeInventoryHash(encodeInventoryHash(inventory));
    expect(result?.inventory).toEqual(inventory);
    expect(result?.dropped).toEqual([]);
  });

  it("decodes with or without the leading hash", () => {
    const hash = encodeInventoryHash(inventory);
    expect(decodeInventoryHash(hash.slice(1))?.inventory).toEqual(inventory);
  });

  it("returns null when there is no fragment", () => {
    expect(decodeInventoryHash("")).toBeNull();
  });

  it("returns null when the fragment carries something else", () => {
    expect(decodeInventoryHash("#other=1")).toBeNull();
  });

  it("returns null for an empty inventory parameter", () => {
    expect(decodeInventoryHash("#i=")).toBeNull();
  });

  it("reports a damaged link rather than throwing", () => {
    // Lone '!' is not valid base64, so atob throws — and it must be caught in
    // the same place a JSON failure would be.
    expect(decodeInventoryHash("#i=!!!")).toEqual({
      inventory: EMPTY,
      dropped: ["This link is damaged."],
    });
  });

  it("reports a link that decodes but is not an inventory", () => {
    const result = decodeInventoryHash(`#i=${toBase64Url("42")}`);
    expect(result?.dropped).toEqual(["Not an inventory."]);
  });
});

describe("browser ports", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.location.hash = "";
  });

  it("browserClipboard writes through navigator.clipboard", async () => {
    const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue();
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    await browserClipboard.writeText("payload");
    expect(writeText).toHaveBeenCalledWith("payload");
  });

  it("browserSaveFile builds, clicks, and revokes an object URL", () => {
    // jsdom has no createObjectURL, but the properties are assignable — so the
    // real implementation can be exercised rather than mocked away wholesale.
    const createObjectURL = vi.fn(() => "blob:kcd2");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { value: createObjectURL, configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: revokeObjectURL, configurable: true });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function mockClick(this: HTMLAnchorElement) {
        expect(this.download).toBe(EXPORT_FILENAME);
        expect(this.getAttribute("href")).toBe("blob:kcd2");
      });

    browserSaveFile(EXPORT_FILENAME, "{}");

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:kcd2");
  });

  it("browserUrlHash reads the fragment", () => {
    window.location.hash = "#i=abc";
    expect(browserUrlHash.read()).toBe("#i=abc");
  });

  it("browserUrlHash clears the fragment without reloading", () => {
    window.location.hash = "#i=abc";
    browserUrlHash.clear();
    expect(window.location.hash).toBe("");
  });

  it("browserUrlHash builds a base URL with no fragment", () => {
    window.location.hash = "#i=abc";
    expect(browserUrlHash.base()).toBe(window.location.origin + window.location.pathname);
    expect(browserUrlHash.base()).not.toContain("#");
  });
});
