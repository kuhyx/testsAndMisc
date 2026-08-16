/**
 * Raw die weights, second half by id.
 *
 * Split out of data/rawDice.ts to keep each file under the 250-line cap.
 * Pure data; rawDice.ts concatenates the halves back into RAW_DICE.
 */

import type { RawDie } from "./rawDice.ts";

export const RAW_DICE_N_Z: readonly RawDie[] = [
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
