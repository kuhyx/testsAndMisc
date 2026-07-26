/**
 * Component tests for the three ways of entering an inventory: clicking a die,
 * scrolling the wheel over its counter, and fuzzy-searching by name.
 */

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MAX_PER_DIE } from "../data/dice.ts";
import type { Die } from "../data/dice.ts";
import type { SolveResponse } from "../core/solve.ts";
import type { SavedInventory } from "../lib/inventoryIo.ts";
import { BadgePicker } from "./BadgePicker.tsx";
import { DiceList } from "./DiceList.tsx";
import { DieRow, highlightName } from "./DieRow.tsx";
import { InventoryIo } from "./InventoryIo.tsx";
import type { InventoryIoProps } from "./InventoryIo.tsx";
import { QuantityStepper, clampCount } from "./QuantityStepper.tsx";
import { ResultPanel, summariseDice } from "./ResultPanel.tsx";

/**
 * Apply the updater a component emitted, to assert on the resulting count.
 *
 * @param mock - The mocked onChange.
 * @param previous - The count it should be applied to.
 * @param call - Which call to read, counting from the end by default.
 * @returns The count the component asked for.
 */
function applied(
  mock: { mock: { calls: unknown[][] } },
  previous: number,
  call = mock.mock.calls.length - 1,
): number {
  const update = mock.mock.calls[call][0] as (p: number) => number;
  return update(previous);
}

const ordinary: Die = {
  id: "ordinary",
  name: "Ordinary die",
  description: "An ordinary playing die.",
  weights: [1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6],
  wildcardFaces: [],
  wildScoresAlone: false,
};

describe("clampCount", () => {
  it("keeps a value inside the range", () => {
    expect(clampCount(3, 6)).toBe(3);
    expect(clampCount(-2, 6)).toBe(0);
    expect(clampCount(99, 6)).toBe(6);
  });

  it("floors fractions and rejects nonsense", () => {
    expect(clampCount(2.9, 6)).toBe(2);
    expect(clampCount(Number.NaN, 6)).toBe(0);
  });
});

describe("QuantityStepper", () => {
  it("adds one when the plus button is pressed", async () => {
    const onChange = vi.fn();
    render(<QuantityStepper label="Ordinary die" value={2} max={6} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText("Add one Ordinary die"));
    expect(applied(onChange, 2)).toBe(3);
  });

  it("removes one when the minus button is pressed", async () => {
    const onChange = vi.fn();
    render(<QuantityStepper label="Ordinary die" value={2} max={6} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText("Remove one Ordinary die"));
    expect(applied(onChange, 2)).toBe(1);
  });

  it("disables the buttons at the ends of the range", () => {
    const { rerender } = render(
      <QuantityStepper label="Ordinary die" value={0} max={6} onChange={vi.fn()} />,
    );
    expect(screen.getByLabelText("Remove one Ordinary die")).toBeDisabled();
    rerender(<QuantityStepper label="Ordinary die" value={6} max={6} onChange={vi.fn()} />);
    expect(screen.getByLabelText("Add one Ordinary die")).toBeDisabled();
  });

  it("increments on a wheel scroll up and decrements on a scroll down", () => {
    const onChange = vi.fn();
    const { container } = render(
      <QuantityStepper label="Ordinary die" value={2} max={6} onChange={onChange} />,
    );
    const stepper = container.querySelector(".stepper");
    if (!stepper) {
      throw new Error("no stepper");
    }
    fireEvent.wheel(stepper, { deltaY: -120 });
    expect(applied(onChange, 2)).toBe(3);
    fireEvent.wheel(stepper, { deltaY: 120 });
    expect(applied(onChange, 2)).toBe(1);
  });

  it("accumulates a burst of wheel ticks rather than collapsing them", () => {
    // Wheel events arrive far faster than React re-renders. Emitting an
    // absolute `value + 1` made six ticks land as one; each emitted updater
    // must therefore compose.
    const onChange = vi.fn();
    const { container } = render(
      <QuantityStepper label="Ordinary die" value={0} max={6} onChange={onChange} />,
    );
    const stepper = container.querySelector(".stepper");
    if (!stepper) {
      throw new Error("no stepper");
    }
    for (let i = 0; i < 6; i += 1) {
      fireEvent.wheel(stepper, { deltaY: -120 });
    }
    expect(onChange).toHaveBeenCalledTimes(6);
    const total = onChange.mock.calls.reduce(
      (count: number, [update]) => (update as (p: number) => number)(count),
      0,
    );
    expect(total).toBe(6);
  });

  it("shows the count as a readout inside the stepper", () => {
    // The wheel handler lives on `.stepper`, so the readout must stay a direct
    // child of it — App.test.tsx reaches the wheel target via parentElement.
    render(<QuantityStepper label="Ordinary die" value={3} max={6} onChange={vi.fn()} />);
    const readout = screen.getByLabelText("How many Ordinary die");
    expect(readout).toHaveTextContent("3");
    expect(readout.parentElement).toHaveClass("stepper");
  });
});

