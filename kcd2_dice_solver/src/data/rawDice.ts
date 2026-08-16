/**
 * The raw die table: every die's unnormalised face weights.
 *
 * Split out of data/dice.ts to keep it under the 250-line cap. Pure data;
 * dice.ts still owns normalise() and the derived DICE/DICE_BY_ID exports.
 */

import type { Face, Weights } from "./dice.ts";
export interface RawDie {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly weights: Weights;
  readonly wildcardFaces?: readonly Face[];
  readonly wildScoresAlone?: boolean;
}

import { RAW_DICE_A_M } from "./rawDiceAM.ts";
import { RAW_DICE_N_Z } from "./rawDiceNZ.ts";

export const RAW_DICE: readonly RawDie[] = [...RAW_DICE_A_M, ...RAW_DICE_N_Z];
