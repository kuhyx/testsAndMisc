# Next session: §3 restructures, then §4's deployed-copy trap

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

Over-cap: **15** (12 shell, 2 kotlin, 1 dart). `phone_focus_mode/` is **done** —
no file there is over the cap. Working tree clean, `main` in sync.

Two standing decisions from the user, already made — do **not** re-litigate:

1. **100% line coverage on what you extract** — with the one measured
   exception in §0.1, which is a prohibition, not a target to chase.
2. **Split blind where there is no device.** Do not deploy to the phone, do
   not ask to. Prove splits with tests, hashes and real runs instead.

---

## 0. Read this first — three rules that cost real time to learn

### 0.1 NEVER pipe a `while read` loop whose body calls `pm`/`adb`/`iptables`

These lines are **deliberately uncovered** and must stay that way:

| file                              | lines                 | why                    |
| --------------------------------- | --------------------- | ---------------------- |
| `phone_focus_mode/daemon_apps.sh` | 35, 60, 110, 130, 158 | trailing `done < file` |

Each is the redirect of a loop whose body calls `pm`. Piping the file in
instead lets `pm` inherit and drain the loop's stdin, so it processes **one**
package instead of all of them — measured in this repo as 1 of 54. kcov
cannot attribute a trailing `done < file`, so those five lines read as
uncovered forever; that is the price and it is paid knowingly. They are
pinned by three mutations in `meta/scripts/fixtures/mutations/daemon_libs.json`
that redirect them from `/dev/null` and fail the suite.

If you ever must remove such a redirect line, use `mapfile -t arr < file`
then `for x in "${arr[@]}"` — **never a pipe** — and only after confirming
nothing in the body reads stdin. Piping _is_ correct where the body is pure
(`curfew_net.sh` did it safely); the body is what decides.

### 0.2 kcov artifact taxonomy

Four constructs are instrumented but never reported, so they hold a file
below 100% no matter how well tested:

| construct                       | safe to restructure?                        |
| ------------------------------- | ------------------------------------------- |
| multi-line array/list literal   | yes — put it on one line                    |
| `{ ... } >file` group           | yes — redirect per statement, or one printf |
| multi-line `mapfile < <(...)`   | yes — put the substitution on one line      |
| embedded multi-line `awk '...'` | **no** — collapsing it destroys readability |
| trailing `done < file`          | **only if the body is stdin-pure** (§0.1)   |

Before restructuring, prove the lines actually execute with a mutation. Two
files are knowingly below 100% for this reason and both are documented:
`daemon_location.sh` 65.00% (the awk Haversine) and `daemon_apps.sh` 93.42%.

### 0.3 An equivalent mutation means dead code, not a missing test

`meta/scripts/mutate_shell.py <spec>` runs one of the six specs in
`meta/scripts/fixtures/mutations/` — 120 mutations, all killed.

A **survivor** is either a missing assertion or _equivalent code_. Twice this
session it was the latter, and both times the right fix was deleting the dead
branch: an unreachable `-f` guard in `hosts_mount.sh`, and a redundant
comment filter in `ctl_usage.sh`. Never resolve a survivor by weakening the
mutation or adding a test that cannot fail.

A **no-op** (the `find` string matched nothing) counts as a failure — a stale
spec entry silently stops testing. Run specs **one at a time**: two runs at
once edit the same subjects and leave a mutation applied, which reads as a
survivor and dirties the tree.

## 1. §3 — the three restructures (start here)

Verbatim moves cannot get these under the cap, so `verify_shell_split.sh`
does not apply. Each needs a real test at 100%.

- **`install_plagiarism_tools.sh` (534, only 3 tiny functions)** — ~500 lines
  of top-level code. Wrap coherent stages in functions first, then move them.
  Most mechanical of the three; do it first. `verify_shell_split.sh` only
  hashes _function bodies_, so it is blind to top-level code — read
  `git diff` on the entry script before committing.
- **`libre_translate.sh` (488, 18 funcs)** — the user chose the approach:
  move the whole config-globals cluster into **one lib that owns both the
  writes and the reads**. Do not try relocating `parse_args` alone; four
  attempts failed.
- **`diagnose_pacman_hook_stall.sh` (493, 15 funcs)** — `run_one` writes
  `LAST_ELAPSED`, `main` reads it. Emits **SC2153** (`PACMAN_BIN` vs
  `PACMAN_PID`) once split: a real finding to resolve, never to suppress.

## 2. §4 — last, and only after §3

