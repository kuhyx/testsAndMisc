/** Shared-link and layout behaviour of the App shell. */

/**
 * End-to-end tests for the app, driving the real flow: search for a die, click
 * to add it, scroll the wheel over a counter, and get a real recommendation.
 *
 * The worker is replaced with a port that runs the *real* solver synchronously —
 * jsdom has no module-worker support, but nothing about the solver is stubbed,
 * so these exercise the actual recommendation path.
 */

import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "./App.tsx";
import { STORAGE_KEY, encodeInventoryHash, toBase64Url } from "./lib/inventoryIo.ts";
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

describe("shared links", () => {
  const shared = encodeInventoryHash({ diceCounts: { weighted: 3 }, badgeIds: [] });

  it("prefers a link over whatever this browser had saved", () => {
    const mine = JSON.stringify({ diceCounts: { lucky: 1 }, badgeIds: [] });
    renderApp(mine, stubUrl(shared));
    expect(screen.getByText("3 dice")).toBeInTheDocument();
  });

  it("drops the fragment so a reload does not resurrect the link", () => {
    const url = stubUrl(shared);
    renderApp(undefined, url);
    expect(url.cleared()).toBe(1);
  });

  it("leaves the URL alone when there was no link", () => {
    const url = stubUrl();
    renderApp(undefined, url);
    expect(url.cleared()).toBe(0);
  });

  it("does not overwrite the saved inventory until the visitor commits", () => {
    // Silently clobbering somebody's own loadout with a link they opened is
    // unrecoverable, so nothing is written until they say so.
    const storage = memoryStorage(JSON.stringify({ diceCounts: { lucky: 1 }, badgeIds: [] }));
    render(
      <App
        createPort={createInlinePort}
        storage={storage}
        urlHash={stubUrl(shared)}
        clipboard={{ writeText: () => Promise.resolve() }}
        saveFile={() => undefined}
      />,
    );
    expect(screen.getByText("3 dice")).toBeInTheDocument();
    expect(readSaved(storage).diceCounts).toEqual({ lucky: 1 });
  });

  it("persists once Keep is pressed", async () => {
    const storage = memoryStorage();
    render(
      <App
        createPort={createInlinePort}
        storage={storage}
        urlHash={stubUrl(shared)}
        clipboard={{ writeText: () => Promise.resolve() }}
        saveFile={() => undefined}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Keep" }));
    expect(readSaved(storage).diceCounts).toEqual({ weighted: 3 });
    expect(screen.queryByRole("button", { name: "Keep" })).not.toBeInTheDocument();
  });

  it("persists as soon as the visitor edits anything, banner and all", async () => {
    const storage = memoryStorage();
    render(
      <App
        createPort={createInlinePort}
        storage={storage}
        urlHash={stubUrl(shared)}
        clipboard={{ writeText: () => Promise.resolve() }}
        saveFile={() => undefined}
      />,
    );
    await userEvent.type(screen.getByLabelText("Search dice and badges"), "wei");
    await userEvent.click(screen.getByLabelText("Remove one Weighted die"));
    expect(readSaved(storage).diceCounts).toEqual({ weighted: 2 });
    expect(screen.queryByRole("button", { name: "Keep" })).not.toBeInTheDocument();
  });

  it("shows no banner on an ordinary visit", () => {
    renderApp();
    expect(screen.queryByRole("button", { name: "Keep" })).not.toBeInTheDocument();
  });

  it("falls through to storage when the fragment carries no inventory", () => {
    const mine = JSON.stringify({ diceCounts: { lucky: 1 }, badgeIds: [] });
    renderApp(mine, stubUrl("#nothing=here"));
    expect(screen.getByText("1 die")).toBeInTheDocument();
  });

  it("keeps the saved inventory when the link is damaged", () => {
    const mine = JSON.stringify({ diceCounts: { lucky: 1 }, badgeIds: [] });
    // "@" is not a base64 character, so decoding throws rather than yielding
    // an inventory — the case a truncated or mangled URL actually produces.
    renderApp(mine, stubUrl("#i=@@@"));
    expect(screen.getByText("1 die")).toBeInTheDocument();
    // Nothing was taken from the link, so there is nothing to accept or refuse.
    expect(screen.queryByRole("button", { name: "Keep" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Discard" })).not.toBeInTheDocument();
  });

  it("reports what a shared link had to drop", () => {
    const link = `#i=${toBase64Url(
      JSON.stringify({ diceCounts: { weighted: 2, nosuchdie: 1 }, badgeIds: [] }),
    )}`;
    renderApp(undefined, stubUrl(link));
    expect(screen.getByText("2 dice")).toBeInTheDocument();
    expect(screen.getByText(/Unknown die/)).toBeInTheDocument();
  });

  it("replaces the whole inventory on import", async () => {
    const storage = memoryStorage(JSON.stringify({ diceCounts: { lucky: 2 }, badgeIds: [] }));
    render(
      <App createPort={createInlinePort} storage={storage} urlHash={stubUrl()} />,
    );
    fireEvent.change(screen.getByLabelText("Inventory JSON"), {
      target: { value: '{"diceCounts":{"weighted":4},"badgeIds":[]}' },
    });
    await userEvent.click(screen.getByRole("button", { name: "Import pasted" }));
    expect(screen.getByText("4 dice")).toBeInTheDocument();
    expect(readSaved(storage).diceCounts).toEqual({ weighted: 4 });
  });
});

describe("layout", () => {
  it("gives the left column to the dice and nothing else", () => {
    renderApp();
    const inventory = document.querySelector("section.inventory");
    if (!inventory) {
      throw new Error("no inventory section");
    }
    // The search box, the title and the badges all moved to the right column so
    // the 43-row grid gets the whole vertical budget.
    expect(inventory.querySelector(".die-list")).toBeInTheDocument();
    expect(inventory.querySelector(".toolbar")).toBeNull();
    expect(inventory.querySelector("h1")).toBeNull();
    expect(inventory.querySelector(".badges")).toBeNull();
  });

  it("keeps the badges collapsed until asked for", () => {
    renderApp();
    const badges = document.querySelector("details.badges");
    expect(badges).toBeInTheDocument();
    expect(badges).not.toHaveAttribute("open");
    // Still reachable — collapsed, not removed.
    expect(within(badges as HTMLElement).getByText("Badges")).toBeInTheDocument();
  });

  it("no longer tells touch users to scroll a mouse wheel", () => {
    renderApp();
    expect(screen.queryByText(/scroll the wheel/i)).not.toBeInTheDocument();
  });
});
