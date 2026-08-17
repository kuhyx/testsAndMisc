# Next session: split the `kcd2_dice_solver` files over the 250-line cap

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## The job

Four files in `kcd2_dice_solver/` are over the repo-wide 250-line cap. Split
all four, and prove each one with the project's own test suite:

| File                     | Lines | Over by | Has a dedicated test file     |
| ------------------------ | ----- | ------- | ----------------------------- |
| `src/core/search.ts`     | 417   | 167     | `src/core/search.test.ts`     |
| `src/core/scoring.ts`    | 361   | 111     | `src/core/scoring.test.ts`    |
| `src/core/badgeValue.ts` | 333   | 83      | `src/core/badgeValue.test.ts` |
| `src/App.tsx`            | 306   | 56      | (component — see note below)  |

**Do as many as you can, in that order** — biggest first, because `search.ts`
is the one most likely to teach you something the others reuse. Each file is an
independent, committable unit of work: finish one, verify it, commit it, then
start the next. Do not batch all four into one commit.

## Why this target set (read this — it changes how you work)

The last three sessions split **shell installers**, where the only way to prove
a split was a bespoke execution-trace harness, and where three of the last four
candidates turned out to be unverifiable or blocked. This target set is
categorically better:

- `npx vitest run` — **288 tests across 24 files, ~4 seconds**
- `npx vitest run --coverage` — **100% statements / branches / functions /
  lines, enforced by config thresholds** (`vite.config.ts`,
  `thresholds: { branches: 100, lines: 100, ... }`)
- `npm run lint` — `tsc --noEmit && eslint src`, currently clean

All three pass at `5dce82f`. That is your baseline: a split is correct when all
three still pass and coverage is still 100%. You do **not** need the shell trace
harness here, and you should not use it.

**Do not fall into the shell-split mindset.** No `trace_shell_split.sh`, no
`--prefix`, no manifest diffing. TypeScript with a real test suite and a 100%
coverage gate is a far stronger verifier than anything that harness produces.

## Baseline — capture before touching anything

```bash
cd ~/testsAndMisc/kcd2_dice_solver
npx vitest run                 # expect: 24 files, 288 tests, all passed
npx vitest run --coverage      # expect: 100% on all four metrics
npm run lint                   # expect: exit 0, no output
```

If any of these is already failing, stop and say so — something changed since
`5dce82f` and the baseline is not what this brief claims.

## The gate is LOCAL ONLY — nothing will catch you

`kcd2_dice_solver` has **no CI workflow** (`.github/workflows/` has entries for
billsplit, poker-stakes and reverse-survivors, but not this project) and is
**not covered by pre-commit**. So:

- A broken split here passes every commit hook and every push.
- You must run the three commands above yourself, before each commit.
- 100% coverage is enforced by vitest's own thresholds, not by any hook — if
  you move code into a new file and the coverage report drops below 100%, the
  `--coverage` run fails. That is your safety net; do not bypass it by
  splitting without re-running it.

## How to split (the actual method)

These are ES modules with named exports and explicit `.ts` import extensions.
The pattern:

1. **Read the file and find the seam.** `search.ts` exports `SET_SIZE`,
   `EXHAUSTIVE_LIMIT`, `InventoryEntry`, `SearchResult`, `SetCandidate`,
   `SearchOptions`, `groupInventory`, `countCandidates`, `findBestSet`. The
   types + small helpers vs. the search engine itself is the obvious cut.
2. **Move a coherent group into a sibling file** (`src/core/<name>.ts`).
3. **Re-export from the original** so every existing importer and every test
   keeps working unchanged:
   ```ts
   export { groupInventory, countCandidates } from "./searchGrouping.ts";
   export type { InventoryEntry, SetCandidate } from "./searchTypes.ts";
   ```
   This is the key move — it means you do **not** have to touch the test files
   or any consumer, which keeps the change small and the verification honest.
4. Re-run the three commands.

**Prefer re-exporting over rewriting imports.** If you find yourself editing
`*.test.ts` files, stop and ask whether a re-export would have avoided it. A
split that requires changing its own tests is a split that changed behaviour.

Check who imports the file before you move anything:

```bash
grep -rn 'from "./search.ts"\|from "../core/search.ts"' src/ | grep -v test
```

### `App.tsx` is different

It is a React component, not a pure module, and it has no dedicated
`App.test.ts`. Its coverage comes from other tests exercising it. Split it by
extracting **presentational subcomponents** or **custom hooks** into
`src/components/` or `src/hooks/`, not by cutting it at an arbitrary line.
Because its verification is weaker than the three core modules, do it **last**,
and if coverage drops below 100% after extracting, that is a real signal — the
extracted code is no longer being exercised. Fix it by making the extraction
smaller, not by lowering the threshold.

## Rules that will bite you

- **No suppressions, ever.** No `// eslint-disable`, no `@ts-ignore`, no
  `@ts-expect-error`, no lowering a coverage threshold. If a split seems to
  require one, the seam is wrong — restructure instead.
- **Do not touch `vite.config.ts`'s `thresholds` or `exclude` list.** Adding a
  new file to `exclude` to dodge coverage is the exact failure this gate exists
  to prevent.
- **Fixtures go in `src/test/`.** Coverage `exclude` matches `src/test/**` by
  path — a fixture placed beside the source gets counted as production code and
  breaks the 100% gate.