**`install_leechblock.sh` (485)** and **`block_compulsive_opening.sh` (705)**
are copied to `/usr/local/…`, and `pacman_wrapper.sh:831` prefers the
deployed copy on **every pacman invocation**. Split them naively and every
`pacman -S` on this machine breaks. Teach the installer to deploy the
directory first, in its own commit, re-baseline, then split.

You cannot run `sudo pacman -S` from the Bash tool — it deadlocks on
`db.lck`. Hand the user a `! sudo pacman -S <pkg>` line plus the expected
output.

## 3. Out of scope until the user says otherwise

`setup_midnight_shutdown.sh` (1734), `check_and_enable_services.sh` (1301),
`generate_study_materials.sh` (1017), `pacman_wrapper.sh` (929),
`setup_night_lockdown.sh` (918), `hosts/install.sh` (912),
`setup_hosts_guard.sh` (576), `EnforcementRunner.kt` (564),
`DevicePolicyBridge.kt` (415), `status_page_state.dart` (307).

`pacman_wrapper.sh` carries the same live-deployment trap as §2. The Kotlin
and Dart files need a different verification stack — `focus_owner` gradle
needs `JAVA_HOME=/usr/lib/jvm/java-21-openjdk` and `--rerun-tasks`; a plain
`gradlew test` reports `UP-TO-DATE` and proves nothing.

## Tooling

**`meta/scripts/check_file_length.sh --all`** — the 250-line gate. Run
**before every commit**: a split that fixes one file while pushing its new
library over the cap is a net zero, and that happened three times.

**`meta/scripts/shell_coverage.sh <test> <subject> [min]`** — kcov wrapper,
100% minimum. Hand it the test script **directly**; `bash script.sh`
instruments the bash binary and silently reports 0/0.

**`meta/scripts/mutate_shell.py <spec>`** — see §0.3.

**`meta/scripts/extract_shell_functions.py`** — moves functions brace-by-
brace. **Never slice by line range**: it also cut through a multi-line
quoted string in `config.sh` and left an unterminated quote, which the policy
loader's regex tolerated while the shell could no longer source the file.

**Do not trust where it puts the source line.** It got the position wrong
three times: before `SCRIPT_DIR` existed, before `STATE_DIR` (so every path
expanded against an empty prefix), and on a _nested_ re-source rather than
the top-level one. Always `grep -c` the anchor and check the placement.

**`meta/scripts/verify_shell_split.sh <pre-split-rev> <old> <new>...`** — for
a **partial** split list the old path among the new paths too, or it reports
a false `DIFFERENCE`.

## Rules that will bite you

- **No suppressions, ever.** Every time this came up, the seam or the code
  was wrong. A comment line starting with the word "shellcheck" is parsed as
  a directive (SC1073) — reword it.
- **A file must not assign a global it never reads** (SC2034). The hook runs
  `shellcheck` with **no `-x`**, so each file stands alone. Constants travel
  with their readers; a global genuinely written on both sides of a seam
  stays in the entry script (`NET_BUILT`, `CURRENT_MODE`, `NEEDS_GPS_FETCH`).
- **New sourced libs need a shebang AND the executable bit.** The hook reads
  the **git index**: stage with `git add --chmod=+x`, and note that a plain
  `git add` afterwards resets it. This cost three failed commits.
