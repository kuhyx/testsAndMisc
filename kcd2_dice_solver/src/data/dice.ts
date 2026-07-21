/**
 * The 43 dice of Kingdom Come: Deliverance II, with their face distributions.
 *
 * Source (canonical): https://kingdom-come-deliverance.fandom.com/wiki/Dice/KCD2
 * Cross-check:        https://inara.cz/kingdom-come-2/items-dice/
 *
 * The wiki publishes percentages rounded to one decimal place, so most rows do
 * not sum to exactly 100. `normaliseDie` divides through by the row total, which
 * both fixes the rounding and lets us store the raw wiki numbers verbatim — the
 * literals below can be diffed against the wiki without arithmetic.
 *
 * Where Inara disagrees with the wiki the Inara figures are recorded in a
 * comment rather than silently reconciled; the wiki is authoritative here.
 */

/** A die face, 1-6. */
export type Face = 1 | 2 | 3 | 4 | 5 | 6;

/** Raw six-element weight vector, indexed by `face - 1`. */
export type Weights = readonly [number, number, number, number, number, number];

export interface Die {
  /** Stable identifier used in saved inventories and worker messages. */
  readonly id: string;
  /** Display name exactly as the wiki spells it. */
  readonly name: string;
  /** Flavour text from the wiki, shown as a tooltip. */
  readonly description: string;
  /**
   * Probability of each face, already normalised to sum to 1.
   * For faces listed as wildcards this is still the probability of *landing* on
   * that face; the scoring engine then treats the result as a substitute.
   */
  readonly weights: Weights;
  /**
   * Faces that act as a wildcard ("substitute") and may count as any value.
   * Empty for all but two dice.
   */
  readonly wildcardFaces: readonly Face[];
}

/**
 * Divide a raw weight vector by its total so the probabilities sum to exactly 1.
 *
 * @param raw - Wiki percentages (or any non-negative weights) for faces 1-6.
 * @returns The same vector scaled to sum to 1.
 */
export function normalise(raw: Weights): Weights {
  const total = raw[0] + raw[1] + raw[2] + raw[3] + raw[4] + raw[5];
  return [
    raw[0] / total,
    raw[1] / total,
    raw[2] / total,
    raw[3] / total,
    raw[4] / total,
    raw[5] / total,
  ];
}

interface RawDie {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly weights: Weights;
  readonly wildcardFaces?: readonly Face[];
}

