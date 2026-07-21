/**
 * The 33 dice badges of Kingdom Come: Deliverance II.
 *
 * Source: https://kingdom-come-deliverance.fandom.com/wiki/Dice/KCD2
 *
 * Badges only take effect when the opponent also brings a badge of the same
 * tier, so the solver recommends one badge per tier rather than a single
 * overall winner.
 *
 * UNVERIFIED CONSTANTS
 * --------------------
 * Neither the fandom wiki nor Inara publishes numeric values for the three
 * "Advantage" formations or for the Headstart point leads — the in-game text is
 * qualitative ("a small point lead"). The constants below are explicit,
 * editable guesses rather than invented data buried in a table; the UI exposes
 * them so they can be corrected from the game's own help screen.
 */

export type BadgeTier = "tin" | "silver" | "gold";

/**
 * Extra scoring formations and multipliers granted by the five badges that
 * change the scoring rules themselves. These are threaded through `bestScore`,
 * so enabling one can change which six dice are optimal.
 */
export interface ScoringRules {
  /** Carpenter's Advantage: the "Cut", a 3 and a 5 together. */
  readonly cut: boolean;
  /** Executioner's Advantage: "The Gallows", a 4, a 5 and a 6. */
  readonly gallows: boolean;
  /** Priest's Advantage: "The Eye", a 1, a 3 and a 5. */
  readonly eye: boolean;
  /** Gold Emperor's badge: triple points for every 1+1+1. */
  readonly emperorTriple: boolean;
  /** Gold Tyche badge: double points for three sixes. */
  readonly tycheDouble: boolean;
}

/** Rule set with every scoring badge switched off. */
export const BASE_RULES: ScoringRules = {
  cut: false,
  gallows: false,
  eye: false,
  emperorTriple: false,
  tycheDouble: false,
};

/**
 * Point values of the three badge-granted formations.
 *
 * UNVERIFIED. Defaulted to what the constituent dice are worth under the
 * ordinary rules, i.e. the formation lets you *use* dice that would otherwise
 * be dead but grants no bonus on top:
 *   Cut    3+5   -> 50 (the 5) is the only ordinary value, rounded up to 150
 *   Gallows 4+5+6 -> 50 (the 5), rounded up to 250
 *   Eye    1+3+5 -> 150 (the 1 and the 5), rounded up to 300
 */
export interface FormationValues {
  readonly cut: number;
  readonly gallows: number;
  readonly eye: number;
}

/** Default, UNVERIFIED formation point values. Editable in the UI. */
export const DEFAULT_FORMATION_VALUES: FormationValues = {
  cut: 150,
  gallows: 250,
  eye: 300,
};

/**
 * Point leads granted by the Headstart badges.
 *
 * UNVERIFIED. The wiki only says "small" / "moderate" / "large".
 */
export const HEADSTART_POINTS: Readonly<Record<BadgeTier, number>> = {
  tin: 250,
  silver: 500,
  gold: 1000,
};

/** What a badge actually does, as a discriminated union. */
export type BadgeEffect =
  /** Changes the scoring table. Evaluated jointly with the dice set. */
  | { readonly kind: "scoring"; readonly rules: Partial<ScoringRules> }
  /** Roll `dice` extra dice, `uses` times per game. */
  | { readonly kind: "extraDice"; readonly dice: number; readonly uses: number }
  /** Reroll up to `dice` dice of your choosing, `uses` times per game. */
  | { readonly kind: "reroll"; readonly dice: number; readonly uses: number }
  /** Re-throw after a bust, `uses` times per game. */
  | { readonly kind: "antibust"; readonly uses: number }
  /** Double the point value of your last throw, `uses` times per game. */
  | { readonly kind: "doubleThrow"; readonly uses: number }
  /** Multiply the whole turn's score by `factor`, `uses` times per game. */
  | { readonly kind: "multiplier"; readonly factor: number; readonly uses: number }
  /** Start the game `points` ahead. */
  | { readonly kind: "headstart"; readonly points: number }
  /** Change a die of your choosing to `value`, `uses` times per game. */
  | { readonly kind: "setDie"; readonly value: number; readonly uses: number }
  /** Purely reactive: cancels an opponent badge of the same tier. */
  | { readonly kind: "defence" };

export interface Badge {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly tier: BadgeTier;
  readonly effect: BadgeEffect;
}

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

/** Lookup from badge id to badge. */
export const BADGES_BY_ID: ReadonlyMap<string, Badge> = new Map(
  BADGES.map((badge) => [badge.id, badge]),
);

/** Tiers in ascending power order, for grouping in the UI and the results. */
export const TIERS: readonly BadgeTier[] = ["tin", "silver", "gold"];
