# Next session: split `install_usage_monitoring.sh`

> **Paste this whole file into a fresh Claude session opened in `~/testsAndMisc`.**
> It is self-contained. Do not go looking for the previous session's context.

## The one job

Split
`linux_configuration/scripts/periodic_background/system-maintenance/bin/install_usage_monitoring.sh`
(290 lines, over the 250-line cap by 40) into files that are each under the
cap, and **prove by execution** that it still does exactly the same thing.

This is a split, not a tooling task. The harness you need already exists and is
already proven against this exact file — use it, don't rebuild it.

Then, if there is room left in the session, take the next target using the same
method (see "If there is time" at the end).

## Why this file, and why now

57 files remain over the cap. Until last session, six installer scripts could
not be executed at all to verify a split: shell redirections (`cat > …`) are
bash builtins, so no `PATH` stub can intercept them — stub `cp`/`chmod` and the
trace comes back nearly empty, don't and the run rewrites the live system.

`meta/scripts/trace_shell_split.sh --prefix` fixed that. This file is the
smallest of the newly-unblocked set (over by only 40) and its trace is
**deterministic across runs**, so a before/after diff is a real proof rather
than a judgement call. It is the cheapest genuine win available.

## The baseline you must reproduce, byte for byte

Captured on 2026-08-16 at commit `19e652d`. Re-capture it yourself with the
procedure below rather than trusting this paste — but if your post-split trace
differs from this in any line, you have broken something:

```
=== exit status: 0
=== mutating calls (stubbed)
sudo pacman -S --needed --noconfirm atop nvtop netdata xclip
systemctl list-unit-files atop.service
sudo systemctl enable --now atop.service
systemctl list-unit-files atop-rotate.timer
sudo systemctl enable --now atop-rotate.timer
systemctl list-unit-files netdata.service
sudo systemctl enable --now netdata.service
systemctl --user daemon-reload
systemctl --user enable --now nvidia-pmon.service
systemctl --user daemon-reload
systemctl --user enable --now usage-report-catchup.timer
=== files written (prefix)
.config/systemd/user/nvidia-pmon.service size=199 sha=af8da89074b49c3f
.config/systemd/user/usage-report-catchup.service size=159 sha=bd685190626f72cb
.config/systemd/user/usage-report-catchup.timer size=206 sha=020effbe805f4ee3
.local/bin/nvidia-pmon-logger.sh size=972 sha=f307d0d3fe5f5e7f
.local/bin/usage-report-catchup.sh size=757 sha=9f4803ab157c5527
=== stdout
=== stderr
[install-usage] detected distro family: arch (Arch Linux)
[install-usage] installing: atop nvtop netdata xclip
[install-usage] enabling atop.service
[install-usage] enabling atop-rotate.timer
[install-usage] enabling netdata.service
[install-usage] setting up nvidia-pmon user service
[install-usage] usage reports will be generated hourly in @PREFIX@/.local/share/usage-reports/
[install-usage] done. Wait for the first atop sample (default 10 min), then run:
[install-usage]   python /home/kuhy/testsAndMisc/linux_configuration/scripts/periodic_background/system-maintenance/bin/usage_report.py
```

**The five content hashes are the real assertion.** The stubbed-call list only
proves the same binaries were invoked; the hashes prove every generated file
came out identical. A split that drops a heredoc shows up here and nowhere
else.

### How to capture and compare — capture the baseline IN PLACE

**Do not trace the baseline from a detached worktree.** The obvious workflow is
wrong for this file and it was measured: tracing
`/tmp/basewt/…/install_usage_monitoring.sh` makes `REPO_DIR` resolve to
`/tmp/basewt`, that path is interpolated into the generated
`usage-report-catchup.sh`, and you get a 2-line diff (`size=745 sha=d15c970e…`
instead of `size=757 sha=9f4803ab…`, plus the final stdout line) that looks
exactly like a broken split but is pure harness artefact. Normalising the trace
text does **not** fix it — the repo path is inside the hashed file content, not
just the trace.

Capture the baseline at the real repo path instead, by restoring `HEAD`'s
version in place for one run:

```bash
F=linux_configuration/scripts/periodic_background/system-maintenance/bin/install_usage_monitoring.sh

cp "$F" /tmp/split_version.sh          # keep your split work
git show HEAD:"$F" > "$F"              # restore the pre-split file in place
meta/scripts/trace_shell_split.sh "$F" --prefix /tmp/pfx-before --out /tmp/before.txt

cp /tmp/split_version.sh "$F"          # put your split back
meta/scripts/trace_shell_split.sh "$F" --prefix /tmp/pfx-after --out /tmp/after.txt

diff /tmp/before.txt /tmp/after.txt    # must be empty
git status --porcelain "$F"            # sanity: your split is back in place
```

Verified pre-split: this produces an empty diff, so any diff you see after
splitting is real signal. If your split moved code into new lib files, restore
those too (or `git stash` is blocked — use `git show HEAD:<path>` per file).

