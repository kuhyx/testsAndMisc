# Shell split verification: how a green split is still broken

Split out of `docs/shell-split-recipes.md` when that file hit the same 250-line
cap it exists to serve. That file covers **how to make** a split; this one
covers **how to find out it is wrong**. Read both before the next
`linux_configuration` or `phone_focus_mode` split.

Every section below cost a failed run, a revert, or — once — a live system
mutation.

### A `--skip-install` flag is not evidence the script is safe to run

`shell_check.sh` gates only `install_if_missing`'s pacman branch on
`SKIP_INSTALL`. The AUR branch inside `install_linters` runs regardless, so a
backgrounded "baseline" run installed four packages before it was killed
mid-`makepkg`. Decision 6 was violated by a flag that looked like permission.

Before running any script to capture a baseline, grep the flag's variable and
confirm it gates **every** mutation path, not just the first one:

```bash
grep -n 'SKIP_INSTALL\|DRY_RUN' <script>   # then read each hit
```

`--list-only` was the genuinely safe path here, because it returns before
`install_linters` is reached at all.

### Check whether the target is DEPLOYED as a single file — the trace cannot

Before designing seams, find out whether some other script copies the target
somewhere and runs it from there. An entry+`lib/` shape ships an entry whose
deployed `SCRIPT_DIR` has no `lib/`, so it dies on its first `source` under
`set -e` — while your trace stays green, because the trace runs the repo copy
where `lib/` exists.

```bash
grep -rn '<target-basename>' linux_configuration/ --include='*.sh' \
  | grep -v '<the target itself>:'
```

Confirmed blocked on this, not theoretically: `install_leechblock.sh` (the
pacman installer `cp`s it to `/usr/local/share/digital_wellbeing/` and
`pacman_wrapper.sh:831` prefers that copy on **every pacman invocation**) and
`block_compulsive_opening.sh` (`install_all` copies itself to
`/usr/local/bin`). A target invoked as `$CONFIG_DIR/scripts/...` is fine.

### A stubbed run cannot reach a bug in a seam that passes state

`meta/scripts/verify_shell_split.sh` and the hand-rolled `declare -F` probe
both **source the libs and never call the functions**. That is enough to prove
every `source` line resolves, and nothing more. The `analyze_repo.sh` split
passed `bash -n`, `shellcheck`, a function-set diff, a line-set diff and the
stubbed probe — and still shipped a script that aborted immediately after
language detection. Two separate bugs, neither reachable without executing:

- **`set -e` and the function tail.** Eight `((LANG_FILES[x] > 0)) && HAS_Y=true`
  lines were top-level statements, where a false `&&` merely leaves `$?`
  non-zero. Wrapped into a function they become its _return value_, and the
  last one (java, false for most repos) killed the script. Any time you wrap
  former top-level code in a function, check what its **last statement** is;
  append `|| true` if it is a bare conditional.
- **A self-referencing nameref.** `local -n LANG_CODE_FILES="$1"` pointing at a
  global of the same name still moves data on bash 5.3, but warns
  `circular name reference` on _every access_ — straight into the script's
  output. Name the local something else (`_code_files`).

So: when a seam passes state, run the thing. Stub only the parts that mutate
the system, and diff the generated artifacts against a detached worktree at the
pre-split commit. That comparison is what proved the fix — same file set, every
text artifact byte-identical.

## The harness and the fixtures

Everything about _running_ the check — `trace_shell_split.sh`, the `--prefix`
mode for scripts whose job is placing files, the regression fixtures, the
entry-point and `shfmt` traps — moved to
**`docs/shell-split-harness.md`** when this file hit the same 250-line cap it
exists to serve. This file stays the _why_; that one is the _how_.

### Prove the move was verbatim: `meta/scripts/verify_shell_split.sh`

The Python splits in this repo are verified with a throwaway `ast` identity
check. There is no `ast` for bash, so the shell equivalent normalises through
`shfmt -mn` (minify: strips comments and indentation, keeps logic) and compares
a hash per top-level function:

```bash
bash meta/scripts/verify_shell_split.sh HEAD <old-path> <new-path>...
# IDENTICAL: all N top-level functions moved verbatim
```

