/**
 * KCD2 Dice Solver.
 *
 * Enter what dice and badges you own; get the best six to bring and the best
 * badge for each tier you hold. Owning the inventory — where it came from and
 * when it is written back — is `useInventoryState`'s job; this file is the view.
 */

import { useMemo, useState } from "react";
import type { JSX } from "react";
import { BadgePicker } from "./components/BadgePicker.tsx";
import { DiceList } from "./components/DiceList.tsx";
import { InventoryIo } from "./components/InventoryIo.tsx";
import { ResultPanel } from "./components/ResultPanel.tsx";
import { SET_SIZE } from "./core/searchGroups.ts";
import type { SolveRequest } from "./core/solve.ts";
import { useInventoryState } from "./hooks/useInventoryState.ts";
import { useSolver } from "./hooks/useSolver.ts";
import type { SolverPort } from "./hooks/useSolver.ts";
import {
  EMPTY,
  browserClipboard,
  browserSaveFile,
  browserUrlHash,
  encodeInventoryHash,
} from "./lib/inventoryIo.ts";
import type { ClipboardPort, SaveFilePort, UrlHashPort } from "./lib/inventoryIo.ts";

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

  const {
    saved,
    stored,
    dropped,
    linkApplied,
    persist,
    total,
    keep,
    replace,
    setDieCount,
    toggleBadge,
  } = useInventoryState(store, urlHash);

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
                  replace(EMPTY);
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
                  onClick={keep}
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
                      replace(stored);
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
              onImport={replace}
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