- `pre-commit run --files <changed>` before committing. **`prettier` and
  `ci-mirror` run on pre-push.** `npx prettier --write` any `.md` you touch.
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json`. Staging **≥4 code files
  also needs** a fresh `docs/superpowers/contracts/*.json`. Put the
  **measured** coverage number in it, not a rounded-up one.
- Work directly on `main`. `git stash` and branch creation are blocked; use
  `git worktree add --detach` for a clean baseline.
- **Do not wire the file-length hook into pre-commit.** It lands last, once
  `check_file_length.sh --all` exits 0. 15 files are still over.
- Cap pytest memory:
  `systemd-run --user --scope -p MemoryMax=2G -p MemorySwapMax=0`.
- Watch `jscpd` (fails above 2%). Measure in a **clean HEAD worktree** —
  the working tree reads ~2.5% because of vendored `.venv`, but HEAD is
  1.57%. Per-file test harnesses are near-identical by nature; drive repeated
  shapes through a table rather than repeating the block.

## `phone_focus_mode` — what changed, and its two live hazards

Nine commits took it from 8 over-cap files to zero. `config.sh` 571→250,
`focus_ctl.sh` 1091→171+8, `deploy.sh` 875→241+6, plus monitor,
`phone_backup.sh`, `curfew_enforcer.sh`, `hosts_enforcer.sh` and
`focus_daemon.sh`. 515 assertions across ten suites, from ~60 before.

**Hazard 1 — `config.sh` is at EXACTLY 250 with no headroom.** 184 of those
lines are the fifteen variables `python_pkg/focus_policy/loader.py` reads by
regex **over `config.sh`'s own text**. Move one into a `config_*.sh` sibling
and the loader does not error — it silently yields an empty set, which for
`WHITELIST` reads as "hide everything". The list is in `config_paths.sh`'s
header and enforced only by that comment.

Verify **both** of these before and after touching it:

```bash
python3 -m python_pkg.focus_policy --config phone_focus_mode/config.sh | sha256sum
# 83e05e82dd1683e1dff1c79a96fec0a4a56aa73295604c681ae355b40a590ba3
```

plus a diff of the **sourced environment** (79 variables) against the
pre-change commit. The hash alone is not enough: it passed clean through
both bugs hit this session — a mangled quote and a `STATE_DIR` ordering
error. The previous brief's recipe (`asdict` + `json.dumps(default=str)`,
baseline `1624750c…`) **cannot work**: four policy fields are `frozenset`, so
`default=str` serialises them in per-process iteration order.

**Hazard 2 — `deploy.sh`'s two hardcoded file lists are now in two files.**
The push list is in `deploy_phases.sh`, the cp list in `deploy_install.sh`. A
new phone-side sibling must go in **both**, or it is staged and never lands,
and whatever sources it fails to start with no obvious cause. Check with
`comm` in both directions; `config_secrets.sh` is deliberately asymmetric.

## Known pre-existing state — not yours, do not fix silently

- `bash phone_focus_mode/lib/tests/test_magisk_service.sh` **hangs**.
  Confirmed identical at HEAD before this session's work; unrelated to it.
- `bash linux_configuration/tests/test_security_hardening.sh` exits 1 with
  `❌ FAIL: Compulsive block wrappers installed`. Belongs to §2.
- `bucket_catch/packages/frontend` has 4 eslint errors, documented in
  `docs/superpowers/evidence/bucket-catch-eslint-2026-08-17.json`.
- **Eight splits are UNVERIFIED ON DEVICE**: `tether_enforcer`, `dns_enforcer`
  (both pre-existing), plus `curfew_enforcer`, `hosts_enforcer`,
  `focus_daemon`, `config.sh`, `focus_ctl` and `deploy.sh`. One real deploy
  validates all of them at once — but `deploy.sh` is itself the untested one,
  so watch it closely and keep an adb push of the directory as the fallback.
- **Two copies of the Haversine** exist: `daemon_location.sh:calc_distance`
  (the original, moved) and `ctl_daemon.sh:cmd_status`'s inline awk. Both are
  tested against known city distances, but not against each other.
  `ctl_is_curfew_now` likewise duplicates `daemon_location.sh`'s
  `is_curfew_now`; those two **are** pinned by an agreement test.
- The eight `ctl_*.sh` libraries are at **41.79–92.98%**, and unlike the two
  files in §0.2 most of that is genuinely untested status-reporting code, not
  a measurement artifact. Closing it means a device fixture per enforcer.

## Testing notes specific to this repo

- `phone_focus_mode`'s shell tests are **not** in CI — `shell-tests.yml` uses
  an explicit list covering `linux_configuration/tests/` only. Run by hand:

  ```bash
  for t in test_dns_iptables test_monitor test_tether_enforcer test_curfew_net \
           test_hosts_libs test_daemon_libs test_backup_capture test_ctl_libs \
           test_adb_common test_adb_trusted; do
    printf '%-22s %s\n' "$t" "$(bash phone_focus_mode/lib/tests/$t.sh | tail -1)"
  done
  # expect: 24 / 82 / 17 / 41 / 69 / 108 / 22 / 136 / 10 / 6
  ```

- A test that passes proves nothing on its own. `test_dns_enforcer.sh` was
  deleted last session because its six assertions targeted three functions
  that never existed. Check the **count**, the coverage, and the mutations.
- Test files are subject to the 250-line cap too. Split them into a harness
  plus sourced case files, keeping **one** entry point so a single coverage
  command still measures every subject.
- `set -e` kills a suite silently. Guard any subject call whose nonzero exit
  is not part of its contract, and never seed `$$` as a pid a subcommand will
  `kill` — the suite signals itself and dies mid-run with no error.
