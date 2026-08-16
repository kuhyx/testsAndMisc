/**
 * Serialising an inventory into a URL hash and back.
 *
 * Split out of inventoryIo.ts to keep it under the 250-line cap.
 */

import { EMPTY, HASH_KEY, parseInventoryJson } from "./inventoryIo.ts";
import type { ParseResult, SavedInventory } from "./inventoryIo.ts";

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
