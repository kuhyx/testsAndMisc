/**
 * End-to-end tests for the app, driving the real flow: search for a die, click
 * to add it, scroll the wheel over a counter, and get a real recommendation.
 *
 * The worker is replaced with a port that runs the *real* solver synchronously —
 * jsdom has no module-worker support, but nothing about the solver is stubbed,
 * so these exercise the actual recommendation path.
 */

import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App, STORAGE_KEY, loadInventory } from "./App.tsx";
import type { SavedInventory } from "./App.tsx";
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

const renderApp = (initial?: string) =>
  render(<App createPort={createInlinePort} storage={memoryStorage(initial)} />);

describe("loadInventory", () => {
  it("starts empty when nothing is saved", () => {
    expect(loadInventory(memoryStorage())).toEqual({ diceCounts: {}, badgeIds: [] });
  });

  it("restores a saved inventory", () => {
    const saved = JSON.stringify({ diceCounts: { weighted: 3 }, badgeIds: ["tin_might"] });
    expect(loadInventory(memoryStorage(saved))).toEqual({
      diceCounts: { weighted: 3 },
      badgeIds: ["tin_might"],
    });
  });

  it("survives a corrupt entry rather than taking the page down with it", () => {
    expect(loadInventory(memoryStorage("{not json"))).toEqual({ diceCounts: {}, badgeIds: [] });
  });

  it("survives an entry of the wrong shape", () => {
    expect(loadInventory(memoryStorage("42"))).toEqual({ diceCounts: {}, badgeIds: [] });
    expect(loadInventory(memoryStorage("null"))).toEqual({ diceCounts: {}, badgeIds: [] });
    expect(loadInventory(memoryStorage('{"diceCounts":"nope","badgeIds":"nope"}'))).toEqual({
      diceCounts: {},
      badgeIds: [],
    });
  });
});

describe("App", () => {
  it("asks for dice before anything is entered", () => {
    renderApp();
    expect(screen.getByText(/Add at least six dice/)).toBeInTheDocument();
    expect(screen.getByText("0 dice")).toBeInTheDocument();
  });

  it("finds a die by fuzzy search, adds six by clicking, and solves", async () => {
    renderApp();

    await userEvent.type(screen.getByLabelText("Search dice and badges"), "wei");
    const row = screen.getAllByRole("listitem")[0];
    const add = within(row).getByRole("button", { name: "Weighted die" });

    for (let i = 0; i < 6; i += 1) {
      await userEvent.click(add);
    }

    expect(screen.getByText("6 dice")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Best loadout")).toBeInTheDocument();
    });
    // Six Weighted dice is the right answer and the panel must name it.
    expect(screen.getByText("6×")).toBeInTheDocument();
    expect(screen.getByText("Weighted die")).toBeInTheDocument();
    expect(screen.getByText(/Provably optimal/)).toBeInTheDocument();
  });

  it("adds dice by scrolling the wheel over the counter", async () => {
    renderApp();
    await userEvent.type(screen.getByLabelText("Search dice and badges"), "wei");
    const counter = screen.getByLabelText("How many Weighted die");
    const stepper = counter.parentElement;
    if (!stepper) {
      throw new Error("no stepper");
    }

    for (let i = 0; i < 6; i += 1) {
      fireEvent.wheel(stepper, { deltaY: -120 });
    }
    expect(screen.getByLabelText("How many Weighted die")).toHaveValue(6);
    expect(screen.getByText("6 dice")).toBeInTheDocument();

    fireEvent.wheel(stepper, { deltaY: 120 });
    expect(screen.getByLabelText("How many Weighted die")).toHaveValue(5);
    expect(screen.getByText("5 dice")).toBeInTheDocument();
  });

  it("accumulates a rapid burst of clicks and wheel ticks", async () => {
    // Driving the real app in headless Chrome caught this: six fast clicks used
    // to land as one, because each handler computed from the count captured at
    // render time. React batches faster than it re-renders.
    renderApp();
    await userEvent.type(screen.getByLabelText("Search dice and badges"), "wei");

    const row = screen.getAllByRole("listitem")[0];
    const add = within(row).getByRole("button", { name: "Weighted die" });
    act(() => {
      for (let i = 0; i < 4; i += 1) {
        fireEvent.click(add);
      }
    });
    expect(screen.getByLabelText("How many Weighted die")).toHaveValue(4);

    const stepper = screen.getByLabelText("How many Weighted die").parentElement;
    if (!stepper) {
      throw new Error("no stepper");
    }
    act(() => {
      for (let i = 0; i < 2; i += 1) {
        fireEvent.wheel(stepper, { deltaY: -120 });
      }
    });
    expect(screen.getByLabelText("How many Weighted die")).toHaveValue(6);
    expect(screen.getByText("6 dice")).toBeInTheDocument();
  });

  it("ranks the badges you own alongside the dice", async () => {
    const saved = JSON.stringify({
      diceCounts: { weighted: 6 },
      badgeIds: ["gold_emperors", "gold_defence"],
    });
    renderApp(saved);

    await waitFor(() => {
      expect(screen.getByText("Best badge per tier")).toBeInTheDocument();
    });
    // The name also appears in the ownership checkbox, so scope to the result.
    const results = document.querySelector(".result");
    if (!results) {
      throw new Error("no result panel");
    }
    expect(within(results as HTMLElement).getByText("Gold Emperor's badge")).toBeInTheDocument();
    // The Defence badge is owned too, and must be reported as situational
    // rather than given an invented number.
    expect(within(results as HTMLElement).getByText(/situational/)).toBeInTheDocument();
  });

  it("restores a saved inventory on load", () => {
    renderApp(JSON.stringify({ diceCounts: { weighted: 4 }, badgeIds: [] }));
    expect(screen.getByText("4 dice")).toBeInTheDocument();
  });

  it("persists changes for next time", async () => {
    const storage = memoryStorage();
    render(<App createPort={createInlinePort} storage={storage} />);
    await userEvent.type(screen.getByLabelText("Search dice and badges"), "wei");
    await userEvent.click(screen.getByLabelText("Add one Weighted die"));

    expect(readSaved(storage)).toEqual({ diceCounts: { weighted: 1 }, badgeIds: [] });
  });

  it("clears everything on request", async () => {
    renderApp(JSON.stringify({ diceCounts: { weighted: 6 }, badgeIds: ["tin_might"] }));
    await waitFor(() => {
      expect(screen.getByText("Best loadout")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.getByText("0 dice")).toBeInTheDocument();
    expect(screen.getByText(/Add at least six dice/)).toBeInTheDocument();
  });

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
