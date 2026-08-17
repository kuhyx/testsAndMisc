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