It reports which function changed, so a diff points at the seam rather than the
whole file. Run it after every split, and again after `shfmt`/pre-commit
autofixes — reordering an import or reflowing a line is exactly what it is
designed to see through.

**Verify the harness before trusting it.** A normalizer that silently passes
everything is worse than none. The three checks it must survive:

| input                                            | expected                                |
| ------------------------------------------------ | --------------------------------------- |
| unchanged copy of the file                       | `IDENTICAL`                             |
| comments/blank lines/indentation changed         | `IDENTICAL`                             |
| one character of logic changed (`"$1"` → `"$2"`) | `DIFFERENCE FOUND`, naming the function |

The first attempt at that mutation test used `sed 's/exit 1/exit 2/'` on a file
containing no `exit 1`. It reported `IDENTICAL` — not because the harness was
broken, but because the mutation never applied. Confirm the mutation actually
changed the file (`diff` it) before concluding anything about the harness.

### Deployment triage of the over-cap scripts (2026-08-17)

Run before designing any seam, per the section above. `deploy.sh` copies a
**hardcoded per-file list** into `/data/local/tmp/focus_mode` and never deploys
`lib/`:

- **`phone_focus_mode/*` (8 over-cap scripts)** — deployed individually.
  A new sibling must be added to `deploy.sh`'s copy list **in the same commit**,
  or focus mode dies on the phone at its first `source`. These scripts source
  only `config.sh`, which is on that list, so a sibling-file seam is workable —
  an entry+`lib/` seam is not.
- **`install_leechblock.sh`, `block_compulsive_opening.sh`** — copied to
  `/usr/local/…` and preferred there by `pacman_wrapper.sh:831` on every pacman
  invocation. Teach the installer to deploy the directory first, in its own
  commit. Highest blast radius; do these last.
- **`hosts/install.sh`, `setup_hosts_guard.sh`, `lib/monitor.sh`** — install
  helper scripts to `/usr/local/sbin` or `/usr/local/bin`; check whether the
  file being split is itself the deployed one.
- **The other 16** (`fresh-install/main.sh`, `nvidia_troubleshoot.sh`,
  `setup_passwordless_system.sh`, `clean_audio.sh`, `enforce_vbox_hosts.sh`,
  `migrate_hosts_guard_to_guard_lib.sh`, `libre_translate.sh`,
  `diagnose_pacman_hook_stall.sh`, `install_plagiarism_tools.sh`,
  `steam_compatibility.sh`, `deploy.sh`, `setup_night_lockdown.sh`,
  `pacman_wrapper.sh`, `generate_study_materials.sh`,
  `check_and_enable_services.sh`, `setup_midnight_shutdown.sh`) — no deployed
  copy found, so an entry+`lib/` shape is safe.

### A lib must contain the readers of every global it assigns

`install_pacman_wrapper.sh:29` records the constraint: a **definitions-only**
lib "assigns without referencing, which is SC2034, and the repo forbids
suppressions." The rule that follows from it is not "assignments stay in the
entry script" — it is that a file must not assign a variable it never reads.
A lib holding both the writer and its readers is clean.

Getting this inverted is easy and costs several revert cycles.
`libre_translate.sh` was split with `parse_args` (the writer) left in the entry
and `health_check` / `sample_request` / `start_container_ephemeral` (the
readers) moved to the lib — the worst of both, and SC2034 fired on nine
globals. The fix is to colocate: move the writer **and** its consumers into the
same file.

The pre-commit hook is `shellcheck` with **no `-x`**, so each file is analysed
standalone and a `# shellcheck source=` directive will not make the checker
follow the link. Verify by running `shellcheck <lib>` on its own before
committing; the hook will not be any more forgiving.

This is the shell analogue of the `monkeypatch.setattr` target trap: the
question is always which file's namespace owns the name.

**`libre_translate.sh` (488) is parked.** What remains after its clean seams
are taken is `parse_args` (111 lines), `write_env_file`, `detect_container_user`
and `main`, which between them assign and read the same configuration globals.
Getting the entry under the cap needs `parse_args` restructured rather than
relocated — a refactor, not a verbatim move, so it is out of scope for this
method. Attempt it with a test harness, or accept an entry that stays over.

