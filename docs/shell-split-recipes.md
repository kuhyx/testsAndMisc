# Shell split recipes for the 250-line cap

Split out of `refactor_claude_todo_resume.md` (which is itself capped).
Applies to `linux_configuration/` and `phone_focus_mode/`.

`linux_configuration` and `phone_focus_mode` have **no test suite and no
coverage gate**, so none of the above transfers. Decision 6 governs:
`bash -n` + `shellcheck` + `systemctl cat` path checks, and **never execute an
enforcement script that mutates the live system or the phone.**

- After each split, `bash -n` and `shellcheck` the entry script _and_ every new
  lib. **Neither catches a `source` line that resolves to the wrong path** —
  both passed clean on a split whose lib was unreachable at runtime.
- So the real check is a **stubbed run**, scripted as
  `meta/scripts/verify_shell_split.sh <script> <function>...`: it mirrors the
  repo tree into a `mktemp -d`, replaces the final `main` invocation with a
  `declare -F` probe, and runs that. The `source` lines execute and nothing
  else, which makes it safe for installers. Across 18 splits it caught five
  bugs no static check did. It needs the script to end in `main "$@"`; for the
  rest, use the by-hand checks below.
- **But a stubbed run only proves the `source` lines resolve.** It sources the
  libs and never calls them, so it cannot reach a bug in a seam that passes
  state — `analyze_repo.sh` passed every static check plus the stub and still
  aborted at runtime. See **`docs/shell-split-verification.md`**, which now
  holds every "the split was green and still wrong" lesson, including the
  `set -e` function-tail trap and the flag that looked safe and was not, and
  **`docs/shell-split-harness.md`** for running `trace_shell_split.sh` itself.

### Use `${BASH_SOURCE[0]}`, not `$0`

The repo's existing convention is
`SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"`, which works only while the
script is executed directly. `$0` is the **sourcing** script, so the moment an
entry script is itself sourced, `SCRIPT_DIR` points somewhere else and the lib
is not found. Write new ones as:

```bash
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
```

`readlink -f` is still required — it is what makes the one symlinked script
(`/usr/local/bin/start-player2`) resolve back into the repo.

### Shape of a new lib (two hooks disagree unless you get this right)

Follow `lib/common.sh`: **shebang present, file executable.** The two
obvious-looking alternatives each fail a hook:

- No shebang → `shellcheck` SC2148 ("target shell unknown").
- Shebang but not executable → `check-shebang-scripts-are-executable`.

So: `#!/bin/bash`, `chmod +x`, and **no `set -euo pipefail`** — a sourced lib
inherits the caller's strict mode, and redeclaring it is duplicated
boilerplate that feeds jscpd. Say so in the lib's header comment.

- **Two live units point at repo paths** and break if a file moves or is
  renamed. `systemctl cat` them after touching either:
  - `/etc/systemd/system/dns-blocklist-refresh.service` →
    `./features/setup_dns_blocker.sh refresh`
  - `/etc/systemd/system/media-organizer.service` →
    `./utils/organize_downloads.sh`

  Every other in-repo unit references an installed copy under `/usr/local/`,
  so those are only at risk if the _installer_ is what you split.

## Which scripts escape the repo (enumerated 2026-08-16)

A split is only safe if the file still resolves its libs from wherever it
actually runs. Two ways a script leaves the repo, both silent when broken:

- **Copied out** — only three, all under
  `periodic_background/hosts/guard/pacman-hooks/`, installed to
  `/usr/local/share/hosts-guard/` by `hosts/guard/install_pacman_hooks.sh`.
  Splitting any of those three means the installer must copy the new libs too,
  **in the same commit** — the same trap as `phone_focus_mode/deploy.sh`.
- **Symlinked in** — exactly one: `/usr/local/bin/start-player2` →
  `gaming/start-player2.sh`. `${BASH_SOURCE[0]%/*}` resolves to
  `/usr/local/bin` there, so a lib path must go through
  `readlink -f "${BASH_SOURCE[0]}"` first.

Everything else under `/usr/local/` is **generated** by an installer (heredoc
or `cat >`), not copied, so splitting the generator is safe as long as the
generated content is unchanged. Re-run both checks if that assumption is ever
in doubt:

```bash
find /usr/local/bin /usr/local/sbin -maxdepth 1 \( -type l -o -name '*.sh' \) \
  -exec readlink -f {} \; | grep testsAndMisc
grep -rn -E '^\s*(sudo )?(install|cp)\s.*(SCRIPT_DIR|REPO).*/usr/local/' \
  linux_configuration --include='*.sh'
```

## Three traps found while splitting (2026-08-16)

- **A script with no `main()`.** `setup_periodic_system.sh` defines functions
  and then runs a block of top-level calls. Moving that block into a lib
  changes _when_ it runs. Move **only function definitions**; leave every
  top-level invocation in the entry script, and check the `source` line comes
  before the first call.
- **A script that needs root at source time.** The same file asks for sudo
  while sourcing, so the stubbed run is not available. Fall back to: source
  line before first call, plus every invoked function defined exactly once
  across the two files (`grep -c '^fn() {'` in each).
- **An entry script that already declares `SCRIPT_DIR`** — often `readonly`.
  Reuse it instead of adding a second declaration, or the script dies with
  `readonly variable`. `bash -n` and `shellcheck` both pass on that.

### Splitting the same file twice is the risky move