const RAW_DICE: readonly RawDie[] = [
  {
    id: "aranka",
    name: "Aranka's die",
    description:
      "Aranka gave me this die to make it easier for me to play against her husband.",
    weights: [28.6, 4.8, 28.6, 4.8, 28.6, 4.8],
  },
  {
    id: "balatro",
    name: "Balatro's die",
    description:
      "A die crafted by the balatro Jimbo, marked with his grinning face. When it lands, you get to choose how it's counted!",
    // The wiki lists no percentages for this die. Every face is a wildcard, so
    // the face distribution is irrelevant to scoring: whichever face lands, the
    // player chooses its value. Modelled as uniform with all six faces wild.
    weights: [1, 1, 1, 1, 1, 1],
    wildcardFaces: [1, 2, 3, 4, 5, 6],
  },
  {
    id: "cautious_cheater",
    name: "Cautious cheater's die",
    description:
      "A die modified by an expert. It is precisely loaded, but also inconspicuous.",
    weights: [23.8, 14.3, 9.5, 14.3, 23.8, 14.3],
  },
  {
    id: "ci",
    name: "Ci die",
    description:
      "The second in the line of the demonic dice, she likes to get lost, but when she's with her sisters she's very strong.",
    // Inara: 14.3 / 14.3 / 14.3 / 14.3 / 14.3 / 28.6
    weights: [13, 13, 13, 13, 13, 34.8],
  },
  {
    id: "devils_head",
    name: "Devil's head die",
    description:
      "A die that feels hot to the touch. In place of a one it has a devil's head, which is not something folk like to gaze upon…",
    // Face 1 is the devil's head, which the wiki scoring table marks "Subst" —
    // it substitutes for any value.
    weights: [16.7, 16.7, 16.7, 16.7, 16.7, 16.7],
    wildcardFaces: [1],
  },
  {
    id: "misfortune",
    name: "Die of misfortune",
    description:
      "They say that when it rains, it pours. But if you play with this die, the only thing pouring will be your tears.",
    weights: [4.5, 22.7, 22.7, 22.7, 22.7, 4.5],
  },
  {
    id: "even",
    name: "Even die",
    description: "A die loaded in favour of even numbers.",
    weights: [6.7, 26.7, 6.7, 26.7, 6.7, 26.7],
  },
  {
    id: "favourable",
    name: "Favourable die",
    description: "A playing die that brings luck more often than you'd expect.",
    weights: [33.3, 0, 5.6, 5.6, 33.3, 22.2],
  },
  {
    id: "fer",
    name: "Fer die",
    description: "The third and last in the line of demonic dice.",
    // Inara: 14.3 / 14.3 / 14.3 / 14.3 / 14.3 / 28.6
    weights: [13, 13, 13, 13, 13, 34.8],
  },
  {
    id: "greasy",
    name: "Greasy die",
    description:
      "A more reliable die than a normal one, but it cannot be relied on for everything.",
    weights: [17.6, 11.8, 17.6, 11.7, 17.6, 23.5],
  },
  {
    id: "grimy",
    name: "Grimy die",
    description:
      "One could say it will get you out of the frying pan into the fire. And sometimes it will let you stew in your own juice.",
    weights: [6.2, 31.2, 6.2, 6.2, 43.7, 6.2],
  },
  {
    id: "grozav",
    name: "Grozav's lucky die",
    description: "It is actually not all that lucky, but don't tell anyone!",
    weights: [6.7, 66.7, 6.7, 6.7, 6.7, 6.7],
  },
  {
    id: "heavenly_kingdom",
    name: "Heavenly Kingdom die",
    description:
      "A miraculous playing die, sent from the Heavenly Kingdom to the kingdom of men.",
    weights: [36.8, 10.5, 10.5, 10.5, 10.5, 21],
  },
  {
    id: "holy_trinity",
    name: "Holy Trinity die",
    description:
      "A consecrated die commemorating the Holy Trinity, especially by rolling threes.",
    // Inara: 21.1 / 26.3 / 36.8 / 5.3 / 5.3 / 5.3
    weights: [18.2, 22.7, 45.4, 4.5, 4.5, 4.5],
  },
  {
    id: "hugo",
    name: "Hugo's die",
    description: "A die of the most loyal regular at the Hole. It bears his likeness.",
    weights: [16.7, 16.7, 16.7, 16.7, 16.7, 16.7],
  },
  {
    id: "kings",
    name: "King's die",
    description:
      "An anointed head has no need of a loaded die, since he is always right and can never lose.",
    weights: [12.5, 18.7, 21.9, 25, 12.5, 9.4],
  },
  {
    id: "lousy_gambler",
    name: "Lousy gambler's die",
    description: "A shoddy loaded die. It's quite noticeably unbalanced.",
    weights: [10, 15, 10, 15, 35, 15],
  },
  {
    id: "lu",
    name: "Lu die",
    description: "The first of the line of demonic dice.",
    // Inara: 14.3 / 14.3 / 14.3 / 14.3 / 14.3 / 28.6
    weights: [13, 13, 13, 13, 13, 34.8],
  },
  {
    id: "lucky",
    name: "Lucky die",
    description:
      "When fortune smiles on you, smile back. Otherwise you'll look suspicious.",
    weights: [27.3, 4.5, 9.1, 13.6, 18.2, 27.3],
  },
  {
    id: "mathematician",
    name: "Mathematician's die",
    description:
      "A die loaded based on the work of a forgotten mathematician. It may be better suited to solving equations than playing dice.",
    weights: [16.7, 20.8, 25, 29.2, 4.2, 4.2],
  },
  {
    id: "molar",
    name: "Molar die",
    description:
      "A die made out of a molar tooth. It's probably better not to know who it came from.",
    weights: [16.7, 16.7, 16.7, 16.7, 16.7, 16.7],
  },
  {
    id: "monk",
    name: "Monk's die",
    description:
      "No one knows for sure whether it was blessed by a holy man or just spat on by a drunken monk. Either way, the die rolls... sort of.",
    weights: [40, 40, 5, 5, 5, 5],
  },
  {
    id: "mother_of_pearl",
    name: "Mother-of-pearl die",
    description:
      "A rare pink mother-of-pearl die. Said to bring luck in games, but misfortune in love.",
    weights: [25, 8.3, 8.3, 8.3, 25, 25],
  },
  {
    id: "odd",
    name: "Odd die",
    description: "A die loaded to favour odd numbers.",
    weights: [26.7, 6.7, 26.7, 6.7, 26.7, 6.7],
  },
  {
    id: "ordinary",
    name: "Ordinary die",
    description: "An ordinary playing die.",
    weights: [16.7, 16.7, 16.7, 16.7, 16.7, 16.7],
  },
  {
    id: "painted",
    name: "Painted die",
    description:
      "One of the dice coloured using modern techniques that hide the attempt to load it.",
    // Inara: 20 / 6.7 / 6.7 / 6.7 / 40 / 20
    weights: [18.7, 6.2, 6.2, 6.2, 43.7, 18.7],
  },
  {
    id: "painters_b",
    name: "Painter's die B",
    description: "Painter Voyta's blue-painted die.",
    weights: [9.1, 27.2, 18.2, 18.2, 18.2, 9.1],
  },
  {
    id: "painters_g",
    name: "Painter's die G",
    description: "Painter Voyta's green-painted die.",
    weights: [9.1, 27.2, 18.2, 18.2, 18.2, 9.1],
  },
  {
    id: "painters_r",
    name: "Painter's die R",
    description: "Painter Voyta's red-painted die.",
    weights: [9.1, 27.2, 18.2, 18.2, 18.2, 9.1],
  },
  {
    id: "pie",
    name: "Pie die",
    description:
      "Doesn't look particularly tasty, but it's well balanced towards lower numbers.",
    weights: [46.2, 7.7, 23.1, 23.1, 0, 0],
  },
  {
    id: "premolar",
    name: "Premolar die",
    description: "A playing die made from a premolar tooth.",
    weights: [16.7, 16.7, 16.7, 16.7, 16.7, 16.7],
  },
  {
    id: "sad_greaser",
    name: "Sad Greaser's die",
    description: "A blue die mirroring the sadness of its original owner.",
    weights: [26.1, 26.1, 4.3, 4.3, 26.1, 13],
  },
  {
    id: "saint_antiochus",
    name: "Saint Antiochus' die",
    description:
      "The Saint Antiochus' die always rolls a 3. Not 2. And especially not 4.",
    weights: [20, 6.7, 40, 6.7, 6.7, 20],
  },
  {
    id: "shrinking",
    name: "Shrinking die",
    description:
      "A very lightly loaded die. One can barely differentiate it from an ordinary die.",
    weights: [22.2, 11.1, 11.1, 11.1, 11.1, 33.3],
  },
  {
    id: "st_stephens",
    name: "St. Stephen's die",
    description:
      "A die blessed by St. Stephen, guaranteeing favourable numbers in the game and protection from loose stones.",
    weights: [16.7, 16.7, 16.7, 16.7, 16.7, 16.7],
  },
  {
    id: "strip",
    name: "Strip die",
    description: "Legend has it this die will help you undress many a wench.",
    weights: [25, 12.5, 12.5, 12.5, 18.8, 18.8],
  },
  {
    id: "tengri",
    name: "Tengri's die",
    description:
      "This one appeared to me after I won on all of Tengri's tracks. A little token of my tremendous success, perhaps?",
    weights: [28.5, 14.3, 14.3, 14.3, 14.3, 14.3],
  },
  {
    id: "trinity",
    name: "Trinity die",
    description: "For some reason, this die usually rolls a three. Why?",
    // Inara: 18.2 / 9.1 / 36.4 / 9.1 / 18.2 / 9.1
    weights: [12.5, 6.2, 56.2, 6.2, 12.5, 6.2],
  },
  {
    id: "unbalanced",
    name: "Unbalanced die",
    description:
      "A playing die someone tried to load to his advantage, but didn't do a very good job.",
    weights: [25, 33.3, 8.3, 8.3, 16.7, 8.3],
  },
  {
    id: "unlucky",
    name: "Unlucky die",
    description:
      "Sometimes Lady Luck is on your side, sometimes she isn't. With this die, she most likely isn't.",
    weights: [9.1, 27.3, 18.2, 18.2, 18.2, 9.1],
  },
  {
    id: "wagoner",
    name: "Wagoner's die",
    description:
      "According to legend, this die belonged to the famous Roman charioteer Arnuldus, whose tactics consisted of tiring his opponents or lulling them to sleep.",
    weights: [5.6, 27.8, 33.3, 11.1, 11.1, 11.1],
  },
  {
    id: "weighted",
    name: "Weighted die",
    description:
      "A mysterious playing die found in a ruined house. Suspiciously, it tends to land on 1.",
    weights: [66.7, 6.7, 6.7, 6.7, 6.7, 6.7],
  },
  {
    id: "wisdom_tooth",
    name: "Wisdom tooth die",
    description: "A playing die made from a wisdom tooth.",
    weights: [16.7, 16.7, 16.7, 16.7, 16.7, 16.7],
  },
];

/** All dice, sorted by display name, with weights normalised to sum to 1. */
export const DICE: readonly Die[] = RAW_DICE.map((raw) => ({
  id: raw.id,
  name: raw.name,
  description: raw.description,
  weights: normalise(raw.weights),
  wildcardFaces: raw.wildcardFaces ?? [],
})).sort((a, b) => a.name.localeCompare(b.name));

/** Lookup from die id to die, for resolving saved inventories. */
export const DICE_BY_ID: ReadonlyMap<string, Die> = new Map(
  DICE.map((die) => [die.id, die]),
);
