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

Three things to watch:

- **A silent stub produces an identical, meaningless trace.** This is the
  trap. `du` stubbed to print nothing makes `size=$(du -sk x)` empty, so every
  `((size > 0))` is false, every guarded branch is skipped, and two such traces
  match perfectly while exercising none of the code you changed. Give
  value-producing commands a plausible output: `--stub 'du=4096\t/some/dir'`.
  Measured on a fixture: the empty stub printed `size=[]` / `branch skipped`
  and never reached the guarded `sudo rm -rf`; the valued stub printed
  `size=[4096]` / `BRANCH TAKEN` and captured it. Ask of every trace: _did this
  actually go down the branch I touched?_
- **Stubs always exit 0.** A script that branches on a real failure status
  takes a path it would not take live. Hand-write a stub for those and say so
  in the split's evidence file.
- **Anything not stubbed runs for real.** `git`, `curl`, `wget` and `makepkg`
  are deliberately excluded from the default set, because many scripts read git
  state harmlessly and a blanket stub would change what they see. Grep the
  target for network and build verbs, then pass them:
  `--stub git,curl,makepkg`.

### `--prefix` — scripts whose job is placing files

Shell redirections (`cat > /etc/modprobe.d/x.conf`) are builtins, so no `PATH`
stub can intercept them. Stub `cp`/`chmod`/`ln` and the trace is nearly empty;
don't, and the run rewrites the live system. `--prefix` (added 2026-08-16)
resolves that in two layers — see `meta/scripts/lib/trace_prefix.sh`:

```bash
# $HOME-rooted destinations: no bwrap, no root needed
meta/scripts/trace_shell_split.sh install_usage_monitoring.sh --prefix /tmp/pfx

# hardcoded absolutes: bind each LEAF directory
meta/scripts/trace_shell_split.sh nvidia_troubleshoot.sh --prefix /tmp/pfx \
  --bind-abs /etc/modprobe.d --bind-abs /etc/X11 --stub git,lsmod,nvidia-smi
```

`HOME` **and every `XDG_*` base** are redirected. Exporting the XDG vars
explicitly is not belt-and-braces: `install_leechblock.sh` reads
`XDG_DATA_HOME` directly and then runs `rsync -a --delete` at it, so inheriting
the caller's real value would delete live data.

The trace gains a `=== files written (prefix)` section listing every file with
its size and a content hash. **That section is the point**: without it a
dropped `cat >` shows up as nothing at all — same exit status, same stubbed
calls, same stdout — and the traces match while one lost a file. Measured on
the `dropped_write_{before,after}.sh` fixture pair: with the manifest the lost
`.timer` is a one-line diff; with the section stripped the two traces are
byte-identical, i.e. the pre-`--prefix` harness passed that broken split.

Four traps, each of which cost a debugging round:

- **Bind leaf directories, never `/etc`.** Binding `/etc` wholesale shadows
  `/etc/passwd` and `/etc/os-release`. Measured: `$SUDO_USER` lookup collapsed
  to `/home//pyroveil`, `/etc/profile` became "No such file or directory", and
  a nested `/etc/X11` bind was masked so its write vanished from the manifest.
  All three look like a broken split. The scanner therefore never emits a bare
  `/etc`.
- **`require_root` truncates a stubbed run to nothing.** `lib/common.sh` does
  `exec sudo "$0" "$@"`; under the `sudo` stub that records one line and exits
  0 — a three-line trace that diffs clean against _any_ split. `--bind-abs`
  runs under `bwrap --unshare-user --uid 0`, so `$EUID` is 0 and the script
  proceeds for real. Without a bind there is no uid 0 and the truncation is
  silent, so check the trace actually entered the code you moved.
- **Unquoted heredocs bake the prefix into the artifact.**
  `install_usage_monitoring.sh:222` uses `<< SCRIPT`, so `$HOME` interpolates
  at write time. Hashes are taken over content with the prefix normalized to
  `@PREFIX@`; without that, a `mktemp -d` prefix makes every run differ.
- **A timestamp the target embeds still varies.** `nvidia_troubleshoot.sh`
  writes `$(date)` into its config, so its hash changes every run; compare the
  file list and sizes. Don't freeze the clock — that would hide real changes.