**Each run needs its own EMPTY prefix.** Reusing one leaves the first run's
files behind, so the second manifest reports writes that never happened and a
dropped write stops showing up at all. The harness refuses a non-empty prefix,
so you will get an error rather than a false pass — don't work around it by
deleting the directory contents and reusing the path out of habit.

## Four hazards specific to THIS file

Each of these was measured. Do not rediscover them.

### 1. An existing test greps the installer's SOURCE TEXT

`linux_configuration/tests/test_usage_monitoring_installer_efficiency.sh`
extracts the pmon-logger heredoc out of the installer with an awk pattern
anchored on this exact line:

```
cat > "$HOME/.local/bin/nvidia-pmon-logger.sh" << 'SCRIPT'
```

It then asserts five properties of the extracted template (no `read -t`
busy-loop, sleeps to the day boundary, blocks on `wait`, uses the `printf`
date builtin, no external `date`). **If you move that heredoc into a lib file,
this test fails with `could not extract nvidia-pmon-logger template`** — and
it is not in the pre-commit set, so nothing will tell you.

Run it before and after, every time:

```bash
bash linux_configuration/tests/test_usage_monitoring_installer_efficiency.sh
# expect: "Usage monitoring installer efficiency tests passed."
```

Either keep that heredoc in a file the test still reads, or update the test's
`INSTALLER` path in the same commit. Deciding which is part of the job; don't
leave it broken and don't weaken the assertions.

### 2. `REPO_DIR` is computed by walking up five levels from `$0`

```bash
REPO_DIR="$(dirname "$(readlink -f "$0")")/../../../../.."
```

From `…/system-maintenance/bin/` that resolves to `/home/kuhy/testsAndMisc`.
This value is **interpolated into the generated catch-up script**, so if a lib
at a different directory depth recomputes it, the generated file silently
points at the wrong repo — and the trace still exits 0. If the code that uses
`REPO_DIR` moves, pass the value in rather than recomputing it, and check the
`usage-report-catchup.sh` hash (`9f4803ab157c5527`) is unchanged.

Note `$0` in a sourced lib is the _entry point_, not the lib — which is what
makes this survivable if you pass the value, and silently wrong if you don't.

This is not theoretical: it already broke the _verification procedure_ for this
file (see "capture the baseline IN PLACE" above), producing a convincing
2-line diff out of nothing but a changed repo root. Treat any diff in
`usage-report-catchup.sh`'s hash as a `REPO_DIR` question first.

### 3. The final stdout line contains the script's own absolute path

```
[install-usage]   python /home/kuhy/…/bin/usage_report.py
```

It is built from `REPO_DIR`/`$0`. It is in the trace, so a change here fails
the diff loudly — good. Just don't "fix" it into a relative path while
splitting; that is a behaviour change disguised as tidying.

### 4. Line 222 is an UNQUOTED heredoc

`cat > "$HOME/.local/bin/usage-report-catchup.sh" << SCRIPT` — no quotes on
`SCRIPT`, so `$HOME` and `$REPO_DIR` interpolate at write time, while `\$REPO`
and `\$OUT_DIR` stay literal. The escaping inside it is load-bearing. If you
move this block, move it verbatim; a single unescaped `$` changes the
generated file and the hash will catch you.

## The seams (already mapped — verify, don't re-derive)

The file is banner-sectioned, so the seams are pre-marked:

| Lines   | Section                                                    | Notes                              |
| ------- | ---------------------------------------------------------- | ---------------------------------- |
| 1–24    | preamble, `log()`, `die()`                                 | shared by everything               |
| 25–55   | distro detection → `FAMILY`                                | `FAMILY` crosses into packages     |
| 56–120  | package names, `pkg_name`, `clipboard_pkg`, resolve `pkgs` | `FAMILY` in, `pkgs` out            |
| 121–136 | `enable_unit`, system services                             | uses `pkgs`                        |
| 137–214 | NVIDIA pmon logger (guarded)                               | **holds the heredoc test 1 greps** |
| 216–290 | usage-report catch-up timer                                | `REPO_DIR`, unquoted heredoc       |

State crossing any seam: `FAMILY`, `pkgs`, `clip`, `unit_dir`, `REPO_DIR`.
Five globals — few enough that this is a genuinely tractable split, unlike the
named blockers in `refactor_claude_todo_resume.md`.

`nvidia-smi` IS present on this machine, so the 137–214 branch really executes
in the trace. That is why the baseline has `nvidia-pmon.service` in it. Don't
assume the guarded block is untested — it is the opposite.

There is **no `lib/` directory** in `…/system-maintenance/bin/` yet. Elsewhere
in the repo the convention is a sibling `lib/` holding sourced `.sh` files with
a shebang and the executable bit (see `meta/scripts/lib/`). Follow it.

