# Next session: Phase 3 — finish wiring the shell-coverage ratchet

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

**Phases 1 and 2 are DONE.** The 250-line cap is at zero and enforced; the CI
gates are wired.

**Phase 3 is BUILT but NOT ENFORCED** (commit `3278bebd`). The three scoping
questions below were answered without the user, because the session that built
it was non-interactive — a grilling round would have ended the turn with
nothing delivered. **The user can still veto any of these cheaply**, since the
gate is not yet in the hook chain:

- **Q1 Scope → ratchet.** 115 pre-existing libraries are exempt via
  `meta/shell-coverage-allowlist.txt`; any library not on that list must be
  covered, so a new one cannot enter untested. Unrelated commits are never
  blocked (verified). **Exemption is static** — editing an allowlisted library
  is allowed and does not demand tests. An entry leaves the list only when its
  directory gains a suite.
- **Q2 Bar → presence, not a percentage — but NOT because a percentage is
  impossible.** An earlier session on 2026-08-21 reached **100% (38/38) on
  `setup_night_lockdown.sh` with no source changes and no suppressions**, using
  a user-namespace jail, with containment verified by canary. The generic
  runner then got **75% (57/76) on `pacman_wrapper.sh`**, because each subject
  needs its own mount analysis. So a numeric bar is reachable but costs bespoke
  per-file work — presence is the floor that can land today, and a percentage
  can layer on top later. See
  `docs/superpowers/evidence/phase3-namespace-jail-feasibility-2026-08-21.json`
  and `meta/scripts/shell_coverage.sh`. **Both jail subjects were entry
  scripts, which Q3 puts out of scope**, so nothing is yet measured for the 198
  `lib/` files.
- **Q3 Which files → `.sh` under a `lib/` dir**, excluding `lib/tests/` and
  `lib/payloads/`. Entry scripts are orchestration whose bodies are untestable.

## The one thing left to do

`meta/scripts/check_shell_coverage.sh` works standalone but is **not in
`.pre-commit-config.yaml`** — that edit was denied as a sensitive file. Add
this block after the `file-length-cap` hook (note `files:`, **not** `--all`;
per-file is what makes it a ratchet):

```yaml
- id: shell-coverage-ratchet
  name: Shell libraries must have a test suite
  entry: bash meta/scripts/check_shell_coverage.sh
  language: system
  files: \.sh$
```

Then re-verify the negative case before trusting it:
`bash meta/scripts/check_shell_coverage.sh meta/scripts/check_file_length.sh`
must exit 0 (an unrelated entry script must never block a commit).

**Do not run `--seed` after adding an untested library** — it would rewrite the
allowlist and silently exempt it. The list is shrink-only; nothing mechanically
enforces that yet.

## Chipping away at the 115

198 in-scope libraries: 115 exempt, 83 already covered. The allowlist is
concentrated: `single_use/features/lib` (45), `single_use/fixes/lib` (22),
`phone_focus_mode/lib` (9), `scripts/lib` (9). Adding one `tests/run_all.sh`
to a directory enforces every file in it at once, so expect the work to arrive
in batches rather than one file at a time.

**`--seed` is shrink-only and now enforces it** — it exits 1 rather than adding
an entry, so you cannot exempt a new library by reseeding. It reads tracked
files only, so stage before trusting its output.

## Phase 4 (later): a percentage bar on top of the ratchet

The namespace-jail evidence above is the load-bearing input. The technique
works and is contained; what is unmeasured is whether it generalises to `lib/`
files rather than entry scripts, and what per-file mount analysis costs at
scale. The `pacman_wrapper.sh` result names the dominant failure mode: masking
`/usr/local/bin` makes the wrapper take its "libraries missing → exec pacman
unwrapped" escape hatch at lines 44-45 and exit before doing any real work, so
coverage collapses from 75% to 29%. Measure a handful of `lib/` files through
`jail_run.sh` before proposing any number.

## What is already true (verify, do not redo)

```bash
bash meta/scripts/check_file_length.sh --all   # "all checked files are within 250 lines"
bash meta/scripts/check_ci_green.sh            # exit 0 while main is green
gh run list --limit 5
```

- **Every file is under 250 lines.** The five deployment-trap files were split:
  `install_leechblock.sh` (485→119), `block_compulsive_opening.sh` (705→182),
  `setup_night_lockdown.sh` (918→127), `pacman_wrapper.sh` (929→217),
  `setup_midnight_shutdown.sh` (1734→109), plus `_glyph_art.py` (253→208).
- **`file-length-cap`** runs `check_file_length.sh --all` on every commit.
- **`ci-baseline-green`** refuses to commit onto a red `main` (fails closed on
  red, warns and passes when it cannot tell). Bypass: `CI_GREEN_SKIP=1`.
- **`ci-mirror`** on pre-push now also runs every `*/lib/tests/run_all.sh` and
  the side-effect-free half of `shell-tests.yml`.
- **`shell-tests.yml`** discovers and runs every `*/lib/tests/run_all.sh`. Four
  such suites existed before and none of them ran in CI until this was added.

## Measuring the scale — use `git ls-files`, not `find`

```bash
git ls-files '*.sh' | wc -l                          # 560 tracked
git ls-files '*/lib/tests/run_all.sh'                # 4 suites
bash meta/scripts/check_shell_coverage.sh --all      # 115 uncovered, 115 exempt
```

