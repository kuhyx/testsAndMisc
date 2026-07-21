# KCD2 Dice Solver

Pick which six dice and which badge to bring to a game of dice in
*Kingdom Come: Deliverance II*. Enter what you own; the solver evaluates every
loadout your inventory allows and reports the best one with the numbers behind
it.

```bash
pnpm install
pnpm dev        # http://localhost:5174
pnpm test       # full suite
pnpm coverage   # 100% statements / branches / functions / lines
pnpm lint       # tsc --noEmit + eslint (strictTypeChecked)
pnpm build
```

## Entering an inventory

Three ways, all wired to the same state:

- **Click** a die's row to add one.
- **Scroll** the mouse wheel over its counter to step it up or down.
- **Search** by name — a fuzzy match, so `wei` finds *Weighted die* and
  `paintb` finds *Painter's die B*. The same box filters the badge list.

The inventory is saved to `localStorage`, so it survives a reload.

## How the recommendation is computed

**Scoring** (`src/core/scoring.ts`) is the wiki's table: 100 per one, 50 per
five, `1000` for three ones and `100 × face` otherwise, doubled for each die
beyond three, and 500/750/1500 for the three straights. A roll scores the best
*partition* of its dice, which is a small memoised search.

**Expected value** (`src/core/evaluate.ts`) is exact, not sampled. Scoring
depends only on the multiset of faces, so the six dice are convolved into a
distribution over count vectors — at most 924 of them, against 6⁶ = 46,656
ordered outcomes. Those vectors stay packed as integers end to end, so the
scorer's memo is keyed on them directly. `evaluate.test.ts` checks the result
against a naive full enumeration that shares none of that machinery.

**The search** (`src/core/search.ts`) evaluates whole sets, because a Farkle
set's value is not the sum of its dice — ranking dice individually and taking
the top six is simply wrong. Dice with identical distributions are pooled
first (nine of the game's dice are plain uniform dice under different names).
Small inventories are enumerated exhaustively and reported as *provably
optimal*; larger ones use a multi-start steepest-ascent local search and are
reported as *not proven*.

**Turn value** (`src/core/simulate.ts`) is a Monte Carlo simulation, and unlike
the above it depends on how you play. The policy is stated explicitly in that
file and its knobs are exposed rather than buried: hold the subset maximising
`points + 60 × dice-left`, bank at 300.

**Badges** (`src/core/badgeValue.ts`) split in two. The five that change the
scoring table are valued on the exact EV delta after re-running the whole dice
search with the rule on — so equipping one can change which dice you should
bring. The rest are simulated one charge at a time, with each turn drawing from
its own seeded stream so the comparison is paired and the measured difference is
the badge rather than a diverged random sequence.

Nothing uses `Math.random`; every random source is a seeded `mulberry32`, so
every number here is reproducible.

## What the numbers are not

- **Balatro's die** publishes no face probabilities. Every face is a wildcard
  ("you get to choose how it's counted"), so it is modelled as always resolving
  in your favour — which means it always wins if you own it.
- **The three "Advantage" formations** (Carpenter's Cut, Executioner's Gallows,
  Priest's Eye) and the **Headstart** point leads have no published values. The
  constants used are marked `UNVERIFIED` in `src/data/badges.ts`. Correct them
  from the game's help screen if you have it open.
- **Badge point-per-game figures** are estimates for ranking badges against each
  other, not a prediction of a scoreline.
- The wiki and [Inara](https://inara.cz/kingdom-come-2/items-dice/) **disagree**
  on about six dice (Ci/Fer/Lu, Painted, Trinity, Holy Trinity, Devil's head).
  The [fandom wiki](https://kingdom-come-deliverance.fandom.com/wiki/Dice/KCD2)
  is treated as canonical; the Inara figures sit in a comment beside each
  conflicting entry.