## Rules that will bite you

- **`SCRIPT_DIR` must resolve symlinks**:
  `SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"`. Plain
  `dirname` is string manipulation; adding a `source` line to a script reached
  through a symlink turns a latent wrong value into an instant `set -e` exit.
  This has already broken `lint_python.sh` once.
- **Wrapping top-level code in a function changes what `set -e` sees.** A bare
  `((x > 0)) && FLAG=true` as the last statement of a function becomes its
  return value; if false, the script dies. Check the last statement of every
  function you create; append `|| true` if it is a bare conditional.
- **Don't make a clean file `shfmt`-dirty.** This file is _already_
  `shfmt -d` dirty, so don't let that mislead you: the rule is not to make it
  **worse**, and any NEW lib file you create must be clean. `shellcheck` on the
  original is currently CLEAN — keep it that way.
- **No suppressions.** No `# shellcheck disable`, no per-file ignores. Fix the
  finding or restructure. If a lint fix seems to require touching behaviour,
  stop and re-read — last session a lint fix silently neutered a regression
  fixture by making an added `echo` the function's last statement, turning
  exit 1 into exit 0 while still "passing".
- Every commit touching code needs an evidence JSON in
  `docs/superpowers/evidence/`; **≥4 staged code files** additionally needs a
  fresh `docs/superpowers/contracts/*.json`
  (`python3 meta/scripts/validate_contract.py <file>`).
- New `.sh` files need the executable bit or the commit hook rejects them.
- Markdown needs `npx prettier --write` — prettier is pre-push only, so a file
  that passes every per-commit gate can still fail the push.
- Work directly on `main`; commit and push. `git stash` and branch creation are
  blocked by hooks. `git worktree add --detach` is the usual way to get a clean
  baseline — but **not for this file's trace**; see "capture the baseline IN
  PLACE" above for why, and use `git show HEAD:<path>` instead.
- `git push` runs `ci-mirror` (clean-venv install + `pre-commit --all-files` +
  pytest) and takes minutes. Never edit files while a push is running.
- **Do not wire the file-length pre-commit hook.** It must land last, only once
  `bash ~/utils/scripts/check_file_length.sh --all` exits 0, or every push
  fails.

## Read these first

1. `docs/shell-split-verification.md` — how a green split is still broken. The
   `--prefix` section covers the manifest, the empty-prefix rule, and the
   `require_root` truncation trap.
2. `docs/shell-split-recipes.md` — how to actually make a split.
3. `meta/scripts/trace_shell_split.sh --help` — the harness.

## Definition of done

- `install_usage_monitoring.sh` and every file split out of it are **under 250
  lines** (`bash ~/utils/scripts/check_file_length.sh --all` no longer lists
  any of them).
- `diff /tmp/before.txt /tmp/after.txt` is **empty** — same exit status, same
  stubbed calls in the same order, and all five content hashes identical.
- `bash linux_configuration/tests/test_usage_monitoring_installer_efficiency.sh`
  still prints "Usage monitoring installer efficiency tests passed."
- `shellcheck` clean on every touched file; no new `shfmt` damage; zero
  suppressions.
- `~/.config/systemd/user/` and `~/.local/bin/` untouched by the verification
  runs — confirm by `ls -la` before and after, and check the mtimes of
  `nvidia-pmon-logger.sh` and `usage-report-catchup.sh` still read **May 2026**.
  If either shows today's date, a run escaped the prefix; stop and say so.
- Committed and pushed, with evidence (and a contract if ≥4 code files).

## If there is time

Take the next target by the same method. Pick by **verifiability**, not by line
count — a big file you can run beats a small one you cannot:

```bash
bash ~/utils/scripts/check_file_length.sh --all
```

Newly unblocked by `--prefix`, in ascending difficulty:
`install_pacman_wrapper.sh` (316), `nvidia_troubleshoot.sh` (336, needs
`--bind-abs /etc/modprobe.d --bind-abs /etc/X11 --bind-abs /etc/profile`),
`setup_thorium_startup.sh` (443), `install_leechblock.sh` (485 — confirm where
`INSTALL_ROOT`/`VERSION_DIR` point BEFORE the first run, it uses
`rsync -a --delete`).

**Still out of scope:** `block_compulsive_opening.sh` (705) — `install_all`
copies the running script into `/usr/local/bin`, and an entry+lib shape ships
an entry whose `SCRIPT_DIR` has no `lib/`, breaking three daily-use apps plus
the pacman rewrap hook. Leave it.

Also still blocked on a NAMED blocker, not on line count — do not "just split"
these: `check_and_enable_services.sh` (1337, every `check_*` writes one
`SERVICE_STATUS`), `steam_compatibility.sh` (663), `libre_translate.sh` (488,
~19 globals cross any seam), `enforce_vbox_hosts.sh` (443, every seam falls
inside a heredoc). See `refactor_claude_todo_resume.md`.