The splitter inserts its `source` line relative to the file as it currently
stands, so a second pass can **displace the first pass's line**. On
`20-dump-stock.sh` that left `verify_dump` called but never defined, and the
repair then put the line inside the lib rather than the entry script.

After any double split: `grep -n 'source "\$SCRIPT_DIR' <entry> <libs>` and
check that the entry sources **every** lib and **no lib sources another**.
`shellcheck` without `-x` on a lib is what surfaces this — a lib sourcing a
sibling reports SC1091 "does not exist", because the relative path is only
valid from the entry script's directory.

### Globals read across the seam

Common, and the fix depends on how many:

- **One or two, module-level constants** — rename to UPPERCASE, matching what
  the surrounding files already do (`QUIET`, `FORCE`). Worked for
  `DESKTOP_DIR` in `fix_unity.sh`.
- **A flag the caller computes** — pass it as a parameter. Worked for
  `persist_with_systemd_logind`.
- **Several, threaded through three files** — stop. See below.

### Unguarded `cd` turns up constantly

Two found in five splits (`build_website`, the study-material generator), both
pre-existing, both a real bug: a failed `cd` runs the next command in the
caller's directory. They only surface on splitting because a moved function
gets linted in isolation. Fix with `|| die` / `|| return 1`, never a suppression.

### Scripts that generate config need a content check

For a setup script, "the functions still exist" is the wrong question — what
matters is that the compose file, unit or settings file it writes is unchanged.
The stubbed run cannot tell you that. Compare the moved region before and
after, ignoring comments and ordering:

```bash
git show HEAD:<script> | awk '/^the_func\(\) \{/,/^\}$/' \
  | grep -vE '^\s*(#|$)' | sort | md5sum
cat <the new libs> | grep -vE '^\s*(#|$)' \
  | grep -v '^new_func_name\|^}' | sort | md5sum
```

Equal hashes mean every emitted line survived and only wrappers were added.
Used on `setup_searxng.sh`, whose `write_stack` was 342 lines of heredoc
emitting three files.

**Keep each heredoc with the comment that explains it.** `setup_searxng.sh`
records why `settings.yml` is mode 640 and not 600 (at 600 the granian worker
dies with EACCES) — that comment is worth more than the code around it.

### A seam inside a heredoc produces a file that will not parse

The worst failure in this effort: the split of `enforce_vbox_hosts.sh` cut
between `cat <<EOF` and its terminator, leaving a lib with an unterminated
here-document. `shellcheck` on the **entry** reported only SC1094 "parsing of
sourced file failed", which reads like a linting nicety rather than a broken
file, and the entry itself still linted clean with `-x`.

`meta/scripts/verify_shell_split.sh` now runs `bash -n` over every lib
**before** linting the entry and names the offending file. The splitter is
still heredoc-unaware, so check for `<<` in the region you are moving before
choosing a boundary.

### A widely-sourced library splits cleanly — keep it as the entry point

`common.sh` (620, sourced by **49** scripts) and `mtk_common.sh` (503, by 7)
both split with no consumer edited: the original file keeps its path and
sources its own parts, which is the shape the handoff prescribes for
`config.sh`. Move any array or constant along with the function that reads it.

**The check that matters is the exported function set**, not a passing lint:

```bash
bash -c 'source <lib>; declare -F | sed "s/declare -f //" | sort'
# diff that against the same run from a detached worktree at HEAD
```

Both gave an identical set (48 and 28 functions). Re-run it after **each**
carve, not just at the end.

### Extracting embedded _data_ is free; embedded _code_ is not

`update_android_hosts.sh` was 870 lines, of which 247 were a heredoc of hosts
entries. Moving that to `data/android_guardian_blocklist.hosts` and `cat`-ing
it cleared the file in one step, and a data file **attracts no linter**.

Verify with a hash of the heredoc body against the extracted file:

```bash
git show HEAD:<script> | awk "/<<'EOF'/,/^EOF$/" | sed '1d;$d' | md5sum
md5sum < <the extracted file>
```

Contrast the next section: extracting an embedded _program_ is the same shape
but a very different cost.

### Extracting an embedded program pulls it into the Python gate

`install_plagiarism_tools.sh` (534) is mostly two heredocs emitting a 224-line
and a 90-line Python program. Extracting them to real files under
`plagiarism/` gets all three under the cap in one move and is what the shell
rules ask for — but those files then face `ruff select = ["ALL"]`, `pylint`
and `mypy`, and they arrived with **22 violations**. Fixing those means
rewriting a plagiarism checker, and it changes code that gets _installed_.

So: extracting an embedded program is the right shape, but budget it as a
**Python cleanup task, not a line-count split**. Reverted for now.

### When to give up on a seam

`clean_audio.sh` was reverted. Two probe-result globals were read by functions
destined for different libs; renaming them to satisfy SC2154 just moved the
warning to a third. **A split that needs a suppression, or that would thread
globals through three files, is a refactor — not a line-count split.** Revert
it, leave the file over the cap, and say so. It is cheaper than a silent
behaviour change in a script you are not allowed to run.

- Prefer files that **nothing** references first — pure lint risk.
- Watch **jscpd** on the first multi-lib commit: repeated `set -euo pipefail` +
  source-guard headers across several new libs is exactly what pushes
  duplication toward the 2% threshold, and it only fires on the real
  `git commit`.
