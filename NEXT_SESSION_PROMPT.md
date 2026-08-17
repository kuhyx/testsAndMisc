# Next session: backfill monitor coverage, then keep splitting at 100%

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

Over-cap: **22** (18 shell, 2 kotlin, 1 dart, 1 markdown — this file).
Working tree clean, `main` in sync with origin.

Two standing decisions from the user, already made — do **not** re-litigate:

1. **100% line coverage, always.** Every shell file you touch gets there. Not
   "100% where cheap"; 100%.
2. **Split blind where there is no device.** Do not deploy to the phone, do not
   ask to. Prove splits with tests, hashes and real runs instead.

---

## 0. Read this first: coverage is measurable now

`kcov 43` is installed and **works**, which changes what "tested" means here.
Use the wrapper, not raw kcov:

```bash
bash meta/scripts/shell_coverage.sh <test-script> <subject-basename> [min-percent]
# e.g.
bash meta/scripts/shell_coverage.sh phone_focus_mode/lib/tests/test_dns_iptables.sh dns_iptables.sh
# -> dns_iptables.sh: 74/74 lines = 100.00%
```

Defaults to a 100% minimum and exits 1 below it, naming the uncovered lines.

Two kcov traps, both of which fail **silently** and both already handled inside
the wrapper — do not go around it:

- It must get the test script **directly**. Handed `bash script.sh` it
  instruments the bash binary, finds no shell source, and reports `0/0 = 0.00%`,
  which reads exactly like "nothing is covered" rather than "nothing was
  measured".
- Per-line detail lives only in `cov.xml`. The `coverage.json` summary has the
  percentage and nothing else, so it cannot tell you which lines are missing.

kcov measures **lines, not branches**, so `[ -n "$x" ] && thing` counts as
covered when only one side runs. That is why every new assertion must also be
**mutation-proofed**: break the code under it, confirm the test fails, restore.
That check caught three real defects last session and is not optional.

## 1. Backfill `lib/monitor.sh` to 100% — do this first

The split shipped verbatim-proven and green (9/9), but measuring it afterwards
showed the tests barely touch it:

| file                           | coverage              |
| ------------------------------ | --------------------- |
| `lib/monitor.sh`               | **44.44%** (48/108)   |
| `lib/monitor_checks_policy.sh` | **7.69%** (5/65)      |
| `lib/monitor_checks_health.sh` | **0%** — never loaded |

This is pre-existing debt that the split merely made visible; the probes were
untested before too. The user has asked for it closed now.

**The work is an ADB stub layer.** Every `_check_*` probe shells out through
`adb_root_shell`, so reaching them means a fake `adb` that models battery,
storage, pidfiles, the hosts sha, launcher state, the companion package and the
boot script. Budget for roughly four times the size of the `dns_iptables`
harness.

Copy the pattern that already works — `lib/tests/dns_iptables_harness.sh`:

- stage the subject into a `mktemp -d` beside a fake `config.sh`;
- put stubs on `PATH`, with **failure injection** (`_fail_op`) and state
  seeding (`_seed_jumps`) so error branches are reachable — that is exactly how
  `dns_iptables.sh` got from 91.89% to 100%, since all six missing lines were
  error paths;
- run each case as a subprocess via a quoted heredoc, so `$0` resolves to the
  staged copy and any `$VAR` reaches the subject unexpanded.

Keep the harness in its own file. Both test files must stay under 250 lines.

## 2. Then the remaining brief-scoped splits

Cheapest first. Each is one commit, each needs 100% on whatever it extracts.

| file                 | lines | notes                                                      |
| -------------------- | ----- | ---------------------------------------------------------- |
| `phone_backup.sh`    | 333   | **PC-side** — bash, absent from `deploy.sh`, no list edits |
| `curfew_enforcer.sh` | 367   | phone; both deploy lists                                   |
| `hosts_enforcer.sh`  | 421   | phone; both deploy lists                                   |
| `focus_daemon.sh`    | 543   | phone; both deploy lists; heavy device I/O                 |
| `config.sh`          | 571   | **see the warning below**                                  |
| `deploy.sh`          | 837   | **must come after every other phone split**                |
| `focus_ctl.sh`       | 1091  | phone; largest; heavy device I/O                           |

### Ordering constraints — getting these backwards is expensive

- **`deploy.sh` goes last.** Every enforcer split adds an entry to its two
  hardcoded lists. Split `deploy.sh` first and those lists move into a new file,
  so the "add to BOTH lists" step then points at a stale location.
- **`config.sh` is paired with `python_pkg/focus_policy/loader.py`.** Two
  commits or one, but plan them together.

### `config.sh`: the safety net the last brief promised does not exist

The previous brief claimed `focus_policy`'s 100% tests would catch a bad
`config.sh` split. **They will not**, and this was verified:

- the `pytest with coverage enforcement` hook is `types: [python]`, so a
  `config.sh`-only commit runs **no tests at all**;
- `pre-push` `ci-mirror` runs pytest only for _changed packages_, and
  `config.sh` is in no package;
