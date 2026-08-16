/**
 * Shared component-test fixtures.
 *
 * In src/test/ because vite.config.ts excludes that path from coverage;
 * a fixture beside the source would be counted as production code and
 * break the 100% gate.
 */

import type { Die } from "../data/dice.ts";
import type { SolveResponse } from "../core/solve.ts";

export const ordinary: Die = {
  id: "ordinary",
  name: "Ordinary die",
  description: "An ordinary playing die.",
  weights: [1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6],
  wildcardFaces: [],
  wildScoresAlone: false,
};

export const response: SolveResponse = {
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