### kcov silently under-reports some subjects: never trust a percentage alone

`rpi_nc_install.sh` measures **10/88 = 11.36%** under
`meta/scripts/shell_coverage_jail.sh`, reporting lines 13–60 as covered and
everything from 61 on as not. The code past line 61 provably runs: the suite's
29 assertions pass, and both `/root/.nextcloud_db_password` (line 61) and
`/etc/apache2/sites-available/nextcloud.conf` (a heredoc ending at line 100)
exist on disk after a run. The two sibling libs in the same directory measure
sensibly, so this is not universal — and nobody has bounded which subjects it
affects.

**Five hypotheses have each been tested against a minimal reproduction and
DISPROVEN. Do not retry them:**

1. kcov traces correctly **past a heredoc**.
2. kcov traces correctly **into a `$(...)` command substitution**.
3. kcov traces correctly **past a heredoc-fed stub reading stdin via `$(cat)`**.
4. kcov traces correctly **past a `cd` that relocates the process** (including
   `cd /tmp`, where the jail's own working dir lives) — lines after the `cd`
   are recorded.
5. kcov traces correctly **past a heredoc piped into a stubbed external** —
   `mysql -u root <<EOF` with a `cat >/dev/null` stub, under strict mode.
   Lines after it are recorded.

**One CONFIRMED artifact (hypothesis 6), reproduced minimally:** kcov counts
the _continuation lines of a multi-line quoted argument_ as instrumentable
statements that never run. A `perl -0777 -i -pe '<newline>...s!a!b!;<newline>'`
block reports its inner lines at zero hits while the line after it is covered.
This accounts for `dwm_config.sh` lines 64-66 and 98-101, and for any
`done < <(...)` process substitution. These lines are **not statements**, so
the denominator is wrong, not the numerator.

That artifact does NOT explain the second pattern: ordinary statements inside
functions that provably execute. In `dwm_config.sh`, `build_install`,
`build_pointer_confine`, `write_session_files` and `verify` all run -- proved
with an `exit 43` sentinel placed after their assertions, which fired -- yet
their bodies report zero hits. `rpi_nc_install.sh` behaves the same way. A
sixth hypothesis (that the jail's `exec`-ing `sudo` shim or a pipeline loses
the trace) was tested minimally and **DISPROVEN**: both trace correctly.

The cause of that second pattern remains unknown. The practical rule:

> **A suspicious percentage means re-measure, not re-write the test.** If a
> suite's assertions pass while its number looks absurd, suspect the
> instrument before suspecting the tests. **Never "fix" a number by weakening
> an assertion.**

Note the failure is _silent and one-directional_: it under-reports, so it can
only ever keep a lib on the allowlist that deserves to come off. It cannot
promote an untested lib. That is why the campaign can continue around it.

**The under-report is contagious across processes in one jail.** Measured on
`rpi_nc_ca.sh`: run alone its suite reports **73/73 = 100.00%**, reproduced
twice. Run through `run_all.sh` it reports **72/73 = 98.63%**, also twice --
and bisecting the five sibling suites shows a single culprit, `test_dwm_config.sh`.
Run `dwm_config` first and `rpi_nc_ca` loses line 141 (`cat <<'EOF'`, an
ordinary statement); run any other sibling first and it keeps it. The CA
suite's assertions all pass either way, confirmed with an exit sentinel, so
nothing is actually untested.

This matters for the gate: `is_covered()` measures through `run_all.sh`, so
the _runner's_ number is the one that counts, and it can be lower than the
same suite's own number for reasons that have nothing to do with the tests.
Never report the single-file figure as the lib's coverage.

**Use an `exit <n>` sentinel to tell the two apart.** The jail discards a
case's stdout, so a suite's own report is invisible; but a non-zero exit is
surfaced by `--fail-on-case-error`. Temporarily ending the suite with
`exit 42` at a chosen point turns "did execution reach here?" into a yes/no
the jail will answer. That is what proved the second pattern is a tracing
failure and not an aborted suite.