- the `focus_policy` tests build **synthetic** `config.sh` fixtures in
  `tmp_path` — they never read the real file, so they cannot regress on it.

Use a parse fingerprint instead. Baseline of the current file:

```
1624750c9636492d225b8bb8555f4e2fa75ea64abc670b37c9557b80b9e1883a
```

Recompute it after the split with `load_policy(Path("phone_focus_mode/config.sh"))`,
`dataclasses.asdict`, `json.dumps(..., sort_keys=True, default=str)`, sha256.
Same hash = the loader still sees an identical policy. `time` objects are not
JSON-serialisable, hence the `default=`. Also run `pytest python_pkg/focus_policy`
by hand regardless of what the hooks say.

## 3. Then the three restructures

Verbatim moves cannot get these under the cap, so the hash tool does **not**
apply. Each needs a real test at 100%.

- **`install_plagiarism_tools.sh` (534, only 3 tiny functions)** — ~500 lines of
  top-level code. Wrap coherent stages in functions first, then move those. Most
  mechanical of the three; do it first. Note `verify_shell_split.sh` only hashes
  _function bodies_, so it is blind to top-level code — read `git diff` on the
  entry script before committing.
- **`libre_translate.sh` (488, 18 funcs)** — the user chose the approach: move
  the whole config-globals cluster into **one lib that owns both the writes and
  the reads**. Do not try relocating `parse_args` alone; four attempts failed.
- **`diagnose_pacman_hook_stall.sh` (493, 15 funcs)** — `run_one` writes
  `LAST_ELAPSED`, `main` reads it. Emits **SC2153** (`PACMAN_BIN` vs
  `PACMAN_PID`) once split: a real finding to resolve, never to suppress.

## 4. Last, and only after the rest

**`install_leechblock.sh` (485)** and **`block_compulsive_opening.sh` (705)** are
copied to `/usr/local/…`, and `pacman_wrapper.sh:831` prefers the deployed copy
on **every pacman invocation**. Split them naively and every `pacman -S` on this
machine breaks. Teach the installer to deploy the directory first, in its own
commit, re-baseline, then split.

You cannot run `sudo pacman -S` from the Bash tool — it deadlocks on `db.lck`.
Hand the user a `! sudo pacman -S <pkg>` line plus the expected output.

---

## Tooling — use it, do not rebuild it

**`meta/scripts/check_file_length.sh --all`** — the 250-line gate. Run it
**before every commit**: a split that fixes one file while pushing its new
library over the cap is a net zero, and that happened twice in an earlier
session. Source extensions only; `third_party/` and `docs/superpowers/` are
excluded.

**`meta/scripts/extract_shell_functions.py`** — moves functions into a library,
brace-by-brace. **Never slice by line range**: these scripts interleave
top-level commands between function definitions, and a range slice sweeps those
into the library where they run at source time and out of order.

It was fixed last session, so the old warning no longer applies: it used to
write the library and then exit on a missing `set -e` anchor, leaving the
functions in **both** files. It now completes the move, prints the source line
to paste by hand, and refuses outright if the entry script would not shrink.
Phone scripts are `#!/system/bin/sh` with no `set -e`, so expect the warning and
place the source line yourself, after the existing `. "$SCRIPT_DIR/config.sh"`.

**`meta/scripts/verify_shell_split.sh <rev> <old> <new>...`** — proves a move
was verbatim by normalising each function through `shfmt -mn` and comparing
hashes. Two things to know:

- For a **partial** split, list the old path **among the new paths too**, or it
  reports a false `DIFFERENCE` with an empty after-set:
  `verify_shell_split.sh <rev> a.sh a.sh b.sh`.
- `<rev>` must be the **pre-split commit**, not `HEAD`, once you have committed.

Re-run it after pre-commit autofixes.

## The rule that decides where a shell seam can fall

**A file must not assign a global it never reads.** That is SC2034; the repo
forbids suppressions; the pre-commit hook runs `shellcheck` with **no `-x`**, so
a `# shellcheck source=` directive will not make it follow the link. Each file
stands alone — run `shellcheck <lib>` on its own before committing.

Constants must travel **with their readers**. In the `monitor.sh` split the
`_MONITOR_*` constants were partitioned by who reads them: the five read only by
the policy probes moved into that file, and the ones shared across both children
stayed in the parent. That is what let all three files pass standalone.

## Rules that will bite you

- **No suppressions, ever.** No `# noqa`, `# type: ignore`, `# shellcheck
disable`, no lowered coverage threshold. Every time this came up, the seam or
  the code was wrong, not the linter. Two SC2016 findings were fixed
  structurally last session — a `[$]` character class in a sed pattern, and a
  quoted heredoc prelude — rather than disabled.
- **Watch ruff's autofixer.** Its `T201` fix silently deleted a tool's own
  `print()` output and left `pass` behind. Use `sys.stdout.write` for real
  output, matching `extract_shell_functions.py`. A new `.py` under
  `meta/scripts/` also needs a `#!/usr/bin/env python3` shebang or `INP001`
  fires.
