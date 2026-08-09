# Reverse Survivors

Vampire Survivors, inverted: **you are the horde**. An AI-controlled survivor
kites, auto-fires, and levels up on its own. You spend a regenerating pool of
souls to spawn grunts, call escalating ring waves, and — once the seals break —
summon bosses. Kill the intruder before the 5:00 clock runs out, or watch dawn
break on your defeat.

## Play

```
npm install
npm run dev
```

- **Rusher / Stalker / Tank / Bomber** — single spawns at a random arena edge.
- **Splitter** — dies into three rushers. Killing it _creates_ pressure.
- **Artillery** — outranges the survivor (460 vs its 260) and holds station beyond
  reach. Its shells **stifle**, stretching the survivor's reload.
- **Warden** — faster than the survivor and **mires** it on contact.
- **Wave N** — a ring formation around the survivor; each call grows and costs more.
- **Colossus** (1:00), **Hivemind** (2:00) and **Leech** (3:00) — expensive, on
  cooldown. The Hivemind births free rushers; the Leech's touch **unknits** flesh,
  shutting off regeneration while it lives.
- **Ambush** places a unit right next to the survivor, at a premium.
  **Frenzy** drives the whole horde faster and harder for six seconds.
  **Rift** pins every spawn to one edge for ten, so you can mass a flank.
- The survivor gains XP per kill and rolls an upgrade per level
  (damage, fire rate, speed, vitality, regen, multishot). Time favors it. Pressure early.
- **Haunting / Normal / Crusade** scale enemy hp and speed, the survivor's health,
  your income, and the length of the night.

Placement is purchasable, never free. By default the director picks _what_ and
_when_ while the seeded RNG picks _where_ — Ambush and Rift buy that choice back,
one at a premium and the other at a cooldown.

> Earlier versions made the loss of placement control absolute. Ambush and Rift
> deliberately reverse that: the interesting decision turned out to be _what a
> placement is worth_, not being denied one.

All three debuffs need contact — a survivor that kites cleanly takes none of them —
and they refresh rather than stack, so a horde can never chain-lock the intruder.

## Quality gates

`npm run check` = typecheck + lint + tests with coverage. All three must pass; CI runs the same.

| Gate                                            | Enforced by                                                                                                                                                                                                     |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 100 % lines / branches / functions / statements | Vitest `coverage.thresholds` hard-set to 100 — the run fails below it                                                                                                                                           |
| Strictest typed linting                         | ESLint 10 flat config: `typescript-eslint` strictTypeChecked + stylisticTypeChecked, `@eslint-react` strict-type-checked, react-hooks (compiler-backed rules), react-refresh, vitest plugin, `--max-warnings 0` |
| Strictest compiler                              | TS `strict` + `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `verbatimModuleSyntax`, `erasableSyntaxOnly`, `noUnusedLocals/Parameters`, and friends                                                  |

Pinned stack (live-latest at build time): React 19.2.8 · Vite 8.2.0 · Vitest 4.1.10 ·
ESLint 10.8.0 · typescript-eslint 8.65.0 · TypeScript **6.0.3**.

> Why not TypeScript 7? TS 7 is the native (Go) compiler and does not expose the
> JS compiler API that typed linting needs — `typescript-eslint@8.65` caps its peer
> range at `<6.1.0`. TS 6.0.x is the newest compiler that still type-lints.

## Architecture (what makes 100 % honest)

- `src/core/status.ts` — the survivor's debuff timers. `isOn`/`factor` are written
  as arithmetic (`Math.min(1, Math.ceil(t))`) rather than comparisons, so the whole
  status system contributes **zero branches** to the coverage gate; consumers just
  multiply by the result. `applyStatus` uses `Math.max`, which is what makes
  refresh-not-stack a structural guarantee rather than a tuned number.
- `src/core/` — the whole game as pure-ish functions over a plain state object.
  Deterministic: seeded mulberry32 RNG lives _in_ the state; same seed + same
  action sequence ⇒ identical run. Behavior dispatch uses records instead of
  switches, and clamping uses `Math.min/max` instead of `if`, so there are no
  unreachable defensive branches to fake-cover.
- `src/render/draw.ts` — draws onto a minimal `Ctx2D` structural interface;
  tests assert against a typed stub. (This layer's tests are mock-assertion
  ritual, as warned — the assurance lives in the core suite.)
- `src/ui/` — thin React shell. The rAF loop clamps dt to 100 ms and holds its
  callback in a ref. `App` accepts a `boot` prop as an explicit test seam to
  reach both endings without simulating five minutes.
- `src/main.tsx` is covered too, including the missing-`#root` throw, via
  `vi.resetModules()` + dynamic import.

## Scripts

`dev` · `build` (tsc + vite) · `preview` · `typecheck` · `lint` · `test` ·
`coverage` · `check` (all gates)
