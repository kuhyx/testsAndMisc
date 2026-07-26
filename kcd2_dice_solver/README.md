# KCD2 Dice Solver

Pick which six dice and which badge to bring to a game of dice in
_Kingdom Come: Deliverance II_. Enter what you own; the solver evaluates every
loadout your inventory allows and reports the best one with the numbers behind
it.

**Live at <https://dice.kuhy.duckdns.org/>** — no terminal needed, and usable on
a phone. See [Deployment](#deployment) for how it gets there.

```bash
pnpm install
pnpm dev        # http://localhost:5174 — for working on it
pnpm test       # full suite
pnpm coverage   # 100% statements / branches / functions / lines
pnpm lint       # tsc --noEmit + eslint (strictTypeChecked)
pnpm build
```

## Entering an inventory

Three ways, all wired to the same state:

- **Click** a die's row to add one.
- **Scroll** the mouse wheel over its counter to step it up or down.
- **Search** by name — a fuzzy match, so `wei` finds _Weighted die_ and
  `paintb` finds _Painter's die B_. The same box filters the badge list.

The inventory is saved to `localStorage`, so it survives a reload.

All 43 dice are on screen at once at every width, phone included — there is no
inner scroll box. The column count and the type size are picked together from a
container query on the inventory panel (not the viewport: at a 1000px viewport
the panel is ~918px wide and one pixel later it drops to ~472px). Two rules
govern the choice: the list must fit above the fold, and the name column must
stay wide enough to tell `Painter's die B`, `G` and `R` apart, which is the
tightest constraint in the layout.

**The left column holds the dice grid and nothing else.** The title, the search
box and the badges all live on the right, where horizontal room is going spare,
rather than spending the vertical budget the grid needs. Badges are collapsed by
default — open, they are the tallest thing on the page. Stacked on a phone the
order becomes title/search, then the dice, then the results.

Because the grid owns that column outright, it is sized to **fill** the height
rather than sit in a band at the top: the 22 rows divide up whatever the
viewport has left, so the row height, the type and the −/+ buttons all scale
together off one `--die-row` value. A 1296px-tall screen gets a 52px row, 20px
type and 44px buttons — the accessibility minimum this layout cannot afford at
phone width, where the same rows are 20px. The type stops growing at 20px while
the row keeps going to 56px: past that the names start truncating, whereas a
taller row is pure gain. The scaling is deliberately **not** applied to the
stacked layout, where the title and search box sit above the grid and the height
is not the grid's to take.

## Moving an inventory between devices

`Import / export`, below the badges, offers three routes — set your dice up once
and carry them anywhere:

- **Download `.json`** and load it back with the file picker.
- **Copy JSON** to the clipboard, paste it into the box on the other device.
  (If the clipboard is unavailable — an insecure origin, say — the payload is
  put in the box so it can still be copied by hand.)
- **Copy link**: the inventory is base64url-encoded into the URL fragment.
  Opening that link elsewhere loads it. A realistic inventory is a ~150–260
  character URL.

Everything imported goes through one validator (`src/lib/inventoryIo.ts`), which
**keeps what it can and tells you what it dropped** rather than rejecting a
whole payload over one bad entry — a die added in a future game patch, or a link
a chat client truncated, should not cost you the rest of your inventory.

A link never silently overwrites what is already saved here. It loads, shows a
banner, and is only written to `localStorage` once you press **Keep** or edit
something. The fragment is cleared on arrival so a later reload does not
resurrect it.

## Deployment

`linux_configuration/scripts/single_use/features/setup_kcd2_dice_solver.sh`
builds `dist/` and serves it read-only from a loopback-bound `caddy` container
on `127.0.0.1:8089`, fronted by the shared `gitea-caddy` edge. It is idempotent;
`setup_kcd2_dice_solver.sh status` self-diagnoses.

Committing to `main` with changes under `kcd2_dice_solver/` republishes the site
via a `post-commit` hook that starts `kcd2-dice-build.service`. Two details that
are load-bearing rather than incidental:

- `deploy_build.sh` builds into `dist.staging/` and `rsync --delete`s into
  `dist/`. The container bind-mounts `dist/`, and a bind mount follows the
  **inode** — replacing the directory would detach the mount silently, and a
  plain `vite build` would empty it mid-request. The script asserts the inode is
  unchanged.
- The build unit sets `MemorySwapMax=0`. This box has zram (swap held in RAM),
  where a memory-capped cgroup without it thrashes instead of dying cleanly.

The rebuild builds the **working tree**, not the commit — an unrelated
uncommitted edit present at rebuild time will ship.

## How the recommendation is computed

**Scoring** (`src/core/scoring.ts`) is the wiki's table: 100 per one, 50 per
five, `1000` for three ones and `100 × face` otherwise, doubled for each die
beyond three, and 500/750/1500 for the three straights. A roll scores the best
_partition_ of its dice, which is a small memoised search.

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
Small inventories are enumerated exhaustively and reported as _provably
optimal_; larger ones use a multi-start steepest-ascent local search and are
reported as _not proven_.

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

- **Balatro's die** publishes no face probabilities: the wiki's dice-effect row
  for it is six unfilled `d` placeholders, and Inara does not list the die at
  all. Exactly **one** of its faces is the joker (Jimbo's grinning face), so it
  is modelled as a fair die whose 1 is replaced by that joker — the same face the
  Devil's head die replaces, which is why holding it alone counts as a 1. Only
  the uniform weights are an assumption; the joker's face is not.
- **The two joker faces score differently**, and the scorer keeps them apart. A
  Devil's head "matches any combination but never scores on its own", so it can
  never be the lone 1 or 5 that lets you hold a die; Balatro's joker can. Both
  are assumed able to fill in for any face of a combination, including one made
  entirely of jokers — the wiki's examples only ever pair a joker with natural
  dice, so that part is an assumption.
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