- **Run the actual thing.** `run_phone.sh --help` exiting 0 is what proved the
  monitor split's source chain resolved. For scripts too dangerous to run, say
  so and rely on `sh -n` plus sourcing each library in a subshell.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (copy `template.json`). Staging
  **≥4 code files also needs** a fresh `docs/superpowers/contracts/*.json`.
  Validate with `meta/scripts/validate_{evidence,contract}.py`. Put the measured
  coverage percentage in the evidence — the real number, not a rounded-up one.
- New sourced libs need a shebang **and** the executable bit; the
  `check-shebang-scripts-are-executable` hook reads the **git index**, so stage
  the mode with `git add --chmod=+x`. A plain `git add` afterwards resets it.
- `pre-commit run --files <changed>` before committing. **`prettier` and
  `ci-mirror` run on pre-push, not pre-commit.** `npx prettier --write` any `.md`
  you touch, including this one.
- Work directly on `main`. `git stash` and branch creation are blocked by hooks;
  use `git worktree add --detach` for a clean baseline. Confirm a push landed
  with `git status -sb` showing no `[ahead N]`.
- **Do not wire the file-length hook into pre-commit.** It lands last, once
  `check_file_length.sh --all` exits 0. 22 files are still over.
- Cap pytest memory:
  `systemd-run --user --scope -p MemoryMax=2G -p MemorySwapMax=0`.
- Watch `jscpd` (fails above 2% duplication). Per-file test harnesses are
  near-identical by nature; there are already three. Run it after adding the
  next one rather than discovering the failure at commit time.

## Known pre-existing state — not yours, do not fix silently

- `bash linux_configuration/tests/test_security_hardening.sh` exits 1 with
  `❌ FAIL: Compulsive block wrappers installed`. Belongs to
  `block_compulsive_opening.sh`.
- **`bucket_catch/packages/frontend` has 4 eslint errors**, documented with
  measured reasoning in
  `docs/superpowers/evidence/bucket-catch-eslint-2026-08-17.json`.
  `usePuzzleGameLoop.ts:129`'s `Map.get(...)!` cannot be fixed with
  `?? Infinity` — tried, measured at 99.54%, because the default side is
  unreachable. `npm run coverage` is green: 145 tests, 100%.
- Repo-wide `jscpd` reports ~2.5% from the working tree but 1.47% at HEAD in a
  clean worktree — the excess is vendored `.venv` site-packages. Don't chase it.
- **Two enforcer splits are unverified on the phone**: `tether_enforcer.sh` and
  now `dns_enforcer.sh`. Both have passing tests and both grew `deploy.sh`'s two
  lists, but no deploy has run. If enforcement misbehaves after the next deploy,
  look there first.

## Ten over-cap files the brief has never covered

Out of scope until the user says otherwise. Report, do not start:

`setup_midnight_shutdown.sh` (1734), `check_and_enable_services.sh` (1301),
`generate_study_materials.sh` (1017), `pacman_wrapper.sh` (929),
`setup_night_lockdown.sh` (918), `hosts/install.sh` (912),
`setup_hosts_guard.sh` (576), `EnforcementRunner.kt` (564),
`DevicePolicyBridge.kt` (415), `status_page_state.dart` (307).

`pacman_wrapper.sh` carries the same live-deployment trap as the leechblock
pair. The Kotlin and Dart files need a different verification stack —
`focus_owner` gradle needs `JAVA_HOME=/usr/lib/jvm/java-21-openjdk` and
`--rerun-tasks`; a plain `gradlew test` reports `UP-TO-DATE` and proves nothing.

## Testing notes specific to this repo

- `linux_configuration/tests` **is** in CI, but never by name: `pyproject.toml`
  sets `testpaths`, so bare `pytest` collects it. Behaviour is gated; coverage is
  not (`--cov=python_pkg` only).
- **Non-`python_pkg` modules are tested via `linux_configuration/tests/`**, whose
  `conftest.py` puts standalone script dirs on `sys.path`. Add a directory there
  rather than moving code into `python_pkg/` — that move drags the file under a
  `fail_under = 100` gate and breaks any by-path caller.
- `name-tests-test` requires every `.py` under `tests/` to be `test_*.py`. Shared
  helpers go in `conftest.py` as **fixtures** — `conftest` is not importable by
  module name.
- For a **test-file** split the discriminating check is the test **count**, not a
  green run: a file outside the runner's glob is silently never collected.
- `phone_focus_mode`'s shell tests are **not** in CI — `shell-tests.yml` uses an
  explicit list covering `linux_configuration/tests/` only. Run them by hand:

  ```bash
  for t in test_dns_iptables test_monitor test_tether_enforcer; do
    bash phone_focus_mode/lib/tests/$t.sh | tail -1
  done
  # expect: 24 passed / 9 passed / 17 passed
  ```

- A test that passes proves nothing on its own. `test_dns_enforcer.sh` was
  deleted last session because its six assertions targeted three functions
  `dns_enforcer.sh` has never defined — it had never run a single assertion
  since the commit that added it. Check the **count**, and check coverage.
