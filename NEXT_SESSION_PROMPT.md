# Next session: pick the next §3/§4 target — no split candidate is currently in scope

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

Over-cap: **11** (10 shell, 2 kotlin, 1 dart — `focus_owner`'s two Kotlin files
count once regardless of listing style). Working tree clean, `main` in sync
as of the `setup_hosts_guard.sh` archive commit (see §0).

Two standing decisions from the user, already made — do **not** re-litigate:

1. **100% line coverage on what you extract** — same bar every session so far
   has applied. Does not apply to archived/deleted code (no split happened).
2. **Split blind where there is no device.** Do not deploy to the phone, do
   not ask to. Prove splits with tests, hashes and real runs instead.

---

## 0. What just happened (read this, don't repeat it)

`setup_hosts_guard.sh` (576 lines) was this session's assigned split target.
The dead-code check-in (per the §0 lesson from two sessions before this one)
turned up evidence the file might be fully superseded — confirmed by
inspecting live machine state: the legacy pacman hooks it installs were
absent from `/etc/pacman.d/hooks/`, its systemd units were all `disabled`,
and guard-lib's `/etc/guard-lib/targets/{hosts,nsswitch,resolved}.conf` were
all already populated. The user confirmed: archive, don't split.

Scope grew past the one named file once the directory was surveyed: the
**whole legacy hosts-guard subsystem** (17 files — `setup_hosts_guard.sh`,
`enforce-hosts.sh`, `enforce-nsswitch.sh`, `enforce-resolved.sh`, 6 systemd
units, `install_pacman_hooks.sh`, `pacman-hooks/*`, `psychological/*`, both
READMEs) only existed to support the retired system, so it went to
`testsAndMisc-archive` together via `git filter-repo` (same procedure as the
plagiarism-tools and libre_translate archives). `plugins/nsswitch-plugin.sh`
and `plugins/resolved-plugin.sh` were **kept** — they're guard-lib's live
plugins, registered by absolute path in `/etc/guard-lib/targets/*.conf`.

`check_and_enable_services.sh`'s `check_hosts()` function was rewritten in
the same commit (user confirmed this too) to check guard-lib state
(`guardctl file-guard status <name>`) instead of the legacy systemd
units/enforce-scripts it used to check and self-repair. Verified live:
`sudo bash check_and_enable_services.sh --status` now reports the hosts
service `ok` against the actual migrated machine, where the old code would
have reported `error` (three units it expected enabled were `disabled` by
design). `linux_configuration/.github/copilot-instructions.md` (always-loaded)
and one comment in `hosts/install.sh` were also updated to stop naming the
archived files.

**Lesson (now 3 for 4):** the check-in keeps changing scope, and this time it
changed scope _twice_ — first archive-vs-split, then "just this file" vs
"the whole dead subsystem." Keep surveying the directory (`grep -rl`, not
just the named file) before proposing an archive's file list, and keep
confirming scope growth with the user before executing it.

## 0.1 Known defect found but NOT fixed this session — flag again if touching guard-lib

