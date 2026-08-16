/** Row, list and picker component tests. */

/**
 * Component tests for the three ways of entering an inventory: clicking a die,
 * scrolling the wheel over its counter, and fuzzy-searching by name.
 */

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MAX_PER_DIE } from "../data/dice.ts";
import type { Die } from "../data/dice.ts";
import { DiceList } from "./DiceList.tsx";
import { DieRow, } from "./DieRow.tsx";

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
