/**
 * KCD2 Dice Solver.
 *
 * Enter what dice and badges you own; get the best six to bring and the best
 * badge for each tier you hold.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import type { JSX } from "react";
import { BadgePicker } from "./components/BadgePicker.tsx";
import { DiceList } from "./components/DiceList.tsx";
import { InventoryIo } from "./components/InventoryIo.tsx";
import { ResultPanel } from "./components/ResultPanel.tsx";
import type { CountUpdater } from "./components/QuantityStepper.tsx";
import { SET_SIZE } from "./core/searchGroups.ts";
import type { SolveRequest } from "./core/solve.ts";
import { useSolver } from "./hooks/useSolver.ts";
import type { SolverPort } from "./hooks/useSolver.ts";
import {
  EMPTY,
  STORAGE_KEY,
  browserClipboard,
  browserSaveFile,
  browserUrlHash,
  decodeInventoryHash,
  encodeInventoryHash,
  isEmptyInventory,
  loadInventory,
} from "./lib/inventoryIo.ts";
import type {
  ClipboardPort,
  SavedInventory,
  SaveFilePort,
  UrlHashPort,
} from "./lib/inventoryIo.ts";

export interface AppProps {
  /** Overridden in tests to avoid depending on jsdom worker support. */
  readonly createPort?: () => SolverPort;
  /** Overridden in tests to isolate persistence. */
  readonly storage?: Pick<Storage, "getItem" | "setItem">;
  /** Overridden in tests; jsdom has no navigator.clipboard. */
  readonly clipboard?: ClipboardPort;
  /** Overridden in tests; jsdom has no URL.createObjectURL. */
  readonly saveFile?: SaveFilePort;
  /** Overridden in tests to keep location/history changes from leaking. */
  readonly urlHash?: UrlHashPort;
}

/**
 * The whole application.
 *
 * @param props - Optional injection points for tests.
 * @returns The app element.
 */
export function App({
  createPort,
  storage,
  clipboard = browserClipboard,
  saveFile = browserSaveFile,
  urlHash = browserUrlHash,
}: AppProps = {}): JSX.Element {
  const store = storage ?? window.localStorage;
  const [query, setQuery] = useState("");

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

  const importInventory = useCallback((inventory: SavedInventory): void => {
    setPersist(true);
    setSaved(inventory);
  }, []);

  const total = Object.values(saved.diceCounts).reduce((sum, count) => sum + count, 0);

  const request = useMemo<SolveRequest | null>(
    () =>
      total < SET_SIZE
        ? null
        : { diceCounts: saved.diceCounts, badgeIds: saved.badgeIds },
    [saved, total],
  );

  const { result, error, solving } = useSolver(request, createPort);
  const ownedBadges = useMemo(() => new Set(saved.badgeIds), [saved.badgeIds]);

  return (
    <div className="app">
      {/*
       * The left column is the dice list and nothing else. Everything that is
       * not "which dice do I own" — the title, the search box, the badges, the
       * results — lives on the right, where there is horizontal room going
       * spare, rather than eating the vertical budget the 43-row grid needs.
       */}
      <div className="columns">
        <section className="inventory">
          <DiceList query={query} counts={saved.diceCounts} onChange={setDieCount} />
        </section>

        <div className="side">
          <section className="controls">
            <header>
              <h1>KCD2 Dice Solver</h1>
              <p className="subtitle">
                Pick what you own; get the best six dice and a badge for each tier.
              </p>
            </header>

            <div className="toolbar">
              <input
                className="search"
                type="search"
                placeholder="Search dice and badges…"
                aria-label="Search dice and badges"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                }}
              />
              <span className="count">
                {total} {total === 1 ? "die" : "dice"}
              </span>
              <button
                type="button"
                className="clear"
                disabled={total === 0 && saved.badgeIds.length === 0}
                onClick={() => {
                  setPersist(true);
                  setSaved(EMPTY);
                }}
              >
                Clear
              </button>
            </div>

            {!persist && (
              <p className="notice" role="status">
                {linkApplied
                  ? "Loaded from a shared link — not saved on this device yet."
                  : "Some saved entries could not be read — not saved over yet."}{" "}
                <button
                  type="button"
                  className="clear"
                  onClick={() => {
                    setPersist(true);
                  }}
                >
                  Keep
                </button>{" "}
                {/* Without this, turning down a link means pressing Clear —
                    which writes an empty inventory over dice the visitor never
                    even saw, with no undo. */}
                {linkApplied && (
                  <button
                    type="button"
                    className="clear"
                    onClick={() => {
                      setPersist(true);
                      setSaved(stored.inventory);
                    }}
                  >
                    Discard
                  </button>
                )}
              </p>
            )}

            {dropped.length > 0 && (
              <p className="notice bad" role="status">
                {`Ignored: ${dropped.join(" ")}`}
              </p>
            )}
          </section>

          <section className="results">
            <ResultPanel result={result} error={error} solving={solving} />

            {/* Collapsed by default: badges matter far less than the dice, and
                open they cost more vertical space than everything else here. */}
            <details className="badges">
              <summary>Badges</summary>
              <BadgePicker query={query} owned={ownedBadges} onToggle={toggleBadge} />
            </details>

            <InventoryIo
              inventory={saved}
              onImport={importInventory}
              clipboard={clipboard}
              saveFile={saveFile}
              shareUrl={urlHash.base() + encodeInventoryHash(saved)}
            />

            <footer className="caveats">
            <h3>What these numbers are</h3>
            <ul>
              <li>
                Expected score and bust chance are <strong>exact</strong>, computed over
                every possible outcome of the six dice — not sampled.
              </li>
              <li>
                Points per turn is a <strong>simulation</strong> of a push-your-luck turn
                that banks at 300 points. Change how you play and it changes.
              </li>
              <li>
                Badge values are <strong>estimates</strong> for ranking badges against each
                other, not a prediction of a scoreline.
              </li>
              <li>
                Balatro’s die has <strong>one</strong> joker face, not six, and the game
                publishes <strong>no face probabilities</strong> for it. It is modelled as a
                fair die whose 1 is replaced by the joker — the same shape as the Devil’s
                head, but its joker also counts as a 1 when held alone.
              </li>
              <li>
                The three “Advantage” formations and the Headstart leads have{" "}
                <strong>no published point values</strong>; the figures used are marked
                UNVERIFIED in the source.
              </li>
            </ul>
            </footer>
          </section>
        </div>
      </div>
    </div>
  );
}
