/**
 * Reading and writing an inventory: localStorage, a JSON file, the clipboard,
 * and a shareable link.
 *
 * All four entry points funnel through one validator. That is the point of the
 * module — a payload typed by hand, exported from an older build, or pasted
 * from a link gets exactly the same treatment as one the app wrote itself.
 *
 * The three `browser*` ports at the bottom exist because `navigator.clipboard`,
 * `URL.createObjectURL` and `location`/`history` are either absent or leaky
 * under jsdom. Injecting them keeps the components testable without sprinkling
 * optional chaining through code paths that would then never be exercised.
 */

import { BADGES_BY_ID } from "../data/badges.ts";
import { DICE_BY_ID, MAX_PER_DIE } from "../data/dice.ts";

/** localStorage key for the saved inventory. */
export const STORAGE_KEY = "kcd2-dice-solver.inventory";

/** Fragment parameter carrying a shared inventory. */
export const HASH_KEY = "i";

/** Filename offered when exporting. */
export const EXPORT_FILENAME = "kcd2-dice.json";

/** What gets persisted between visits. */
export interface SavedInventory {
  readonly diceCounts: Record<string, number>;
  readonly badgeIds: string[];
}

/** An inventory with nothing in it. */
export const EMPTY: SavedInventory = { diceCounts: {}, badgeIds: [] };

/** A validated inventory plus a note for anything that had to be discarded. */
export interface ParseResult {
  readonly inventory: SavedInventory;
  /** Human-readable notes; empty when the payload was clean. */
  readonly dropped: readonly string[];
}

/**
 * Whether an inventory holds nothing at all.
 *
 * @param inventory - The inventory to test.
 * @returns True when it has neither dice nor badges.
 */
export function isEmptyInventory(inventory: SavedInventory): boolean {
  return Object.keys(inventory.diceCounts).length === 0 && inventory.badgeIds.length === 0;
}

/**
 * Whether a parse result carried anything worth applying.
 *
 * An empty result WITH complaints means the payload was unusable — a damaged
 * link, a truncated file, JSON that was never an inventory. An empty result
 * WITHOUT complaints is a legitimately empty inventory, which is a real thing
 * to import. Both callers (the paste box and the shared-link path) need exactly
 * this distinction, so it lives here rather than being spelled out twice.
 *
 * @param result - The result of parsing an untrusted payload.
 * @returns True when the inventory should be applied.
 */
export function isUsable({ inventory, dropped }: ParseResult): boolean {
  return !isEmptyInventory(inventory) || dropped.length === 0;
}

/**
 * Validate anything claiming to be an inventory, keeping what is usable.
 *
 * Sanitise rather than reject: a single unknown id — a die added in a later
 * game patch, a hand-edited file, a link from an older build — should not throw
 * away an inventory somebody just pasted. What it must not do is discard things
 * silently, so everything dropped is reported and the UI shows it. Only
 * structural failure (not an object at all) is fatal, because then there is
 * nothing left to keep.
 *
 * @param value - Untrusted parsed JSON.
 * @returns The usable inventory and notes on whatever was discarded.
 */
export function parseInventory(value: unknown): ParseResult {
  const dropped: string[] = [];
  if (typeof value !== "object" || value === null) {
    return { inventory: EMPTY, dropped: ["Not an inventory."] };
  }

  // Typed as unknown rather than Partial<SavedInventory>: the payload is
  // untrusted, and claiming its fields already have their declared types would
  // make the guards below look redundant to the type checker when they are the
  // only thing standing between a hand-edited file and the solver.
  const { diceCounts, badgeIds } = value as Record<string, unknown>;
  const counts: Record<string, number> = {};

  if (typeof diceCounts !== "object" || diceCounts === null) {
    dropped.push("No dice in this file.");
  } else {
    for (const [id, count] of Object.entries(diceCounts as Record<string, unknown>)) {
      if (!DICE_BY_ID.has(id)) {
        dropped.push(`Unknown die “${id}”.`);
      } else if (typeof count !== "number" || !Number.isInteger(count) || count < 0) {
        dropped.push(`Invalid count for “${id}”.`);
      } else if (count > MAX_PER_DIE) {
        dropped.push(`Count for “${id}” exceeds ${String(MAX_PER_DIE)}.`);
      } else if (count > 0) {
        // Zero is not an error — the app already omits empty entries.
        counts[id] = count;
      }
    }
  }

  const badges: string[] = [];
  if (!Array.isArray(badgeIds)) {
    dropped.push("No badges in this file.");
  } else {
    for (const id of badgeIds as unknown[]) {
      if (typeof id !== "string" || !BADGES_BY_ID.has(id)) {
        dropped.push(`Unknown badge “${String(id)}”.`);
      } else if (badges.includes(id)) {
        dropped.push(`Duplicate badge “${id}”.`);
      } else {
        badges.push(id);
      }
    }
  }

  return { inventory: { diceCounts: counts, badgeIds: badges }, dropped };
}

