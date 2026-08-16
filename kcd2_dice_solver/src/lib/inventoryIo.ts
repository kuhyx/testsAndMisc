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

export {
  browserClipboard,
  browserSaveFile,
  browserUrlHash,
  decodeInventoryHash,
  encodeInventoryHash,
  fromBase64Url,
  serialiseInventory,
  toBase64Url,
} from "./inventoryHash.ts";
export type { ClipboardPort, SaveFilePort, UrlHashPort } from "./inventoryHash.ts";
