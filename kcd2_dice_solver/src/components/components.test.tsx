/**
 * Component tests for the three ways of entering an inventory: clicking a die,
 * scrolling the wheel over its counter, and fuzzy-searching by name.
 */

import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Die } from "../data/dice.ts";
import type { SolveResponse } from "../core/solve.ts";
import { BadgePicker } from "./BadgePicker.tsx";
import { DiceList } from "./DiceList.tsx";
import { DieRow, MAX_PER_DIE, highlightName } from "./DieRow.tsx";
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

  it("clamps a typed value", async () => {
    const onChange = vi.fn();
    render(<QuantityStepper label="Ordinary die" value={0} max={6} onChange={onChange} />);
    await userEvent.type(screen.getByLabelText("How many Ordinary die"), "9");
    expect(applied(onChange, 0)).toBe(6);
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
    const balatro: Die = { ...ordinary, id: "balatro", wildcardFaces: [1, 2, 3, 4, 5, 6] };
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
    expect(screen.getByLabelText("How many Weighted die")).toHaveValue(4);
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
