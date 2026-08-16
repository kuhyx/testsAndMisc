/**
 * The gold-tier badges.
 *
 * Split out of data/badgeTable.ts to keep it under the 250-line cap.
 */

import type { Badge } from "./badges.ts";
import { HEADSTART_POINTS } from "./headstart.ts";

export const GOLD_BADGES: readonly Badge[] = [
  // ---- Gold --------------------------------------------------------------
  {
    id: "gold_defence",
    name: "Gold Defence badge",
    description: "Use to cancel the effect of your opponent's gold badge.",
    tier: "gold",
    effect: { kind: "defence" },
  },
  {
    id: "gold_doppelganger",
    name: "Gold Doppelganger badge",
    description:
      "Using this badge will double the point value of your last throw. Can be used three times per game.",
    tier: "gold",
    effect: { kind: "doubleThrow", uses: 3 },
  },
  {
    id: "gold_emperors",
    name: "Gold Emperor's badge",
    description:
      "Using this badge, you will gain triple points for every 1+1+1 dice combination. Emperors don't lose.",
    tier: "gold",
    effect: { kind: "scoring", rules: { emperorTriple: true } },
  },
  {
    id: "gold_fortune",
    name: "Gold Fortune badge",
    description: "After your throw, you can reroll up to three dice. Can be used once per game.",
    tier: "gold",
    effect: { kind: "reroll", dice: 3, uses: 1 },
  },
  {
    id: "gold_headstart",
    name: "Gold Headstart badge",
    description: "Using this badge will give you a large point lead at the start of the game.",
    tier: "gold",
    effect: { kind: "headstart", points: HEADSTART_POINTS.gold },
  },
  {
    id: "gold_might",
    name: "Gold Might badge",
    description: "Using it will allow you to roll one extra die. Can be used three times per game.",
    tier: "gold",
    effect: { kind: "extraDice", dice: 1, uses: 3 },
  },
  {
    id: "gold_resurrection",
    name: "Gold Resurrection badge",
    description: "After an unlucky throw, you can throw again. Can be used three times per game.",
    tier: "gold",
    effect: { kind: "antibust", uses: 3 },
  },
  {
    id: "gold_swap_out",
    name: "Gold Swap-out badge",
    description:
      "After your throw, you can reroll two dice with the same value. Can be used once per game.",
    tier: "gold",
    effect: { kind: "reroll", dice: 2, uses: 1 },
  },
  {
    id: "gold_transmutation",
    name: "Gold Transmutation badge",
    description: "After your throw, change a die of your choosing to a 1. Can be used once per game.",
    tier: "gold",
    effect: { kind: "setDie", value: 1, uses: 1 },
  },
  {
    id: "gold_tyche",
    name: "Gold Tyche badge",
    description: "If you roll three sixes in a game, you'll always earn double points for them.",
    tier: "gold",
    effect: { kind: "scoring", rules: { tycheDouble: true } },
  },
  {
    id: "gold_warlord",
    name: "Gold Warlord badge",
    description: "You double the score of your turn. Can be used once per game.",
    tier: "gold",
    effect: { kind: "multiplier", factor: 2, uses: 1 },
  },
  {
    id: "gold_wedding",
    name: "Gold Wedding badge",
    description:
      "A memento of Agnes and Olda's big day. Using it allows you to reroll up to three dice. Can be used once per game.",
    tier: "gold",
    effect: { kind: "reroll", dice: 3, uses: 1 },
  },
  {
    id: "priests_advantage",
    name: "Priest's Advantage badge",
    description:
      "You gain a new dice formation called The Eye, consisting of the values 1, 3 and 5.",
    tier: "gold",
    effect: { kind: "scoring", rules: { eye: true } },
  },
];
