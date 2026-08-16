/** Badge picker and result panel component tests. */

/** Row, list and picker component tests. */

/**
 * Component tests for the three ways of entering an inventory: clicking a die,
 * scrolling the wheel over its counter, and fuzzy-searching by name.
 */

import { render, screen, } from "@testing-library/react";
import { ordinary } from "../test/fixtures.ts";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Die } from "../data/dice.ts";
import { BadgePicker } from "./BadgePicker.tsx";
import { summariseDice } from "./ResultPanel.tsx";

/**
 * Apply the updater a component emitted, to assert on the resulting count.
 *
 * @param mock - The mocked onChange.
 * @param previous - The count it should be applied to.
 * @param call - Which call to read, counting from the end by default.
 * @returns The count the component asked for.
 */


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