Anything absolute that was _not_ bound fails read-only/EPERM rather than
succeeding, so Decision 6 holds by construction. `--prefix` **refuses to run**
when the target writes to absolute paths and no `--bind-abs` was given, listing
the paths it found; the scan follows variables
(`MODPROBE_DIR="/etc/modprobe.d"` → `cat >"$CONFIG_FILE"`), because a
literal-only scan found nothing and produced a silent empty manifest.

Verified untouched after the runs above: `~/.config/systemd/user`,
`~/.local/bin`, `~/.local/share`, `/etc/modprobe.d` (identical listings), and
`systemctl --user list-unit-files | grep -c usage-report` unchanged at 2.

`block_compulsive_opening.sh` remains out of scope: `install_all` copies the
running script into `/usr/local/bin`, and the handoff records that a bad split
there breaks three daily-use apps plus the pacman rewrap hook.

### Regression fixtures

`meta/scripts/fixtures/` holds runnable reproductions of every trap above, so a
harness change can be checked instead of trusted:

| Fixture                           | Reproduces                                      |
| --------------------------------- | ----------------------------------------------- |
| `set_e_function_tail.sh`          | exit 1, later calls missing from the trace      |
| `circular_nameref.sh`             | exit 0, correct stdout, warning only in stderr  |
| `valued_stub_branch.sh`           | the silent-stub trap (`--stub du` vs `du=4096`) |
| `dropped_write_{before,after}.sh` | a split that silently loses one write           |

A lint fix once broke one of these invisibly: adding a trailing `echo` to
satisfy SC2034 made _that_ echo the function's last statement, so the fixture
exited 0 and reproduced nothing while still "passing". Re-run the fixtures
after touching them, and check the exit status is still the one documented.

**Run the baseline from the script's own directory** when it reads relative
paths. `fresh-install/main.sh` reads `aur_packages.txt` and
`pacman_packages.txt` from the cwd; tracing it from elsewhere dies at the first
read and looks exactly like a broken split.

Note it does not need a `main()`, which matters: none of the remaining
near-miss shell targets (`install_usage_monitoring.sh`,
`install_pacman_wrapper.sh`, `disk_cleanup_check.sh`, `fresh-install/main.sh`)
have one, so `verify_shell_split.sh` cannot check any of them.

Note the knock-on: renaming the nameref local hides the array from shellcheck
(SC2034), because it is then only ever named as a bare word. Pass the name
through a variable (`CODE_FILES_MAP="LANG_CODE_FILES"`) so the reference is
real, rather than suppressing.

### Verify through every entry point, especially symlinks

Adding a `source "$SCRIPT_DIR/lib/..."` line to `meta/lint_python.sh` broke
`./lint_python.sh` from the repo root, because that root path is a **symlink**
into `meta/` (so are `pyproject.toml`, `requirements.txt`, `run.sh`, `.fvmrc`).
`SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` does not resolve
symlinks — `dirname` is string manipulation — so it became the repo root, where
`lib/` does not exist, and `set -euo pipefail` turned that into an instant exit.

It was invisible because every check used `bash meta/lint_python.sh`, the one
path that cannot fail. Before splitting a script, ask how else it is reachable:

```bash
find . -maxdepth 2 -type l -lname '*<script>*'   # symlinks pointing at it
grep -rn '<script>' .github/workflows/ .pre-commit-config.yaml meta/run.sh
```

The fix is the pattern already used elsewhere in this repo:

```bash
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
```

Note the pre-split script had the same unresolved `SCRIPT_DIR`; it only fed
`PROJECT_ROOT`, so the bug was latent. Adding a `source` line is what turns a
quiet wrong value into a hard failure — which is exactly what a split does.

### Do not make a clean file shfmt-dirty

157 of 298 `linux_configuration` shell files already fail `shfmt` and there is
no `.editorconfig` or shfmt pre-commit hook, so `shell_check.sh`'s `run_linters`
exits 1 on the full tree regardless. That is not licence to add more: check
`shfmt -d <file>` before and after a split. `analyze_repo.sh` was clean and a
split made it dirty over one double blank line.

`shfmt -w` also **deletes comment banners** it considers stray — it removed a
`#====` STEP header. Re-count the banners after running it.
