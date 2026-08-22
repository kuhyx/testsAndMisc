# Next session: Phase 3 — keep clearing the shell-coverage allowlist

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## The scoping answers are SETTLED. Do not re-ask them.

| Question           | Answer                                               |
| ------------------ | ---------------------------------------------------- |
| **Scope**          | Repo-wide gate. NOT a ratchet.                       |
| **Bar**            | **100%** line coverage. Shim every external.         |
| **Files**          | **ALL** `.sh`, not just `lib/`.                      |
| **Gates**          | pre-commit **AND** pre-push **AND** CI.              |
| **Order**          | Tests first; arm the gate only once 100% is reached. |
| **Target picking** | Hardest first.                                       |

Because the gate arms last, it never freezes the repo. That ordering is what
makes this safe.

## What is already true (verify, do not redo)

```bash
git log --oneline -5        # 0091608b, d277369a, 154b4166, b91be309 on main
grep -vc '^#\|^$' meta/shell-coverage-allowlist.txt   # 103 (was 105)
```

- **The allowlist went 105 -> 103.** `unity_handler.sh` and
  `transcribe_venv.sh` both measure **100%** and are OFF it, verified through
  `check_shell_coverage.sh` itself with the exemption deleted.
- **`meta/scripts/shell_coverage_jail.sh`** measures a script's coverage while
  it runs **for real** in a user+mount namespace. New this session:
  `--fail-on-case-error` (default OFF). Without it a suite with a failing
  assertion exits 0.
- **A suite declares its jail needs in a `jail_args` file** beside its
  `run_all.sh`. `ci_mirror.sh`, `shell-tests.yml` and `is_covered()` all read
  it. No marker = the suite runs bare.
- **CI is green.** `shell-tests.yml` SKIPS jail_args-marked suites with a
  printed reason: kcov is not packaged for Ubuntu 24.04 and upstream ships no
  binary. The pre-push `ci-mirror` hook runs them for real instead.

### Measured so far (always through `run_all.sh` — see below)

| lib                       | coverage            | state         |
| ------------------------- | ------------------- | ------------- |
| `dot_resolver_install.sh` | **39/39 = 100.00%** | off allowlist |
| `unity_handler.sh`        | **32/32 = 100.00%** | off allowlist |
| `transcribe_venv.sh`      | **53/53 = 100.00%** | off allowlist |
| `rpi_nc_ca.sh`            | 72/73 = 98.63%      | allowlisted   |
| `transcribe_pkgmgr.sh`    | 49/50 = 98.00%      | allowlisted   |
| `nc_php.sh`               | 84/85 = 98.82%      | allowlisted   |
| `clean_audio_filters.sh`  | 83/93 = 89.25%      | allowlisted   |
| `transcribe_deps.sh`      | 48/52 = 92.31%      | allowlisted   |
| `aw_autostart.sh`         | 68/82 = 82.93%      | allowlisted   |
| `dwm_config.sh`           | 35/73 = 47.95%      | allowlisted   |
| `rpi_nc_install.sh`       | 10/88 = 11.36%      | MIS-MEASURED  |

Two directories now have harnesses:
`single_use/features/lib/tests/` (jailed) and
`single_use/misc/testsAndMisc-bash/lib/tests/` (no jail, 118 assertions).

## Start here

Highest-scored remaining, all in `features/lib/` where a harness exists:

```
score  lines  file
   4x    ~    linux_configuration/scripts/single_use/features/lib/*.sh  (41 left)
   22 libs    linux_configuration/scripts/single_use/fixes/lib/          (no harness yet)
    9 libs    phone_focus_mode/lib/                                      (no harness yet)
```

### The invocation that works

```bash
bash -c '
ja=(); while IFS= read -r l; do ja+=("$l"); done \
  < <(grep -v "^#\|^$" linux_configuration/scripts/single_use/features/lib/tests/jail_args)
timeout 300s bash meta/scripts/shell_coverage_jail.sh \
  --subject linux_configuration/scripts/single_use/features/lib/tests/run_all.sh \
  "${ja[@]}" --measure <lib>.sh --min 1 --fail-on-case-error -- ""'
```

**Always measure through `run_all.sh`, never a single test file.** That is the
subject `is_covered()` builds, and the runner's number can be LOWER than the
same suite's own — `rpi_nc_ca.sh` is 100% alone and 98.63% through the runner.
Reporting the single-file figure is reporting a number the gate will not agree
with.