`/etc/guard-lib/targets/nsswitch.conf` and `.../resolved.conf` both have
`PLUGIN=` pointing at the **repo checkout**
(`/home/kuhy/testsAndMisc/linux_configuration/scripts/periodic_background/hosts/guard/plugins/*.sh`)
instead of `/usr/local/share/guard-lib-plugins/`, which
`migrate_hosts_guard_to_guard_lib.sh`'s own header warns against by name
("pointing it at a repo checkout... silently breaks enforcement the day that
directory moves"). `/usr/local/share/guard-lib-plugins/` does not exist on
this machine at all — the migration's plugin-install step appears to have
never run. Not fixed this session: it needs a sudo mutation of a live
security-enforcement system plus `guardctl` re-registration, which the user
was not asked to approve. If a future session touches guard-lib, nsswitch,
resolved, or moves/renames this checkout, raise this first.

## 1. This session's task: none pre-selected — ask the user

Every file currently over the 250-line cap is already on an explicit
out-of-scope list from a prior session (§3 below, or the equivalent of the
old §4). There is no unclaimed split candidate right now. Options, in
roughly ascending order of friction:

- Re-run `bash meta/scripts/check_file_length.sh --all` fresh (files may have
  grown/shrunk since this doc was written) and see if a genuinely new
  candidate appeared.
- Ask the user whether any §3/§4 file should be taken out of its hold (e.g.
  "is `install_leechblock.sh`/`block_compulsive_opening.sh` still deployed at
  `/usr/local/…`? still preferred by `pacman_wrapper.sh:831`?" — re-verify,
  don't assume the old note is still true).
- Ask the user for a completely different task.

**Ask before picking** — do not silently start splitting a file that a prior
session explicitly parked, and do not assume "no candidate" means "nothing to
do here" without checking with the user first.

## 2. §3 — do not touch this session (unless the user lifts it)

`install_leechblock.sh` (485) and `block_compulsive_opening.sh` (705) are
copied to `/usr/local/…`, and `pacman_wrapper.sh:831` prefers the deployed
copy on **every pacman invocation**. Splitting them naively breaks every
`pacman -S` on this machine. Re-verify this is still true (grep
`pacman_wrapper.sh` for the deployed-copy preference) before assuming the old
note still holds — a lot has changed guard-lib-side this session, worth the
30-second re-check.

You cannot run `sudo pacman -S` from the Bash tool — it deadlocks on
`db.lck`. Hand the user a `! sudo pacman -S <pkg>` line plus the expected
output if `pacman_wrapper.sh` ever needs live verification.

## 3. Out of scope until the user says otherwise

`setup_midnight_shutdown.sh` (1734), `check_and_enable_services.sh` (1225,
edited this session but not split — same out-of-scope reasoning as before),
`generate_study_materials.sh` (1017), `pacman_wrapper.sh` (929),
`setup_night_lockdown.sh` (918), `hosts/install.sh` (913, one comment edited
this session), `EnforcementRunner.kt` (564), `DevicePolicyBridge.kt` (415),
`status_page_state.dart` (307) — check `check_file_length.sh --all` for the
current exact list before assuming this is still accurate, since files
change size between sessions.

`pacman_wrapper.sh` carries the same live-deployment trap as §2. The Kotlin
and Dart files need a different verification stack — `focus_owner` gradle
needs `JAVA_HOME=/usr/lib/jvm/java-21-openjdk` and `--rerun-tasks`; a plain
`gradlew test` reports `UP-TO-DATE` and proves nothing.

## 4. Rules that will bite you (carried forward, still true)

- **Ask before large scope changes.** Three of the last four sessions have
  changed scope mid-session because the user volunteered new information, or
  a check-in (dead-code, or in this session's case a directory survey)
  surfaced something bigger than the named file. That is fine and expected —
  just don't assume silence means "keep going as originally scoped."
- **Survey the whole directory before scoping an archive, not just the named
  file.** `grep -rl <filename-stem>` across the repo, then `ls` the file's
  own directory — this session's file list grew from 1 to 17 files this way.
- **No suppressions, ever.** No `# noqa`, no per-file-ignore added without
  asking every time, no shellcheck disable beyond what's already justified
  inline.
- **A file must not assign a global it never reads** (SC2034). The hook runs
  `shellcheck` with **no `-x`**, but `.shellcheckrc`'s
  `external-sources=true` + `source-path=SCRIPTDIR` means a `source=`
  annotation on the _sourcing_ file still resolves correctly.
- **New sourced libs need a shebang AND the executable bit**, staged with
  `git add --chmod=+x` — a plain `git add` afterwards resets it.
- `pre-commit run --files <changed>` before committing, but run it **after**
  `git add`. **`prettier` and `ci-mirror` run on pre-push.** `npx prettier
--write` any `.md`/`.json` you touch (evidence/contract files included).
- **Every commit touching code needs evidence** in
  `docs/superpowers/evidence/<slug>-<date>.json`. Staging **≥4 code files
  also needs** a fresh `docs/superpowers/contracts/*.json`. Put the
  **measured** number in it, not a rounded-up one. This session's pair
  (`archive-setup-hosts-guard-2026-08-18.json` in both `evidence/` and
  `contracts/`) documents an archive-plus-live-script-fix, not a pure split —
  read it if the next task is another archive-vs-split judgment call.
- **An archive does not need new tests.** The 100%-coverage standing decision
  binds code that gets _split_, not code that gets _deleted_. Neither this
  session's archive nor the two before it added tests for the archived code.
- Work directly on `main`. `git stash` and branch creation are blocked; use
  `git worktree add --detach` for a clean baseline (but NEVER `git filter-repo`
  inside a worktree — it shares the object store with the main repo and will
  corrupt it; always a throwaway `git clone` for that).
- **Do not wire the file-length hook into pre-commit.** It lands last, once
  `check_file_length.sh --all` exits 0.
- Watch `jscpd` (fails above 2%). Measure in a **clean HEAD worktree**.
- Cap pytest memory:
  `systemd-run --user --scope -p MemorySwapMax=0 -p MemoryMax=2G`.
- **Never let a test allocate unbounded real memory.**

## 5. Tooling reference

**`meta/scripts/check_file_length.sh --all`** — the 250-line gate. Run
**before every commit**. Applies to test files too, not just the file you're
splitting.

**`meta/scripts/shell_coverage.sh <test> <subject> [min]`** — kcov wrapper,
100% minimum. Hand it the test script **directly**; `bash script.sh`
instruments the bash binary and silently reports 0/0.

**`meta/scripts/extract_shell_functions.py`** — moves functions
brace-by-brace. **Never slice by line range**. Verify placement with `grep -c`
on the anchor.

**`meta/scripts/verify_shell_split.sh <pre-split-rev> <old> <new>...`** —
proves a split moved every function verbatim. For a **partial** split list
the old path among the new paths too.

**`meta/scripts/mutate_shell.py <spec>`** — mutation testing; optional, not
required.

**Archiving a dead file/subsystem** (no dedicated script — hand-run each
time): clone to a scratch dir, `git filter-repo --force --path <each current
path> --path <each historical path from `git log --all --follow
--name-only`>`, clone `testsAndMisc-archive` separately, add the filtered
clone as a remote, `git merge --allow-unrelated-histories`, remove stray
remote-tracking branches and the remote, push, verify with `gh api
repos/kuhyx/testsAndMisc-archive/contents/<dir>`, **then** `git rm` from
`testsAndMisc`. Read `docs/superpowers/evidence/archive-setup-hosts-guard-2026-08-18.json`
or `archive-plagiarism-tools-2026-08-18.json` for the full worked example.

## 6. Testing pattern to follow (for an actual split, if one gets picked)

The established pattern for `single_use/`-adjacent shell scripts with no
prior test coverage (used across three prior splits):

- A `lib/tests/` directory sibling to the split libs.
- A `*_harness.sh` file (sourced, not executed) with `_t_pass`/`_t_fail`/
  `_t_eq` helpers, `mktemp -d` + `trap cleanup EXIT`, and PATH-shim fakes for
  any external tool the code shells out to.
- One `test_<lib>.sh` per lib, sourcing the harness, asserting against real
  function calls (not mocks at the call-site level).
- A `test_<entry-script>.sh` that runs the **actual entry script as a
  subprocess** against the same fakes. If this test file threatens to grow
  past 250 lines, split the fixture setup into its own `*_entry_harness.sh`
  early.
- Sharp edges hit and fixed across sessions, watch for all of them again:
  - `local a="$1" b="${a}"` **fails under `set -u`** — split into separate
    `local` statements.
  - A function that calls `exit` (not `return`) on a fatal condition will
    kill the whole test script if called directly inside an `if` condition.
    Run it in a subshell: `if (fn args); then ...`.
  - A backgrounded process needs `disown` before `kill`/`wait` reliably
    affects only it.
  - **SIGINT delivery to a backgrounded job was unreliable in this
    environment; SIGTERM was not.**
  - If a script under test computes a real resource allocation (memory,
    disk) from live system state, make the relevant constants
    env-overridable and pin them to something tiny in every test.

Check the target file for anything that shells out before assuming a prior
session's fakes apply — each file is a different domain.
