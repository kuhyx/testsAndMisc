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
  STORAGE_KEY,
  browserClipboard,
  browserSaveFile,
  browserUrlHash,
  decodeInventoryHash,
  encodeInventoryHash,
  fromBase64Url,
  loadInventory,
  parseInventory,
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
function memoryStorage(initial?: string): Pick<Storage, "getItem"> {
  return { getItem: (key: string) => (key === STORAGE_KEY ? (initial ?? null) : null) };
}

describe("parseInventory", () => {
  it("keeps a clean payload intact", () => {
    const input = { diceCounts: { weighted: 3 }, badgeIds: ["tin_might"] };
    expect(parseInventory(input)).toEqual({
      inventory: { diceCounts: { weighted: 3 }, badgeIds: ["tin_might"] },
      dropped: [],
    });
  });

  it("rejects anything that is not an object outright", () => {
    // Nothing salvageable, so this is the one case that fails whole.
    for (const value of [42, null, "nope", undefined]) {
      expect(parseInventory(value)).toEqual({ inventory: EMPTY, dropped: ["Not an inventory."] });
    }
  });

  it("notes a missing or mistyped diceCounts", () => {
    const result = parseInventory({ diceCounts: "nope", badgeIds: [] });
    expect(result.inventory.diceCounts).toEqual({});
    expect(result.dropped).toContain("No dice in this file.");
  });

  it("notes a null diceCounts", () => {
    const result = parseInventory({ diceCounts: null, badgeIds: [] });
    expect(result.dropped).toContain("No dice in this file.");
  });

  it("notes a missing or mistyped badgeIds", () => {
    const result = parseInventory({ diceCounts: {}, badgeIds: "nope" });
    expect(result.inventory.badgeIds).toEqual([]);
    expect(result.dropped).toContain("No badges in this file.");
  });

  it("drops a die it does not recognise", () => {
    const result = parseInventory({ diceCounts: { not_a_die: 2 }, badgeIds: [] });
    expect(result.inventory.diceCounts).toEqual({});
    expect(result.dropped).toContain("Unknown die “not_a_die”.");
  });

  it("drops a non-integer count", () => {
    const result = parseInventory({ diceCounts: { weighted: 1.5 }, badgeIds: [] });
    expect(result.inventory.diceCounts).toEqual({});
    expect(result.dropped).toContain("Invalid count for “weighted”.");
  });

  it("drops a count that is not a number at all", () => {
    const result = parseInventory({ diceCounts: { weighted: "three" }, badgeIds: [] });
    expect(result.dropped).toContain("Invalid count for “weighted”.");
  });

  it("drops a negative count", () => {
    const result = parseInventory({ diceCounts: { weighted: -1 }, badgeIds: [] });
    expect(result.dropped).toContain("Invalid count for “weighted”.");
  });

  it("drops a count above the per-die maximum", () => {
    const result = parseInventory({ diceCounts: { weighted: 7 }, badgeIds: [] });
    expect(result.inventory.diceCounts).toEqual({});
    expect(result.dropped).toContain("Count for “weighted” exceeds 6.");
  });

  it("drops a zero count without complaining about it", () => {
    // The app never writes zeros, so a zero is tidy-up, not corruption.
    const result = parseInventory({ diceCounts: { weighted: 0 }, badgeIds: [] });
    expect(result.inventory.diceCounts).toEqual({});
    expect(result.dropped).toEqual([]);
  });

  it("drops a badge it does not recognise", () => {
    const result = parseInventory({ diceCounts: {}, badgeIds: ["not_a_badge"] });
    expect(result.inventory.badgeIds).toEqual([]);
    expect(result.dropped).toContain("Unknown badge “not_a_badge”.");
  });

  it("drops a badge id that is not a string", () => {
    const result = parseInventory({ diceCounts: {}, badgeIds: [7] });
    expect(result.dropped).toContain("Unknown badge “7”.");
  });

  it("dedupes a repeated badge", () => {
    const result = parseInventory({ diceCounts: {}, badgeIds: ["tin_might", "tin_might"] });
    expect(result.inventory.badgeIds).toEqual(["tin_might"]);
    expect(result.dropped).toContain("Duplicate badge “tin_might”.");
  });

  it("keeps the valid entries alongside the invalid ones", () => {
    // This is the whole reason for sanitising instead of rejecting: one bad id
    // must not cost you the rest of an inventory you just pasted.
    const result = parseInventory({
      diceCounts: { weighted: 2, not_a_die: 1, lucky: 99 },
      badgeIds: ["tin_might", "not_a_badge"],
    });
    expect(result.inventory.diceCounts).toEqual({ weighted: 2 });
    expect(result.inventory.badgeIds).toEqual(["tin_might"]);
    expect(result.dropped).toHaveLength(3);
  });
});

describe("parseInventoryJson", () => {
  it("reports unparsable JSON", () => {
    expect(parseInventoryJson("{not json")).toEqual({
      inventory: EMPTY,
      dropped: ["Not valid JSON."],
    });
  });

  it("parses valid JSON through the validator", () => {
    const result = parseInventoryJson('{"diceCounts":{"weighted":1},"badgeIds":[]}');
    expect(result.inventory.diceCounts).toEqual({ weighted: 1 });
  });
});

describe("loadInventory", () => {
  it("starts empty when nothing is saved", () => {
    expect(loadInventory(memoryStorage()).inventory).toEqual(EMPTY);
  });

  it("restores a saved inventory", () => {
    const saved = JSON.stringify({ diceCounts: { weighted: 3 }, badgeIds: ["tin_might"] });
    expect(loadInventory(memoryStorage(saved)).inventory).toEqual({
      diceCounts: { weighted: 3 },
      badgeIds: ["tin_might"],
    });
  });

  it("survives a corrupt entry rather than taking the page down with it", () => {
    expect(loadInventory(memoryStorage("{not json")).inventory).toEqual(EMPTY);
  });

  it("survives an entry of the wrong shape", () => {
    expect(loadInventory(memoryStorage("42")).inventory).toEqual(EMPTY);
    expect(loadInventory(memoryStorage("null")).inventory).toEqual(EMPTY);
    expect(
      loadInventory(memoryStorage('{"diceCounts":"nope","badgeIds":"nope"}')).inventory,
    ).toEqual(EMPTY);
  });
});

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
