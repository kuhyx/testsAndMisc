/**
 * The one entrypoint the UI calls: inventory in, recommendation out.
 *
 * Kept free of any DOM or React reference so it runs unchanged on the main
 * thread (in tests) and inside the Web Worker (in the app).
 */

import type { FormationValues } from "../data/badges.ts";
import { BASE_RULES, DEFAULT_FORMATION_VALUES } from "../data/badges.ts";
import { DICE_BY_ID } from "../data/dice.ts";
import type { Die } from "../data/dice.ts";
import { recommendBadges } from "./badgeValue.ts";
import type { BadgeRecommendation } from "./badgeValue.ts";
import type { Evaluation } from "./evaluate.ts";
import { Scorer } from "./scoring.ts";
import { findBestSet } from "./search.ts";
import type { InventoryEntry, SearchOptions } from "./search.ts";
import { DEFAULT_POLICY, NO_CHARGES, simulateTurns } from "./simulate.ts";
import type { SimulationResult, TurnPolicy } from "./simulate.ts";

/** What the UI sends to the solver. */
export interface SolveRequest {
  /** Owned dice, as die id to count. */
  readonly diceCounts: Readonly<Record<string, number>>;
  /** Owned badge ids. */
  readonly badgeIds: readonly string[];
  /** UNVERIFIED formation point values, editable in the UI. */
  readonly formationValues?: FormationValues;
  /** Push-your-luck policy for the simulated turn EV. */
  readonly policy?: TurnPolicy;
  /** Turns to simulate for the headline turn EV figure. */
  readonly simulationTurns?: number;
  /** Search tuning; the UI leaves this at its defaults. */
  readonly searchOptions?: SearchOptions;
}

/** What the solver sends back. */
export interface SolveResponse {
  /** The recommended six dice. */
  readonly dice: readonly Die[];
  /** Exact single-roll evaluation of that set. */
  readonly evaluation: Evaluation;
  /** Simulated full-turn value of that set. */
  readonly simulation: SimulationResult;
  /** True when the whole search space was enumerated. */
  readonly optimal: boolean;
  /** Runner-up loadouts, best first. */
  readonly alternatives: readonly { dice: readonly Die[]; evaluation: Evaluation }[];
  /** Best badge per owned tier. */
  readonly badges: readonly BadgeRecommendation[];
  /** Total dice in the inventory, echoed back for the UI's status line. */
  readonly inventorySize: number;
}

/**
 * Turn a die-id-to-count record into inventory entries, dropping unknown ids.
 *
 * @param counts - Die ids mapped to how many are owned.
 * @returns Inventory entries for ids that exist in the game data.
 */
export function toInventory(counts: Readonly<Record<string, number>>): InventoryEntry[] {
  const entries: InventoryEntry[] = [];
  for (const [id, count] of Object.entries(counts)) {
    const die = DICE_BY_ID.get(id);
    if (die && count > 0) {
      entries.push({ die, count });
    }
  }
  return entries;
}

/** Turns simulated for the headline turn-EV figure. */
export const DEFAULT_SIMULATION_TURNS = 20_000;

/**
 * Solve an inventory: pick the best six dice and rank the owned badges.
 *
 * @param request - Inventory and options.
 * @returns The recommended loadout with both objectives and badge advice.
 * @throws If the inventory holds fewer than six dice.
 */
export function solve(request: SolveRequest): SolveResponse {
  const inventory = toInventory(request.diceCounts);
  const formationValues = request.formationValues ?? DEFAULT_FORMATION_VALUES;
  const policy = request.policy ?? DEFAULT_POLICY;
  const searchOptions = request.searchOptions ?? {};

  const scorer = new Scorer(BASE_RULES, formationValues);
  const search = findBestSet(inventory, scorer, searchOptions);
  const simulation = simulateTurns(
    search.dice,
    scorer,
    request.simulationTurns ?? DEFAULT_SIMULATION_TURNS,
    policy,
    NO_CHARGES,
  );

  const badges = recommendBadges(new Set(request.badgeIds), {
    inventory,
    baselineDice: search.dice,
    formationValues,
    policy,
    seed: 0x5eed,
    searchOptions,
  });

  return {
    dice: search.dice,
    evaluation: search.evaluation,
    simulation,
    optimal: search.optimal,
    alternatives: search.alternatives,
    badges,
    inventorySize: inventory.reduce((sum, entry) => sum + entry.count, 0),
  };
}