A bare `find` reports 565 `.sh` files because it walks `.venv/`,
`.ci-mirror-venv/` and `node_modules/`. The earlier "roughly 487" figure in
this file came from an unfiltered walk of a different tree state. Seeding an
allowlist from an unfiltered `find` would bake vendored venv scripts into a
tracked file, and `check_file_length.sh --all` passing would not reveal it,
because that script carries its own separate exclusion list.

## What Phase 1 measured — why the bar is presence, not a percentage

Coverage of the new libs, measured with
`bash meta/scripts/shell_coverage.sh <lib/tests/run_all.sh> <lib-basename> 0`:

| lib                                                       | coverage       | what is uncovered                                |
| --------------------------------------------------------- | -------------- | ------------------------------------------------ |
| `cco_state.sh`                                            | 93.94% (62/66) | only `kill_app`'s two `pkill` lines              |
| `leechblock_fetch.sh`                                     | 38.57% (27/70) | `download_extension`: curl/tar/unzip             |
| `leechblock_browsers.sh`                                  | 36.47% (31/85) | `replace_browser_in_place`: sudo binary patching |
| `cco_wrapper/install/report`, `leechblock_config/firefox` | 0%             | every function pkills, sudo-writes or installs   |

**The pattern: the decision logic reaches ~90%+, the effecting code reaches 0%.**
A 100% bar means shimming `sudo`, `pkill`, `systemctl`, `curl` and `npm` for
every installer in the repo. That is the real cost to put in front of the user.

## The harness that works — extend it, do not clone it

`linux_configuration/scripts/periodic_background/digital_wellbeing/lib/tests/`
holds `leechblock_harness.sh` and `cco_harness.sh` plus a `run_all.sh` whose
glob is `test_*.sh`. **One harness per directory, not per file** — `jscpd`
fails above 2% duplication and five near-identical harnesses is exactly how
that trips.

Two patterns worth copying:

- **`_t_isolate_path`** narrows `PATH` to a shim dir. It is the only way to
  make `command -v jq` or `command -v chromium` fail on a machine that has
  them. **Every external the code under test calls must be seeded into that
  dir** — a missing `mkdir` aborted the suite under `set -e` with _no stderr_,
  which under kcov looked like a coverage-tool bug for twenty minutes.
- **A fixture self-check.** `cco_harness.sh` asserts its own globals are
  populated and calls `notify` for real. This is not linter appeasement: it is
  what turns "a typo in a global name" from a silent skipped assertion into a
  loud failure, and it happens to satisfy SC2034 honestly.

## Traps that cost real time in Phase 1 — all still live

- **`shfmt -w` corrupts `[hyphenated-keys]` in associative arrays**, turning
  `${BROWSERS[google-chrome-stable]}` into a subtraction expression. **Quote the
  subscripts.** Reproduced live in a test file during this campaign. Canary:
  `grep -nE '\[[a-z0-9]+ - ' <file>` must be empty after every `shfmt` and
  every `pre-commit run`.
- **A comment line starting with `# shellcheck` is parsed as a directive** and
  fails with SC1072/SC1073. Write "the linter", not "shellcheck", at the start
  of a comment line.
- **`verify_shell_split.sh` cannot see heredocs.** In
  `setup_midnight_shutdown.sh` it reported a bare `-log`, because `log()` sits
  at column 0 _inside a generated script_. For any file that emits scripts,
  the real check is **hashing the emitted content**, not the function list.
- **New sourced libs need a shebang AND the exec bit**, staged with
  `git add --chmod=+x`. A plain `git add` afterwards resets it. Payload files
  under `lib/payloads/` are `100755` too — the shebang hook rejects `100644`.
- **`gh` and `git push` race.** Several pushes failed with "cannot lock ref";
  `git fetch` then re-push. Not a divergence.

## Known-broken, NOT caused by the campaign

**`Python tests` has been failing since 2026-08-17** — before any of this work.
The cause is `pip` hitting `error: resolution-too-deep` while installing
`meta/requirements.txt`, on commits that touch no Python at all. It needs
dependency pinning, and it is why `python-tests.yml` is deliberately **not** in
`check_ci_green.sh`'s required list. Worth fixing on its own; do not fold it
into Phase 3.

## Rules that will bite you

- **No suppressions, ever.** No `# noqa`, no `shellcheck disable`, no
  per-file-ignore without asking every single time.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json`, **plus a contract** in
  `docs/superpowers/contracts/` once ≥4 code files are staged. Put the
  **measured** number in it, never a rounded or hoped-for one.
- **A test file broken by your commit is a same-session bug.** Three were
  broken this way in Phase 1 (`security_apps.sh`, `test_shutdown_timer_monitor.sh`,
  and the pacman pair) — each asserted on code a split had moved. Fix the
  assertion to search the entry script _and_ its libs; do not weaken it.
- `pre-commit run --files <changed>` **after** `git add`. `prettier` and
  `ci-mirror` run on **pre-push**. `npx prettier --write` any `.md`/`.json`.
- Work directly on `main`. `git stash` and branch creation are blocked.
- **Verify what actually got committed.** Re-grep the file after committing;
  an autoformat pass stripped a load-bearing variable definition three times in
  Phase 1, once landing a `set -u` abort in `setup_night_lockdown.sh` that had
  to be fixed in a follow-up commit.
