/**
 * The badge table: every badge's id, tier, description and effect.
 *
 * Split out of data/badges.ts to keep it under the 250-line cap. Pure data;
 * badges.ts still owns the scoring rules and the derived lookups.
 */

import type { Badge } from "./badges.ts";
import { HEADSTART_POINTS } from "./headstart.ts";
import { GOLD_BADGES } from "./badgeTableGold.ts";

export const BADGES: readonly Badge[] = [
  // ---- Tin ---------------------------------------------------------------
  {
    id: "carpenters_advantage",
    name: "Carpenter's Advantage badge",
    description: "You gain a new dice formation called the Cut, consisting of 3+5.",
    tier: "tin",
    effect: { kind: "scoring", rules: { cut: true } },
  },
  {
    id: "tin_defence",
    name: "Tin Defence badge",
    description: "Use to cancel the effect of your opponent's tin badge.",
    tier: "tin",
    effect: { kind: "defence" },
  },
  {
    id: "tin_doppelganger",
    name: "Tin Doppelganger badge",
    description: "Using it will double the score of your last roll. Can be used once per game.",
    tier: "tin",
    effect: { kind: "doubleThrow", uses: 1 },
  },
  {
    id: "tin_fortune",
    name: "Tin Fortune badge",
    description:
      "After your throw, you can reroll a die of your choosing. Can be used once per game.",
    tier: "tin",
    effect: { kind: "reroll", dice: 1, uses: 1 },
  },
  {
    id: "tin_headstart",
    name: "Tin Headstart badge",
    description: "You gain a small point lead at the start of the game.",
    tier: "tin",
    effect: { kind: "headstart", points: HEADSTART_POINTS.tin },
  },
  {
    id: "tin_might",
    name: "Tin Might badge",
    description: "Use it to add one extra die to your throw. Can be used once per game.",
    tier: "tin",
    effect: { kind: "extraDice", dice: 1, uses: 1 },
  },
  {
    id: "tin_resurrection",
    name: "Tin Resurrection badge",
    description: "After an unlucky throw, use this badge to throw again. Can be used once per game.",
    tier: "tin",
    effect: { kind: "antibust", uses: 1 },
  },
  {
    id: "tin_transmutation",
    name: "Tin Transmutation badge",
    description:
      "After your throw, you can change a die of your choosing to a 3. Can be used once per game.",
    tier: "tin",
    effect: { kind: "setDie", value: 3, uses: 1 },
  },
  {
    id: "tin_warlord",
    name: "Tin Warlord badge",
    description: "Used to gain a quarter more points from your turn. Can be used once per game.",
    tier: "tin",
    effect: { kind: "multiplier", factor: 1.25, uses: 1 },
  },

  // ---- Silver ------------------------------------------------------------
  {
    id: "bird_kings",
    name: "Bird king's badge",
    description:
      "The badge of the rightful king of the birds will allow you to roll an additional die. Can be used twice per game.",
    tier: "silver",
    effect: { kind: "extraDice", dice: 1, uses: 2 },
  },
  {
    id: "executioners_advantage",
    name: "Executioner's Advantage badge",
    description:
      "You gain a new dice combination called The Gallows, which consists of 4, 5 and 6.",
    tier: "silver",
    effect: { kind: "scoring", rules: { gallows: true } },
  },
  {
    id: "silver_defence",
    name: "Silver Defence badge",
    description: "Use to cancel the effect of your opponent's Silver badge in the game.",
    tier: "silver",
    effect: { kind: "defence" },
  },
  {
    id: "silver_doppelganger",
    name: "Silver Doppelganger badge",
    description: "You double the score of your last throw. Can be used twice per game.",
    tier: "silver",
    effect: { kind: "doubleThrow", uses: 2 },
  },
  {
    id: "silver_fortune",
    name: "Silver Fortune badge",
    description: "After your throw, you can reroll up to 2 dice. Can be used once per game.",
    tier: "silver",
    effect: { kind: "reroll", dice: 2, uses: 1 },
  },
  {
    id: "silver_headstart",
    name: "Silver Headstart badge",
    description: "Use it to get a moderate point lead at the start of the game.",
    tier: "silver",
    effect: { kind: "headstart", points: HEADSTART_POINTS.silver },
  },
  {
    id: "silver_might",
    name: "Silver Might badge",
    description: "Using it will allow you to roll one extra die. Can be used twice per game.",
    tier: "silver",
    effect: { kind: "extraDice", dice: 1, uses: 2 },
  },
  {
    id: "silver_resurrection",
    name: "Silver Resurrection badge",
    description:
      "When a throw doesn't go your way, use this badge to throw again. Can be used twice per game.",
    tier: "silver",
    effect: { kind: "antibust", uses: 2 },
  },
  {
    id: "silver_swap_out",
    name: "Silver Swap-out badge",
    description:
      "After your throw, you can reroll a die of your choosing. Can be used once per game.",
    tier: "silver",
    effect: { kind: "reroll", dice: 1, uses: 1 },
  },
  {
    id: "silver_transmutation",
    name: "Silver Transmutation badge",
    description:
      "After your throw, you can change a die of your choosing to a five. Can be used once per game.",
    tier: "silver",
    effect: { kind: "setDie", value: 5, uses: 1 },
  },
  {
    id: "silver_warlord",
    name: "Silver Warlord badge",
    description:
      "Using this badge will grant you 50% more points this round. Can be used once per game.",
    tier: "silver",
    effect: { kind: "multiplier", factor: 1.5, uses: 1 },
  },
  ...GOLD_BADGES,
];
