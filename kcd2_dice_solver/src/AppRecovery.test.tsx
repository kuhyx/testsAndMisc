/** How the App recovers a shared link that would clobber saved state. */

/** Shared-link and layout behaviour of the App shell. */

/**
 * End-to-end tests for the app, driving the real flow: search for a die, click
 * to add it, scroll the wheel over a counter, and get a real recommendation.
 *
 * The worker is replaced with a port that runs the *real* solver synchronously —
 * jsdom has no module-worker support, but nothing about the solver is stubbed,
 * so these exercise the actual recommendation path.
 */

import { render, screen, } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "./App.tsx";
import { STORAGE_KEY, encodeInventoryHash, } from "./lib/inventoryIo.ts";
import type { SavedInventory, UrlHashPort } from "./lib/inventoryIo.ts";
import { solve } from "./core/solve.ts";
import type { SolverPort } from "./hooks/useSolver.ts";
import type { WorkerReply, WorkerRequest } from "./worker/solver.worker.ts";

/**
 * A solver port that runs the real solver in-process.
 *
 * @returns A port usable in place of the Web Worker.
 */
function createInlinePort(): SolverPort {
  const listeners = new Set<(event: MessageEvent<WorkerReply>) => void>();
  return {
    postMessage: ({ id, request }: WorkerRequest) => {
      let reply: WorkerReply;
      try {
        // Keep the simulation short: these tests are about the wiring.
        reply = { id, ok: true, response: solve({ ...request, simulationTurns: 200 }) };
      } catch (error) {
        reply = { id, ok: false, error: error instanceof Error ? error.message : "failed" };
      }
      for (const listener of listeners) {
        listener({ data: reply } as MessageEvent<WorkerReply>);
      }
    },
    addEventListener: (_type, listener) => listeners.add(listener),
    removeEventListener: (_type, listener) => listeners.delete(listener),
  };
}

/**
 * An in-memory Storage stand-in, so tests do not share persisted state.
 *
 * @param initial - Optional starting contents.
 * @returns A minimal storage object.
 */
function memoryStorage(initial?: string): Pick<Storage, "getItem" | "setItem"> {
  const store = new Map<string, string>();
  if (initial !== undefined) {
    store.set(STORAGE_KEY, initial);
  }
  return {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => {
      store.set(key, value);
    },
  };
}

/**
 * Read back what the app persisted, typed so assertions are not on `any`.
 *
 * @param storage - The storage the app was given.
 * @returns The parsed inventory.
 */
function readSaved(storage: Pick<Storage, "getItem">): SavedInventory {
  return JSON.parse(storage.getItem(STORAGE_KEY) ?? "{}") as SavedInventory;
}

/**
 * A URL port that reports a fragment without touching the real location.
 *
 * @param hash - The fragment the page was "opened with".
 * @returns The port plus a record of whether the app cleared the fragment.
 */
function stubUrl(hash = ""): UrlHashPort & { cleared: () => number } {
  let clears = 0;
  return {
    read: () => hash,
    clear: () => {
      clears += 1;
    },
    base: () => "https://dice.example/",
    cleared: () => clears,
  };
}

const renderApp = (initial?: string, urlHash: UrlHashPort = stubUrl()) =>
  render(
    <App
      createPort={createInlinePort}
      storage={memoryStorage(initial)}
      urlHash={urlHash}
      clipboard={{ writeText: () => Promise.resolve() }}
      saveFile={() => undefined}
    />,
  );

describe("shared links cannot destroy what is already saved", () => {
  it("ignores a link that carries no dice or badges", () => {
    // A count of zero parses cleanly, so "did the parser complain?" is the
    // wrong question — this used to blank the inventory on screen, disable
    // Clear, and leave Keep as the only enabled control, writing the emptiness
    // over the visitor's own dice.
    const mine = JSON.stringify({ diceCounts: { lucky: 4 }, badgeIds: [] });
    const empty = encodeInventoryHash({ diceCounts: { weighted: 0 }, badgeIds: [] });
    const storage = memoryStorage(mine);
    render(
      <App createPort={createInlinePort} storage={storage} urlHash={stubUrl(empty)} />,
    );
    expect(screen.getByText("4 dice")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Keep" })).not.toBeInTheDocument();
    expect(readSaved(storage).diceCounts).toEqual({ lucky: 4 });
  });

  it("restores the visitor's own inventory when a link is discarded", async () => {
    const mine = JSON.stringify({ diceCounts: { lucky: 4 }, badgeIds: ["tin_might"] });
    const link = encodeInventoryHash({ diceCounts: { weighted: 3 }, badgeIds: [] });
    const storage = memoryStorage(mine);
    render(
      <App createPort={createInlinePort} storage={storage} urlHash={stubUrl(link)} />,
    );
    expect(screen.getByText("3 dice")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Discard" }));
    expect(screen.getByText("4 dice")).toBeInTheDocument();
    expect(readSaved(storage)).toEqual({
      diceCounts: { lucky: 4 },
      badgeIds: ["tin_might"],
    });
  });

  it("clears a fragment even when it decoded to nothing", () => {
    // A fragment left in the bar is read again on the next reload, where it
    // would land on top of whatever has been edited since.
    for (const hash of ["#i=@@@", "#other=1", "#i="]) {
      const url = stubUrl(hash);
      renderApp(undefined, url);
      expect(url.cleared()).toBe(1);
    }
  });
});

describe("a saved inventory that no longer parses cleanly", () => {
  const stale = JSON.stringify({
    diceCounts: { lucky: 4, future_patch_die: 6 },
    badgeIds: [],
  });

  it("is not silently truncated in storage on load", () => {
    const storage = memoryStorage(stale);
    render(<App createPort={createInlinePort} storage={storage} urlHash={stubUrl()} />);
    // Still the original text: nothing was written over it on first paint.
    expect(readSaved(storage).diceCounts).toEqual({ lucky: 4, future_patch_die: 6 });
  });

  it("says what it could not read, and only commits once accepted", async () => {
    const storage = memoryStorage(stale);
    render(<App createPort={createInlinePort} storage={storage} urlHash={stubUrl()} />);
    expect(screen.getByText(/Unknown die “future_patch_die”/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Keep" }));
    expect(readSaved(storage).diceCounts).toEqual({ lucky: 4 });
  });
});
