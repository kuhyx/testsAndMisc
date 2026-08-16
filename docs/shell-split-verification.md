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
backgrounded "baseline" run installed four packages (`python-pbr`,
`python-fixtures`, `python-discover`, `python-reno`) before it was killed
mid-`makepkg`. Decision 6 was violated by a flag that looked like it granted
permission.

Before running any script to capture a baseline, grep the flag's variable and
confirm it gates **every** mutation path, not just the first one:

```bash
grep -n 'SKIP_INSTALL\|DRY_RUN' <script>   # then read each hit
```

`--list-only` was the genuinely safe path here, because it returns before
`install_linters` is reached at all.

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

### `trace_shell_split.sh` — the run, made routine

`meta/scripts/trace_shell_split.sh` (added 2026-08-16) does the stubbed run for
you. It shadows ~30 mutating binaries (`sudo`, `pacman`, `systemctl`, `adb`,
`nft`, `mount`, `mkinitcpio`, `reboot`, …) with `PATH` stubs that record each
call and exit 0, runs the script, and prints a diffable trace: exit status,
stubbed calls in order with arguments, stdout, stderr.

```bash
# baseline, in a detached worktree at the pre-split commit
meta/scripts/trace_shell_split.sh <script> --out /tmp/before.txt
# after the split
meta/scripts/trace_shell_split.sh <script> --out /tmp/after.txt
diff /tmp/before.txt /tmp/after.txt
```

It was verified against both bugs above: the `set -e` function tail shows up as
exit 1 with the later calls missing from the trace, and the nameref shows up as
`circular name reference` in stderr despite exit 0 and correct stdout. A run
against a fixture calling `systemctl` left the real unit untouched.

Two things it does not do:

- **Stubs always exit 0.** A script that branches on a real failure status
  takes a path it would not take live. Hand-write a stub for those and say so
  in the split's evidence file.
- **Anything not stubbed runs for real.** `git`, `curl`, `wget` and `makepkg`
  are deliberately excluded from the default set, because many scripts read git
  state harmlessly and a blanket stub would change what they see. Grep the
  target for network and build verbs, then pass them:
  `--stub git,curl,makepkg`.

Note it does not need a `main()`, which matters: none of the remaining
near-miss shell targets (`install_usage_monitoring.sh`,
`install_pacman_wrapper.sh`, `disk_cleanup_check.sh`, `fresh-install/main.sh`)
have one, so `verify_shell_split.sh` cannot check any of them.

Note the knock-on: renaming the nameref local hides the array from shellcheck
(SC2034), because it is then only ever named as a bare word. Pass the name
through a variable (`CODE_FILES_MAP="LANG_CODE_FILES"`) so the reference is
real, rather than suppressing.

### Do not make a clean file shfmt-dirty

157 of 298 `linux_configuration` shell files already fail `shfmt` and there is
no `.editorconfig` or shfmt pre-commit hook, so `shell_check.sh`'s `run_linters`
exits 1 on the full tree regardless. That is not licence to add more: check
`shfmt -d <file>` before and after a split. `analyze_repo.sh` was clean and a
split made it dirty over one double blank line.

`shfmt -w` also **deletes comment banners** it considers stray — it removed a
`#====` STEP header. Re-count the banners after running it.
