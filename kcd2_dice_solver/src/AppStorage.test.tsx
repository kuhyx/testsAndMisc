/** How the App shell falls back to browser storage. */

/** The App shell's core behaviour. */

/**
 * End-to-end tests for the app, driving the real flow: search for a die, click
 * to add it, scroll the wheel over a counter, and get a real recommendation.
 *
 * The worker is replaced with a port that runs the *real* solver synchronously —
 * jsdom has no module-worker support, but nothing about the solver is stubbed,
 * so these exercise the actual recommendation path.
 */

import { render, screen, waitFor, } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "./App.tsx";
import { STORAGE_KEY, } from "./lib/inventoryIo.ts";
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

describe("App storage", () => {
  it("falls back to the browser's own storage when none is injected", () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ diceCounts: { weighted: 2 }, badgeIds: [] }),
    );
    render(<App createPort={createInlinePort} />);
    expect(screen.getByText("2 dice")).toBeInTheDocument();
    window.localStorage.clear();
  });

  it("disables Clear when there is nothing to clear", () => {
    renderApp();
    expect(screen.getByRole("button", { name: "Clear" })).toBeDisabled();
  });

  it("drops a die from the inventory when its count reaches zero", async () => {
    const storage = memoryStorage(
      JSON.stringify({ diceCounts: { weighted: 1 }, badgeIds: [] }),
    );
    render(<App createPort={createInlinePort} storage={storage} />);
    await userEvent.type(screen.getByLabelText("Search dice and badges"), "wei");
    await userEvent.click(screen.getByLabelText("Remove one Weighted die"));

    expect(readSaved(storage)).toEqual({ diceCounts: {}, badgeIds: [] });
  });

  it("toggles a badge on and off", async () => {
    const storage = memoryStorage();
    render(<App createPort={createInlinePort} storage={storage} />);
    await userEvent.type(screen.getByLabelText("Search dice and badges"), "emperor");

    const checkbox = screen.getByRole("checkbox");
    await userEvent.click(checkbox);
    expect(readSaved(storage).badgeIds).toEqual(["gold_emperors"]);

    await userEvent.click(checkbox);
    expect(readSaved(storage).badgeIds).toEqual([]);
  });

  it("uses the singular for a single die", async () => {
    renderApp();
    await userEvent.type(screen.getByLabelText("Search dice and badges"), "wei");
    await userEvent.click(screen.getByLabelText("Add one Weighted die"));
    expect(screen.getByText("1 die")).toBeInTheDocument();
  });

  it("surfaces a solver error rather than showing nothing", async () => {
    // A port that always fails, standing in for a worker that threw.
    const failingPort = (): SolverPort => {
      const listeners = new Set<(event: MessageEvent<WorkerReply>) => void>();
      return {
        postMessage: ({ id }: WorkerRequest) => {
          for (const listener of listeners) {
            listener({ data: { id, ok: false, error: "solver exploded" } } as MessageEvent<
              WorkerReply
            >);
          }
        },
        addEventListener: (_type, listener) => listeners.add(listener),
        removeEventListener: (_type, listener) => listeners.delete(listener),
      };
    };
    render(
      <App
        createPort={failingPort}
        storage={memoryStorage(JSON.stringify({ diceCounts: { weighted: 6 }, badgeIds: [] }))}
      />,
    );
    await waitFor(() => {
      expect(screen.getByText("solver exploded")).toBeInTheDocument();
    });
  });
});