/**
 * Parse an inventory out of a JSON string.
 *
 * @param raw - Untrusted JSON text.
 * @returns The usable inventory and notes on whatever was discarded.
 */
export function parseInventoryJson(raw: string): ParseResult {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return { inventory: EMPTY, dropped: ["Not valid JSON."] };
  }
  return parseInventory(value);
}

/**
 * Read the saved inventory, tolerating anything unparsable.
 *
 * Returns the full ParseResult, not just the inventory: this path sanitises
 * exactly like the file, paste and link paths, so it has to be able to say what
 * it discarded. Swallowing `dropped` here made storage the one entry point of
 * the four that silently deleted entries — and it deleted them on first paint,
 * before anyone could object.
 *
 * @param storage - Where to read from; injectable for tests.
 * @returns The saved inventory and notes on anything discarded.
 */
export function loadInventory(storage: Pick<Storage, "getItem">): ParseResult {
  const raw = storage.getItem(STORAGE_KEY);
  if (raw === null) {
    return { inventory: EMPTY, dropped: [] };
  }
  // A corrupt entry costs the saved inventory, not the whole page.
  return parseInventoryJson(raw);
}

/**
 * Render an inventory as the JSON we hand to the user.
 *
 * @param inventory - The inventory to write out.
 * @returns Indented JSON.
 */
export function serialiseInventory(inventory: SavedInventory): string {
  return JSON.stringify(inventory, null, 2);
}

/**
 * Encode text as base64url (URL-safe, unpadded).
 *
 * @param text - ASCII text to encode.
 * @returns The base64url form.
 */
export function toBase64Url(text: string): string {
  return btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/**
 * Decode base64url text.
 *
 * @param encoded - base64url, with or without padding.
 * @returns The decoded text.
 */
export function fromBase64Url(encoded: string): string {
  const standard = encoded.replace(/-/g, "+").replace(/_/g, "/");
  const padding = (4 - (standard.length % 4)) % 4;
  return atob(standard + "=".repeat(padding));
}

/**
 * Encode an inventory as a URL fragment.
 *
 * base64url of the JSON, deliberately, rather than a compact positional scheme
 * keyed on the index of each die. `DICE` is sorted alphabetically, so any die
 * added in a future patch is all but guaranteed to land mid-array — which would
 * silently turn every previously-shared link into a *different* inventory.
 * A longer URL is a much better failure mode than quietly wrong data.
 *
 * @param inventory - The inventory to share.
 * @returns A fragment beginning with `#`.
 */
export function encodeInventoryHash(inventory: SavedInventory): string {
  return `#${HASH_KEY}=${toBase64Url(JSON.stringify(inventory))}`;
}

/**
 * Decode an inventory from a URL fragment.
 *
 * @param hash - The fragment, with or without its leading `#`.
 * @returns The parse result, or null when the fragment carries no inventory.
 */
export function decodeInventoryHash(hash: string): ParseResult | null {
  const params = new URLSearchParams(hash.startsWith("#") ? hash.slice(1) : hash);
  const encoded = params.get(HASH_KEY);
  if (encoded === null || encoded === "") {
    return null;
  }
  let json: string;
  try {
    // atob belongs inside the try with the parse: a malformed fragment throws
    // here, not in JSON.parse, and both mean the same thing to the caller.
    json = fromBase64Url(encoded);
  } catch {
    return { inventory: EMPTY, dropped: ["This link is damaged."] };
  }
  return parseInventoryJson(json);
}

/** Writing text to the system clipboard. */
export interface ClipboardPort {
  writeText: (text: string) => Promise<void>;
}

/**
 * The real clipboard.
 *
 * No optional chaining on purpose: on a non-secure origin or under jsdom this
 * throws or rejects, and the caller's catch is the failure path. Guarding with
 * `?.` would add a branch that no test could reach.
 */
export const browserClipboard: ClipboardPort = {
  writeText: (text: string): Promise<void> => navigator.clipboard.writeText(text),
};

/** Offering text to the user as a file download. */
export type SaveFilePort = (filename: string, text: string) => void;

/** The real download, via a synthetic anchor. */
export const browserSaveFile: SaveFilePort = (filename: string, text: string): void => {
  const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
};

/** Reading, clearing, and building on the page's URL. */
export interface UrlHashPort {
  read: () => string;
  clear: () => void;
  base: () => string;
}

/**
 * The real URL.
 *
 * One port with three methods rather than three separate props: under
 * `exactOptionalPropertyTypes` every optional prop owes a "falls back to the
 * real thing" test, so bundling them costs one test instead of three.
 */
export const browserUrlHash: UrlHashPort = {
  read: (): string => window.location.hash,
  clear: (): void => {
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
  },
  base: (): string => window.location.origin + window.location.pathname,
};