- **Match the existing import style**: explicit `.ts` extensions
  (`from "./counts.ts"`), `export type` for type-only re-exports. `tsc
--noEmit` will catch you if you get this wrong, so run `npm run lint`.
- Every commit touching code needs an evidence JSON in
  `docs/superpowers/evidence/<slug>-<date>.json`. Copy
  `docs/superpowers/evidence/template.json`; `validate_evidence.py` rejects
  empty `verification[]` and the phrases "should work", "probably fine",
  "seems right". **Staging ≥4 code files additionally requires a fresh
  `docs/superpowers/contracts/*.json`** — validate with
  `python3 meta/scripts/validate_contract.py <file>`. One file per commit keeps
  you under that threshold.
- `pre-commit run --files <changed>` before committing, as always.
- Work directly on `main`; commit and push. `git stash` and branch creation are
  blocked by hooks. `git push` runs `ci-mirror` (clean-venv install +
  `pre-commit --all-files` + pytest) and takes minutes — **never edit files
  while a push is running**. Background the push and keep reading the next
  file, but do not write.
- **Do not wire the file-length pre-commit hook.** It must land last, only once
  `bash ~/utils/scripts/check_file_length.sh --all` exits 0. 55 files are still
  over.

## Definition of done (per file)

- The file and everything split out of it are **under 250 lines**
  (`bash ~/utils/scripts/check_file_length.sh --all` no longer lists them).
- `npx vitest run` — still 288 tests, all passing.
- `npx vitest run --coverage` — still 100% on all four metrics.
- `npm run lint` — still exit 0.
- No test file was modified (or, if one was, you can explain exactly why a
  re-export could not avoid it).
- Zero suppressions added; `vite.config.ts` untouched.
- Committed and pushed with evidence.

## If you finish all four

`reverse_survivors/` (`src/core/sim.ts` 361, `src/core/types.ts` 295) is the
next-best set — same TypeScript shape, and it **does** have CI
(`.github/workflows/reverse-survivors-ci.yml`), so check what that workflow
gates on and run it locally before pushing.

After that, `bucket_catch/packages/frontend/src/hooks/usePuzzleGameLoop.ts`
(386) plus its 332-line test file.

## Do not attempt these (all measured, do not re-derive)

Shell targets, in the order someone would naively pick them:

- **`install_leechblock.sh` (485)** — traces perfectly (exit 0, 93 files, all
  hashes stable) and is still unsplittable in an entry+`lib/` shape. It is
  **deployed as a single file**: `install_pacman_wrapper.sh` copies it to
  `/usr/local/share/digital_wellbeing/`, and `pacman_wrapper.sh:831` prefers
  that deployed copy on **every pacman invocation**. An entry whose
  `SCRIPT_DIR` has no `lib/` dies on its first `source`. The trace cannot see
  this — it runs the repo copy. Splitting it is a two-file job (teach the
  pacman installer to deploy `lib/`, then re-baseline that file's 16-entry
  manifest).
- **`nvidia_troubleshoot.sh` (336)** — its trace dies at step 3 because
  `backup_file` writes `/etc/profile.backup.<stamp>`, a new _sibling_ in
  unbound `/etc`. 239 of its 336 lines never execute, so keeping the unproven
  ones in the entry leaves it at ~265 — still over the cap.
- **`block_compulsive_opening.sh` (705)** — same deployed-copy blocker;
  `install_all` copies the running script into `/usr/local/bin`.
- Blocked on named blockers, not line count: `check_and_enable_services.sh`
  (1301), `steam_compatibility.sh` (663), `libre_translate.sh` (488),
  `enforce_vbox_hosts.sh` (443). See `refactor_claude_todo_resume.md`.

`docs/shell-split-verification.md` is itself 272 lines and over the cap. Split
it only if you are already doing docs work; it is not urgent.

## Context: what landed in the last session

Four commits, all pushed, all verified:

- `26965ba` — `install_usage_monitoring.sh` 290 → 53-line entry + 5 libs
- `4eedc17` — `install_pacman_wrapper.sh` 316 → 128-line entry + 4 libs
- `6066201` — documented the deployed-copy blocker and two harness limits
- `5dce82f` — **deleted** `setup_thorium_startup.sh` (443) rather than
  splitting it: Thorium was removed from this machine in favour of
  chromium/librewolf, so the autostart it installs had been failing at every
  boot (`thorium-browser: line 33: /https://www.fitatu.com/app/planner: No such
file`) while systemd reported `status=0/SUCCESS`. Removing
  `check_thorium_startup()` from `check_and_enable_services.sh` was the
  load-bearing part — its `report_and_fix` re-ran the installer whenever the
  service was not enabled.

The lesson worth carrying: **check whether the thing is still used before
splitting it.** One of the four "targets" was dead code protecting a dead
feature, and deleting it was worth more than any split.

## Known pre-existing failures (not yours — do not fix)

- `bash linux_configuration/tests/test_security_hardening.sh` exits 1 with
  exactly one failure, `❌ FAIL: Compulsive block wrappers installed`. It
  belongs to `block_compulsive_opening.sh`.
- Repo-wide `jscpd` reports ~2.5% duplication from the working tree but 1.47%
  at HEAD in a clean worktree — the excess is entirely vendored
  `.venv`/`.ci-mirror-venv` site-packages. Don't chase it.