## Traps that cost real time this session

- **`--fail-on-case-error` or you are flying blind.** The jail suppresses a
  suite's stdout entirely, so assertions can fail invisibly. Always pass it.
- **To find WHERE a suite dies, use an `exit <n>` sentinel.** Temporarily end
  the suite with `exit 42` at a chosen point; the jail surfaces the code. This
  is the only way to tell a tracing failure from an aborted suite.
- **`rm -f "$TEST_TMPDIR/bin/foo"` does NOT hide foo.** bash caches executable
  locations, so `command -v foo` keeps succeeding. Both harnesses now ship
  `_t_unstub`, which also runs `hash -r`. Three assertions in this repo were
  asserting the opposite of their own names because of this.
- **A prepended stub dir cannot hide a real binary either.** If the host truly
  has the tool (`pacman`, `aw-qt`, `/usr/lib/libsndfile.so`), REPLACE PATH or
  jail it. Otherwise the "not installed" case tests nothing.
- **A stub must materialise what the real tool creates.** A record-only stub
  in a `[[ ! -s $file ]]` fallback chain silently exercises the NEXT branch.
- **A top-level stub function SHADOWS the subject's own** for every later
  assertion. Put redefinitions in a subshell.
- **`shfmt` reformats after your own check passes** — re-check the 250-line cap
  after staging.
- **Commits exceed a 2-minute foreground timeout.** Use `run_in_background`.
- **Two-strike rule.** Two failed attempts at the same line -> stop, document,
  keep the working state.

## THE OPEN PROBLEM — read before trusting any number

**kcov silently under-reports, and it is contagious across processes in one
jail.** `rpi_nc_ca.sh` measures 100% alone but 98.63% through `run_all.sh`;
bisection shows `test_dwm_config.sh` running first is what costs it line 141.
`dwm_config.sh` reports 47.95% while an `exit 43` sentinel proves four of its
functions run to completion.

**One artifact is CONFIRMED:** continuation lines inside a multi-line quoted
argument (a `perl -0777 -pe '...'` block) are counted as statements that never
run — the wrong denominator. **Six other hypotheses are DISPROVEN** (heredocs,
`$(...)`, stdin-reading stubs, `cd` relocation, heredoc-into-stubbed-external,
and the exec-ing `sudo` shim / pipelines). Full details and the disproof list
are in `docs/shell-split-verification.md`. **Do not re-run those.**

The failure is one-directional: it only ever under-reports, so it can keep a
lib on the allowlist but can never promote an untested one. That is why the
campaign can continue around it. **Never "fix" a number by weakening a test.**

## Rules that will bite you

- **No suppressions, ever.** Fix SC2016/SC2155 at the source.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (validate with
  `python3 meta/scripts/validate_evidence.py <file>`), **plus a contract** in
  `docs/superpowers/contracts/` once **>=4 code files** are staged.
- **Put the MEASURED number in it**, never a rounded or hoped-for one.
- **Stage narrowly.** A concurrent session had 8 unrelated files in the shared
  index this session; `git restore --staged` them, do not commit them.
- **New test files need the exec bit** — and `git add --chmod=+x` only changes
  the INDEX. `chmod +x` the working tree too or the shebang hook fails.
- **`CI_GREEN_SKIP=1`** is the documented escape hatch when THIS commit is the
  fix for a red baseline. It must also be exported for the pre-push mirror.
- Work directly on `main`. `git stash` and branch creation are blocked.
- **Another Claude session may be working in this repo simultaneously.**

## Not caused by this campaign

**`Python tests` CI has been failing since 2026-08-17** — `pip` hits
`error: resolution-too-deep` installing `meta/requirements.txt`. It needs
dependency pinning and is deliberately excluded from `check_ci_green.sh`. Do
not fold it into Phase 3.

## When the allowlist reaches zero

Only then, wire `check_shell_coverage.sh` into **pre-commit, pre-push and CI**.
`is_covered()` now reads `jail_args` and passes `--fail-on-case-error`, so the
gate is ready; what remains is the allowlist. Note it runs a full jailed suite
per lib, so an `--all` sweep is minutes and belongs in CI, not a commit hook.
