/** Result panel and inventory IO component tests. */

/** Badge picker and result panel component tests. */

/** Row, list and picker component tests. */

/**
 * Component tests for the three ways of entering an inventory: clicking a die,
 * scrolling the wheel over its counter, and fuzzy-searching by name.
 */

import { render, screen, } from "@testing-library/react";
import { ordinary, response } from "../test/fixtures.ts";
import { describe, expect, it, } from "vitest";
import type { Die } from "../data/dice.ts";
import type { SolveResponse } from "../core/solve.ts";
import { ResultPanel, } from "./ResultPanel.tsx";

/**
 * Apply the updater a component emitted, to assert on the resulting count.
 *
 * @param mock - The mocked onChange.
 * @param previous - The count it should be applied to.
 * @param call - Which call to read, counting from the end by default.
 * @returns The count the component asked for.
 */


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
