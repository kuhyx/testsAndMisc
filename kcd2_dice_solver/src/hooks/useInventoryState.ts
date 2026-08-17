/**
 * The inventory the app is editing: where it came from, when it gets written
 * back, and how it changes.
 *
 * Three sources compete at mount — a shared link, this browser's storage, and
 * nothing at all — and the rules for resolving them are subtle enough that they
 * are stated here once rather than inline in the view. The comments on each
 * decision record cases that were live bugs.
 */

import { useCallback, useEffect, useState } from "react";
import type { CountUpdater } from "../components/QuantityStepper.tsx";
import {
  STORAGE_KEY,
  decodeInventoryHash,
  isEmptyInventory,
  loadInventory,
} from "../lib/inventoryIo.ts";
import type { SavedInventory, UrlHashPort } from "../lib/inventoryIo.ts";

/** What the view needs to render and mutate the inventory. */
export interface InventoryState {
  /** The inventory currently on screen. */
  readonly saved: SavedInventory;
  /** The inventory this browser had before a link was applied, for Discard. */
  readonly stored: SavedInventory;
  /** Entries the parser could not read, surfaced rather than dropped silently. */
  readonly dropped: readonly string[];
  /** True when the on-screen inventory came from a shared link. */
  readonly linkApplied: boolean;
  /** False while changes are deliberately not being written to storage. */
  readonly persist: boolean;
  /** Total dice owned, across every entry. */
  readonly total: number;
  /** Accept the current state and resume writing to storage. */
  readonly keep: () => void;
  /** Replace the whole inventory, e.g. from an import or Clear. */
  readonly replace: (inventory: SavedInventory) => void;
  /** Change how many of one die is owned. */
  readonly setDieCount: (id: string, update: CountUpdater) => void;
  /** Add or remove a badge from the owned set. */
  readonly toggleBadge: (id: string, owned: boolean) => void;
}

/**
 * Own the inventory: resolve where it came from, persist it once that is
 * consented to, and expose the mutators the view needs.
 *
 * @param store - Where the inventory is persisted between visits.
 * @param urlHash - Access to the URL fragment a shared link arrives in.
 * @returns The current inventory and everything needed to change it.
 */
export function useInventoryState(
  store: Pick<Storage, "getItem" | "setItem">,
  urlHash: UrlHashPort,
): InventoryState {
  // What this browser already had. Kept around so a shared link can be turned
  // down without losing it.
  const [stored] = useState(() => loadInventory(store));

  // A link beats whatever is in this browser: following one is a deliberate act
  // in a way that "opening the page again" is not.
  const [fromLink] = useState(() => decodeInventoryHash(urlHash.read()));

  /*
   * ...but only a link that actually carried dice or badges. Testing "did the
   * parser complain?" is not the same question: a link encoding a count of zero
   * parses perfectly and yields an EMPTY inventory, which would then replace the
   * visitor's own dice on screen, disable Clear (nothing to clear), and leave
   * Keep as the sole enabled control — writing that emptiness over their saved
   * loadout. Requiring the link to actually carry something removes the case.
   */
  const linkApplied = fromLink !== null && !isEmptyInventory(fromLink.inventory);
  const [saved, setSaved] = useState<SavedInventory>(() =>
    linkApplied ? fromLink.inventory : stored.inventory,
  );

  // Whatever was discarded on the way in, from whichever source was used. The
  // parser sanitises rather than rejects, so without surfacing this a die added
  // in a later game patch — or a URL a chat client truncated — would vanish in
  // complete silence.
  const dropped = linkApplied ? fromLink.dropped : stored.dropped;

  /*
   * Nothing is written to storage until the visitor accepts it. Silently
   * overwriting a saved loadout — with somebody else's dice, or with a
   * sanitised copy of their own that just lost an entry — is unrecoverable, and
   * a confirm() dialog is both untestable and hostile. Persistence is deferred
   * until they do something that implies consent: press Keep, or simply edit
   * anything. One boolean, and the banner clears itself the moment they engage.
   */
  const [persist, setPersist] = useState(!linkApplied && dropped.length === 0);

  useEffect(() => {
    if (persist) {
      store.setItem(STORAGE_KEY, JSON.stringify(saved));
    }
  }, [saved, store, persist]);

  useEffect(() => {
    /*
     * Clear ANY fragment, not just one that decoded. A fragment left in the bar
     * is a loaded gun: it is read once, at mount, so a link arriving in an
     * already-open tab is a same-document navigation that changes nothing now —
     * but survives to be applied over edited state on the next reload.
     */
    if (urlHash.read() !== "") {
      urlHash.clear();
    }
  }, [urlHash]);

  const setDieCount = useCallback((id: string, update: CountUpdater): void => {
    setPersist(true);
    setSaved((previous) => {
      // Applied to the previous state, not to a value captured at render time,
      // so a burst of clicks or wheel ticks accumulates instead of collapsing.
      const count = update(previous.diceCounts[id] ?? 0);
      // Rebuilt rather than mutated so a count of zero simply never makes it
      // into the saved object.
      const diceCounts = Object.fromEntries(
        Object.entries(previous.diceCounts).filter(([key]) => key !== id),
      );
      if (count > 0) {
        diceCounts[id] = count;
      }
      return { ...previous, diceCounts };
    });
  }, []);

  const toggleBadge = useCallback((id: string, owned: boolean): void => {
    setPersist(true);
    setSaved((previous) => ({
      ...previous,
      badgeIds: owned
        ? [...previous.badgeIds, id]
        : previous.badgeIds.filter((existing) => existing !== id),
    }));
  }, []);

  const replace = useCallback((inventory: SavedInventory): void => {
    setPersist(true);
    setSaved(inventory);
  }, []);

  const keep = useCallback((): void => {
    setPersist(true);
  }, []);

  const total = Object.values(saved.diceCounts).reduce((sum, count) => sum + count, 0);

  return {
    saved,
    stored: stored.inventory,
    dropped,
    linkApplied,
    persist,
    total,
    keep,
    replace,
    setDieCount,
    toggleBadge,
  };
}
