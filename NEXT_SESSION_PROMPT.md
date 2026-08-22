# Next session: Phase 3 — keep clearing the shell-coverage allowlist

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## The scoping answers are SETTLED. Do not re-ask them.

The user answered these explicitly on 2026-08-22. An earlier session built a
_presence-based, lib-only ratchet_ instead — the opposite of every answer. It
has since been converted. **Do not re-propose the ratchet.**

| Question           | Answer                                               |
| ------------------ | ---------------------------------------------------- |
| **Scope**          | Repo-wide gate. NOT a ratchet.                       |
| **Bar**            | **100%** line coverage. Shim every external.         |
| **Files**          | **ALL** `.sh`, not just `lib/`.                      |
| **Gates**          | pre-commit **AND** pre-push **AND** CI.              |
| **Order**          | Tests first; arm the gate only once 100% is reached. |
| **Target picking** | Hardest first.                                       |

Because the gate arms last, it never freezes the repo — there is nothing left
to block by the time it turns on. That ordering is what makes this safe.

## What is already true (verify, do not redo)

```bash
git log --oneline -5          # bca70b67, 61ff5eac, b7523d16, 0e843c2a on main
bash meta/scripts/check_file_length.sh --all          # all within 250 lines
grep -vc '^#\|^$' meta/shell-coverage-allowlist.txt   # 105
```

- **`meta/scripts/shell_coverage_jail.sh`** measures a script's coverage while
  it runs **for real** inside a user+mount namespace. This is the campaign's
  core tool. **100% needs NO source changes and NO suppressions.**
- **`meta/scripts/check_shell_coverage.sh`** now enforces a **measured 100%
  bar** (it was a presence check that an empty suite could satisfy). It is
  **deliberately NOT wired into any hook yet.**
- **jscpd was already over its own 2% threshold at 2.45%** and would have
  rejected every commit staging a `.sh` file. Vendored `.venv/` shell alone
  accounted for it (2.50% -> 1.67%); `lib/tests/` is also excluded now (1.47%).
- **5 commits are unpushed.** Push them when convenient.

### Measured so far

| lib                       | coverage                                     |
| ------------------------- | -------------------------------------------- |
| `dot_resolver_install.sh` | **39/39 = 100.00%** (off the allowlist)      |
| `nc_php.sh`               | 84/85 = 98.82% (still exempt)                |
| `rpi_nc_install.sh`       | 10/88 = 11.36% — **MIS-MEASURED, see below** |

Suites are green: **28 + 30 + 29 = 87 assertions, 0 failures.**

## Start here

The hardest remaining, scored on root ops + system writes + destructive calls.
**44 of the 105 allowlisted libs sit in `features/lib/`, where a harness
already exists** — that directory is the cheapest place to keep going.

```
score  lines  file
   53    221  linux_configuration/scripts/single_use/features/lib/dwm_config.sh
   51    241  linux_configuration/scripts/single_use/features/lib/aw_autostart.sh
   51    179  linux_configuration/scripts/single_use/features/lib/rpi_nc_ca.sh
   50     92  linux_configuration/scripts/single_use/misc/testsAndMisc-bash/lib/transcribe_deps.sh
```

### The invocation that works

```bash
bash meta/scripts/shell_coverage_jail.sh \
  --subject linux_configuration/scripts/single_use/features/lib/tests/run_all.sh \
  --bind /etc --bind /usr/local/bin --bind /var --bind /root \
  --seed-dir /var/www/nextcloud --seed-dir /var/lib \
  --seed-dir /etc/php/8.2/apache2 --seed-dir /etc/php/8.2/mods-available \
  --seed-dir /etc/apache2/sites-available \
  --seed-file /etc/php/8.2/apache2/php.ini \
  --measure <lib>.sh --min 100 --timeout 90s -- ""
```

`--bind` what a subject **writes**; **never** bind what it **reads**. Binding
`/usr/local/bin` cut `pacman_wrapper.sh` from 75.00% to 28.95%, because it
sources its sibling libs from there. **Never `--bind /tmp`** — the jail's own
working dir lives there and the run dies with "cases: No such file".

## THE OPEN PROBLEM — read before trusting any number

**kcov mis-measures `rpi_nc_install.sh`.** It reports 10/88 = 11.36%,
recording lines 13-54 and nothing after — but the code past line 54 provably
runs: `/root/.nextcloud_db_password` and
`/etc/apache2/sites-available/nextcloud.conf` both exist after a run, and all
29 assertions pass.

Three hypotheses were each tested against a minimal reproduction and
**DISPROVEN** — do not retry them:

1. kcov traces correctly **past a heredoc**.
2. kcov traces correctly **into a `$(...)` command substitution**.
3. kcov traces correctly **past a heredoc-fed stub reading stdin via `$(cat)`**.