describe("highlightName", () => {
  it("marks the matched characters and leaves the rest alone", () => {
    const { container } = render(<p>{highlightName("Die", [0])}</p>);
    expect(container.querySelectorAll("mark")).toHaveLength(1);
    expect(container.textContent).toBe("Die");
  });
});

describe("DieRow", () => {
  it("adds one die when the row is clicked", async () => {
    const onChange = vi.fn();
    render(<DieRow die={ordinary} count={0} highlight={[]} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Ordinary die" }));
    expect(applied(onChange, 0)).toBe(1);
  });

  it("stops at the maximum when clicked repeatedly", async () => {
    const onChange = vi.fn();
    render(
      <DieRow die={ordinary} count={MAX_PER_DIE} highlight={[]} onChange={onChange} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Ordinary die" }));
    expect(applied(onChange, MAX_PER_DIE)).toBe(MAX_PER_DIE);
  });

  it("marks a row you own", () => {
    const { container } = render(
      <DieRow die={ordinary} count={2} highlight={[]} onChange={vi.fn()} />,
    );
    expect(container.querySelector(".die-row")).toHaveClass("owned");
  });

  it("tags the wildcard dice", () => {
    const balatro: Die = {
      ...ordinary,
      id: "balatro",
      wildcardFaces: [1],
      wildScoresAlone: true,
    };
    render(<DieRow die={balatro} count={0} highlight={[]} onChange={vi.fn()} />);
    expect(screen.getByText("wild")).toBeInTheDocument();
  });
});

describe("DiceList", () => {
  it("shows every die when the query is empty", () => {
    render(<DiceList query="" counts={{}} onChange={vi.fn()} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(43);
  });

  it("narrows to the Weighted die on a three-letter query", () => {
    render(<DiceList query="wei" counts={{}} onChange={vi.fn()} />);
    const rows = screen.getAllByRole("listitem");
    // The name is split into highlighted and plain runs, so match on the row
    // button's accessible name rather than on a single text node.
    expect(within(rows[0]).getByRole("button", { name: "Weighted die" })).toBeInTheDocument();
  });

  it("highlights the characters the query matched", () => {
    render(<DiceList query="wei" counts={{}} onChange={vi.fn()} />);
    const rows = screen.getAllByRole("listitem");
    expect(within(rows[0]).getByText("Wei").tagName).toBe("MARK");
  });

  it("finds a die by a fragment from the middle of its name", () => {
    render(<DiceList query="grozav" counts={{}} onChange={vi.fn()} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });

  it("says so when nothing matches", () => {
    render(<DiceList query="qqqqq" counts={{}} onChange={vi.fn()} />);
    expect(screen.getByText(/No die matches/)).toBeInTheDocument();
  });

  it("passes the owned count through to the row", () => {
    render(<DiceList query="wei" counts={{ weighted: 4 }} onChange={vi.fn()} />);
    expect(screen.getByLabelText("How many Weighted die")).toHaveTextContent("4");
  });

  it("reports which die changed", async () => {
    const onChange = vi.fn();
    render(<DiceList query="wei" counts={{}} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Weighted die" }));
    expect(onChange.mock.calls[0][0]).toBe("weighted");
    expect((onChange.mock.calls[0][1] as (p: number) => number)(0)).toBe(1);
  });
});

describe("BadgePicker", () => {
  it("groups badges under their tier", () => {
    render(<BadgePicker query="" owned={new Set()} onToggle={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "tin" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "silver" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "gold" })).toBeInTheDocument();
  });

  it("hides a tier with no matching badge", () => {
    render(<BadgePicker query="emperor" owned={new Set()} onToggle={vi.fn()} />);
    expect(screen.queryByRole("heading", { name: "tin" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "gold" })).toBeInTheDocument();
  });

  it("reflects which badges are owned", () => {
    render(<BadgePicker query="emperor" owned={new Set(["gold_emperors"])} onToggle={vi.fn()} />);
    expect(screen.getByRole("checkbox")).toBeChecked();
  });

  it("reports a toggle in both directions", async () => {
    const onToggle = vi.fn();
    const { rerender } = render(
      <BadgePicker query="emperor" owned={new Set()} onToggle={onToggle} />,
    );
    await userEvent.click(screen.getByRole("checkbox"));
    expect(onToggle).toHaveBeenLastCalledWith("gold_emperors", true);

    rerender(
      <BadgePicker query="emperor" owned={new Set(["gold_emperors"])} onToggle={onToggle} />,
    );
    await userEvent.click(screen.getByRole("checkbox"));
    expect(onToggle).toHaveBeenLastCalledWith("gold_emperors", false);
  });
});

describe("summariseDice", () => {
  it("collapses duplicates and orders by count", () => {
    const weighted: Die = { ...ordinary, id: "weighted", name: "Weighted die" };
    expect(summariseDice([ordinary, weighted, weighted, weighted])).toEqual([
      { die: weighted, count: 3 },
      { die: ordinary, count: 1 },
    ]);
  });
});

const response: SolveResponse = {
  dice: new Array<Die>(6).fill(ordinary),
  evaluation: { ev: 399.1, bustProbability: 0.0309, p90: 900 },
  simulation: {
    meanPerTurn: 412.5,
    standardError: 3.2,
    bustRate: 0.2,
    throwsPerTurn: 1.4,
    turns: 20000,
  },
  optimal: true,
  alternatives: [],
  badges: [],
  inventorySize: 6,
};

describe("ResultPanel", () => {
  it("prompts for dice before the first solve", () => {
    render(<ResultPanel result={null} error={null} solving={false} />);
    expect(screen.getByText(/Add at least six dice/)).toBeInTheDocument();
  });

  it("says it is working while a solve is in flight", () => {
    render(<ResultPanel result={null} error={null} solving />);
    expect(screen.getByText("Solving…")).toBeInTheDocument();
  });

  it("shows an error instead of a stale answer", () => {
    render(<ResultPanel result={null} error="Need at least 6 dice" solving={false} />);
    expect(screen.getByText("Need at least 6 dice")).toBeInTheDocument();
  });

  it("shows the loadout and its numbers", () => {
    render(<ResultPanel result={response} error={null} solving={false} />);
    expect(screen.getByText("6×")).toBeInTheDocument();
    expect(screen.getByText("Ordinary die")).toBeInTheDocument();
    expect(screen.getByText("399")).toBeInTheDocument();
    expect(screen.getByText("3.09%")).toBeInTheDocument();
    expect(screen.getByText("900")).toBeInTheDocument();
  });

  it("says when the answer is proven rather than merely good", () => {
    render(<ResultPanel result={response} error={null} solving={false} />);
    expect(screen.getByText(/Provably optimal/)).toBeInTheDocument();
  });

  it("admits when the answer is only a local search result", () => {
    render(
      <ResultPanel result={{ ...response, optimal: false }} error={null} solving={false} />,
    );
    expect(screen.getByText(/not proven/)).toBeInTheDocument();
  });

  it("lists runners-up when there are any", () => {
    const withAlternatives: SolveResponse = {
      ...response,
      alternatives: [
        { dice: new Array<Die>(6).fill(ordinary), evaluation: response.evaluation },
      ],
    };
    render(<ResultPanel result={withAlternatives} error={null} solving={false} />);
    expect(screen.getByText("Runners-up")).toBeInTheDocument();
  });

  it("asks for badges when none are owned", () => {
    render(<ResultPanel result={response} error={null} solving={false} />);
    expect(screen.getByText(/Tick the badges you own/)).toBeInTheDocument();
  });

  it("shows the pick, its value and its reasoning for each tier", () => {
    const withBadges: SolveResponse = {
      ...response,
      badges: [
        {
          tier: "gold",
          ranked: [
            {
              badge: {
                id: "gold_emperors",
                name: "Gold Emperor's badge",
                description: "",
                tier: "gold",
                effect: { kind: "scoring", rules: { emperorTriple: true } },
              },
              pointsPerGame: 1234,
              reason: "Changes the scoring table.",
              dice: new Array<Die>(6).fill(ordinary),
            },
            {
              badge: {
                id: "gold_warlord",
                name: "Gold Warlord badge",
                description: "",
                tier: "gold",
                effect: { kind: "multiplier", factor: 2, uses: 1 },
              },
              pointsPerGame: 567,
              reason: "Doubles a good turn.",
              dice: null,
            },
            {
              badge: {
                id: "gold_defence",
                name: "Gold Defence badge",
                description: "",
                tier: "gold",
                effect: { kind: "defence" },
              },
              pointsPerGame: null,
              reason: "Situational.",
              dice: null,
            },
          ],
        },
      ],
    };
    render(<ResultPanel result={withBadges} error={null} solving={false} />);
    expect(screen.getByText("Gold Emperor's badge")).toBeInTheDocument();
    expect(screen.getByText(/~1,234 pts\/game/)).toBeInTheDocument();
    expect(screen.getByText("Changes the scoring table.")).toBeInTheDocument();
    expect(screen.getByText(/With this badge, bring/)).toBeInTheDocument();
    // The runners-up list renders both a valued badge and a situational one.
    expect(screen.getByText(/Gold Warlord badge — ~567 pts\/game/)).toBeInTheDocument();
    expect(screen.getByText(/Gold Defence badge — situational/)).toBeInTheDocument();
  });

  it("dims the panel while a fresh solve is running", () => {
    const { container } = render(
      <ResultPanel result={response} error={null} solving />,
    );
    expect(container.querySelector(".result")).toHaveClass("stale");
  });
});

describe("InventoryIo", () => {
  const inventory: SavedInventory = {
    diceCounts: { weighted: 2 },
    badgeIds: ["tin_might"],
  };

  /**
   * Render the panel with every port stubbed, and open it.
   *
   * @param overrides - Ports or handlers to replace.
   * @returns The stubs the caller will want to assert on.
   */
  function setup(overrides: Partial<InventoryIoProps> = {}) {
    const onImport = vi.fn();
    const saveFile = vi.fn();
    const clipboard = { writeText: vi.fn<(text: string) => Promise<void>>().mockResolvedValue() };
    render(
      <InventoryIo
        inventory={inventory}
        onImport={onImport}
        clipboard={clipboard}
        saveFile={saveFile}
        shareUrl="https://dice.example/#i=abc"
        {...overrides}
      />,
    );
    return { onImport, saveFile, clipboard };
  }

  it("starts collapsed so it costs no vertical space", () => {
    setup();
    expect(screen.getByText("Import / export").closest("details")).not.toHaveAttribute("open");
  });

  it("downloads the inventory as parseable JSON", async () => {
    const { saveFile } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Download .json" }));
    expect(saveFile).toHaveBeenCalledTimes(1);
    const [filename, body] = saveFile.mock.calls[0] as [string, string];
    expect(filename).toBe("kcd2-dice.json");
    expect(JSON.parse(body)).toEqual(inventory);
    expect(screen.getByRole("status")).toHaveTextContent("Saved kcd2-dice.json.");
  });

  it("copies the JSON to the clipboard", async () => {
    const { clipboard } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Copy JSON" }));
    expect(JSON.parse(clipboard.writeText.mock.calls[0][0])).toEqual(inventory);
    await screen.findByText("JSON copied.");
  });

  it("copies the share link", async () => {
    const { clipboard } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Copy link" }));
    expect(clipboard.writeText).toHaveBeenCalledWith("https://dice.example/#i=abc");
    await screen.findByText("Link copied.");
  });

  it("falls back to the textarea when the clipboard refuses", async () => {
    // Insecure origins reject; the payload must still be reachable by hand.
    const clipboard = {
      writeText: vi.fn<(text: string) => Promise<void>>().mockRejectedValue(new Error("denied")),
    };
    setup({ clipboard });
    await userEvent.click(screen.getByRole("button", { name: "Copy JSON" }));
    await screen.findByText(/Copy failed/);
    const box = screen.getByLabelText<HTMLTextAreaElement>("Inventory JSON");
    expect(JSON.parse(box.value)).toEqual(inventory);
  });

  it("imports a pasted inventory", async () => {
    const { onImport } = setup();
    // fireEvent rather than userEvent.type: the latter treats "{" and "[" as
    // key-descriptor syntax, which mangles JSON.
    fireEvent.change(screen.getByLabelText("Inventory JSON"), {
      target: { value: JSON.stringify({ diceCounts: { lucky: 3 }, badgeIds: [] }) },
    });
    await userEvent.click(screen.getByRole("button", { name: "Import pasted" }));
    expect(onImport).toHaveBeenCalledWith({ diceCounts: { lucky: 3 }, badgeIds: [] });
    expect(screen.getByRole("status")).toHaveTextContent("Imported.");
  });

  it("refuses an unusable payload without calling onImport", async () => {
    const { onImport } = setup();
    fireEvent.change(screen.getByLabelText("Inventory JSON"), { target: { value: "{not json" } });
    await userEvent.click(screen.getByRole("button", { name: "Import pasted" }));
    expect(onImport).not.toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent("Nothing imported. Not valid JSON.");
  });

  it("imports what it can and says what it ignored", async () => {
    const { onImport } = setup();
    fireEvent.change(screen.getByLabelText("Inventory JSON"), {
      target: { value: '{"diceCounts":{"lucky":1,"nope":2},"badgeIds":[]}' },
    });
    await userEvent.click(screen.getByRole("button", { name: "Import pasted" }));
    expect(onImport).toHaveBeenCalledWith({ diceCounts: { lucky: 1 }, badgeIds: [] });
    expect(screen.getByRole("status")).toHaveTextContent("Ignored: Unknown die “nope”.");
  });

  it("keeps the import button disabled until something is pasted", () => {
    setup();
    expect(screen.getByRole("button", { name: "Import pasted" })).toBeDisabled();
  });

  it("imports an uploaded file", async () => {
    const { onImport } = setup();
    const file = new File([JSON.stringify({ diceCounts: { lucky: 5 }, badgeIds: [] })], "inv.json", {
      type: "application/json",
    });
    await userEvent.upload(screen.getByLabelText(/Load a .json file/), file);
    await waitFor(() => {
      expect(onImport).toHaveBeenCalledWith({ diceCounts: { lucky: 5 }, badgeIds: [] });
    });
  });

  it("does nothing when the file picker is dismissed", () => {
    const { onImport } = setup();
    const input = screen.getByLabelText(/Load a .json file/);
    fireEvent.change(input, { target: { files: [] } });
    expect(onImport).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { files: null } });
    expect(onImport).not.toHaveBeenCalled();
  });

  it("reports a file it cannot read", async () => {
    const { onImport } = setup();
    const unreadable = new File(["x"], "bad.json", { type: "application/json" });
    vi.spyOn(unreadable, "text").mockRejectedValue(new Error("I/O"));
    await userEvent.upload(screen.getByLabelText(/Load a .json file/), unreadable);
    await screen.findByText("Could not read that file.");
    expect(onImport).not.toHaveBeenCalled();
  });
});
