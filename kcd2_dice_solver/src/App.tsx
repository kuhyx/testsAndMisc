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
import { ResultPanel } from "./components/ResultPanel.tsx";
import type { CountUpdater } from "./components/QuantityStepper.tsx";
import { SET_SIZE } from "./core/search.ts";
import type { SolveRequest } from "./core/solve.ts";
import { useSolver } from "./hooks/useSolver.ts";
import type { SolverPort } from "./hooks/useSolver.ts";

/** localStorage key for the saved inventory. */
export const STORAGE_KEY = "kcd2-dice-solver.inventory";

/** What gets persisted between visits. */
export interface SavedInventory {
  readonly diceCounts: Record<string, number>;
  readonly badgeIds: string[];
}

const EMPTY: SavedInventory = { diceCounts: {}, badgeIds: [] };

/**
 * Read the saved inventory, tolerating anything unparsable.
 *
 * @param storage - Where to read from; injectable for tests.
 * @returns The saved inventory, or an empty one.
 */
export function loadInventory(storage: Pick<Storage, "getItem">): SavedInventory {
  const raw = storage.getItem(STORAGE_KEY);
  if (raw === null) {
    return EMPTY;
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) {
      return EMPTY;
    }
    const { diceCounts, badgeIds } = parsed as Partial<SavedInventory>;
    return {
      diceCounts: typeof diceCounts === "object" ? { ...diceCounts } : {},
      badgeIds: Array.isArray(badgeIds) ? [...badgeIds] : [],
    };
  } catch {
    // A corrupt entry should cost the saved inventory, not the whole page.
    return EMPTY;
  }
}

export interface AppProps {
  /** Overridden in tests to avoid depending on jsdom worker support. */
  readonly createPort?: () => SolverPort;
  /** Overridden in tests to isolate persistence. */
  readonly storage?: Pick<Storage, "getItem" | "setItem">;
}

/**
 * The whole application.
 *
 * @param props - Optional injection points for tests.
 * @returns The app element.
 */
export function App({ createPort, storage }: AppProps = {}): JSX.Element {
  const store = storage ?? window.localStorage;
  const [query, setQuery] = useState("");
  const [saved, setSaved] = useState<SavedInventory>(() => loadInventory(store));

  useEffect(() => {
    store.setItem(STORAGE_KEY, JSON.stringify(saved));
  }, [saved, store]);

  const setDieCount = useCallback((id: string, update: CountUpdater): void => {
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
    setSaved((previous) => ({
      ...previous,
      badgeIds: owned
        ? [...previous.badgeIds, id]
        : previous.badgeIds.filter((existing) => existing !== id),
    }));
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
      <header>
        <h1>KCD2 Dice Solver</h1>
        <p className="subtitle">
          Pick what you own; get the best six dice and a badge for each tier.
        </p>
      </header>

      <div className="columns">
        <section className="inventory">
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
                setSaved(EMPTY);
              }}
            >
              Clear
            </button>
          </div>

          <p className="hint">
            Click a die to add one, or scroll the wheel over its counter.
          </p>

          <DiceList query={query} counts={saved.diceCounts} onChange={setDieCount} />

          <h2>Badges</h2>
          <BadgePicker query={query} owned={ownedBadges} onToggle={toggleBadge} />
        </section>

        <section className="results">
          <ResultPanel result={result} error={error} solving={solving} />

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
                Balatro’s die is modelled as always counting in your favour, so it will
                always be picked if you own it.
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
  );
}