The cause is unknown. **This is a hole in the campaign's primary instrument.**
The other two libs in the same directory measure sensibly, so it is not
universal, but nobody has bounded which subjects it affects. If a suite's
assertions pass while its percentage looks absurd, suspect this before
suspecting the tests. **Never "fix" a number by weakening a test.**

## Traps that cost real time — all still live

- **Check assertion RESULTS, not just the coverage percentage.** The committed
  `nc_php` suite shipped **2 failing assertions** because an earlier session
  measured coverage and never read the output. Both were test bugs: the cron
  entry arrives on `crontab`'s **stdin**, not argv, and `configure_mariadb`'s
  stdout is eaten by `db_password=$(...)`. Run the suite and read it.
- **A top-level stub function SHADOWS the subject's own function** for every
  later assertion. Doing this for a phase-order test dropped coverage
  83.53% -> 57.65% **while the tests still reported passing**, because they
  were exercising the stubs. Put such redefinitions in a **subshell**.
- **A stub for a piped-into command must drain stdin**, or the writer takes
  SIGPIPE and the suite aborts under `set -e`. If its output feeds `grep -v`,
  it must also **emit a line** — `grep` exits 1 on no match and `pipefail`
  propagates that.
- **A stub must materialise what the real tool creates.** `rm -rf
/var/www/nextcloud` followed by a record-only `unzip` leaves the later `cd`
  with nothing to enter; the function returns 1 and `set -e` aborts the suite
  from inside a command substitution **with no stderr at all**.
- **`sudo` cannot work inside a userns** (`setresuid` -> EINVAL). The jail
  supplies a pass-through that drops flags and `exec`s. Do not add `sudo` to
  `DEFAULT_SHIMS` — recording-and-exiting would skip the very writes the
  suites exist to assert on.
- **The jail needs its own `passwd`/`group`/`nsswitch`**, or `id -u "$USER"`
  fails and aborts the subject under `set -e` before anything interesting.
- **`--map-root-user` alone does not grant `/etc` writes.** `CAP_DAC_OVERRIDE`
  in a userns only covers files whose owner uid is mapped in; the bind-mount
  over the write target is what makes the write land.
- **`shfmt` (run by the pre-commit hook) reformats and can push a file over
  the 250-line cap** _after_ your own check passed. It also rewrites `case`
  arms onto separate lines, so exact-match patches written against the old
  layout silently fail to apply. Re-check the cap after staging.
- **Commits exceed a 2-minute foreground timeout.** Run `git commit` with
  `run_in_background: true` and read the output file.
- **Two-strike rule.** Two failed attempts at the same line -> stop, document
  it, keep the working state. `nc_php.sh` line 111 (the `crontab -l ||`
  first-run fallback) hung the suite twice and is deliberately left uncovered.

## Rules that will bite you

- **No suppressions, ever.** SC2155 and SC2016 were both fixed at the source
  rather than disabled; do the same.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json` (schema: `intent`, `scope`,
  `changes[]`, `verification[]` each with `command`/`result`/**`evidence`**,
  `risks[]`, `rollback[]` — validate with
  `python3 meta/scripts/validate_evidence.py <file>`), **plus a contract** in
  `docs/superpowers/contracts/` once **>=4 code files** are staged.
- **Put the MEASURED number in it**, never a rounded or hoped-for one.
- **Stage narrowly.** Pre-commit hooks restage files; a `git add` of one path
  once swept four unrelated files from a _concurrent session_ into a commit.
  Check `git diff --cached --name-only` before committing.
- **New test files need the exec bit**: `git add --chmod=+x`.
- Work directly on `main`. `git stash` and branch creation are blocked.
- **Another Claude session may be working in this repo simultaneously.** One
  was on 2026-08-21/22. Check `git log` for commits you did not make before
  assuming the tree is yours.

## Not caused by this campaign

**`Python tests` CI has been failing since 2026-08-17** — `pip` hits
`error: resolution-too-deep` installing `meta/requirements.txt`, on commits
touching no Python. It needs dependency pinning, and is why `python-tests.yml`
is deliberately **not** in `check_ci_green.sh`'s required list. Worth fixing on
its own; do not fold it into Phase 3.

**The 2026-08-22 11:33 hard freeze was investigated and cleared.** No OOM, no
hung task, no kernel message after 11:20; this campaign was idle at the time
and left no residue. Steam crash-dumped two minutes prior on an RTX 3090.
Correlation only — a hard hang leaves no log — but the jail was ruled out. Each
jail case is now bounded by `timeout --kill-after=10s` with stdin closed.

## When the allowlist reaches zero

Only then, wire `check_shell_coverage.sh` into **pre-commit, pre-push and CI**
(all three — that was the answer). Hook mode costs **0.42s per file**, so a
normal commit stays sub-second; a full `--all` sweep is minutes and belongs in
CI.
