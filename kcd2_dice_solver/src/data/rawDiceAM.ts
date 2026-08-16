/**
 * Raw die weights, first half by id.
 *
 * Split out of data/rawDice.ts to keep each file under the 250-line cap.
 * Pure data; rawDice.ts concatenates the halves back into RAW_DICE.
 */

import type { RawDie } from "./rawDice.ts";

export const RAW_DICE_A_M: readonly RawDie[] = [
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
    // Only ONE face is the joker — Jimbo's grinning face, visible on the item
    // icon. The wiki's dice-effect table for this die is `{{Dice effect|d|d|d|d|
    // d|d}}`: six *unfilled placeholders* that render as "d%", not six wildcards.
    // Reading them as wildcards is what made this die look unbeatable.
    //
    // No source publishes its side weights (the wiki cells are the placeholders
    // above and Inara omits the die entirely), so uniform is an assumption, kept
    // as [1,1,1,1,1,1] rather than a fake "16.7" so it cannot be mistaken for a
    // transcribed figure.
    //
    // The joker replaces the one — confirmed by the player, who owns the game —
    // like the Devil's head die it is explicitly compared to. That is also why
    // holding it alone counts as a 1: the joker sits where the 1 used to be, so
    // the die has no plain single pip at all.
    weights: [1, 1, 1, 1, 1, 1],
    wildcardFaces: [1],
    // "When it lands, you get to choose how it's counted!" — and, unlike the
    // Devil's head, "picking it alone will count as if you threw 1".
    wildScoresAlone: true,
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
    // it substitutes for any value, but per the die's own page it "acts as a
    // joker, matching any combination but never scoring on its own", so it
    // cannot be the lone 1 or 5 that lets you hold a die.
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
];
