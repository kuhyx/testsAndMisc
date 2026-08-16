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
- So the real check is a **stubbed run**: copy the entry script and its libs to
  a `mktemp -d`, `sed` the final `main` invocation into a `declare -F` probe,
  and run it. That executes the `source` lines and nothing else. This caught
  the bug below; no static check did.

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

Follow `scripts/lib/common.sh`: **shebang present, file executable.** The two
obvious-looking alternatives each fail a hook:

- No shebang → `shellcheck` SC2148 ("target shell unknown").
- Shebang but not executable → `check-shebang-scripts-are-executable`.

So: `#!/bin/bash`, `chmod +x`, and **no `set -euo pipefail`** — a sourced lib
inherits the caller's strict mode, and redeclaring it is duplicated
boilerplate that feeds jscpd. Say so in the lib's header comment.

- **Two live units point at repo paths** and break if a file moves or is
  renamed. `systemctl cat` them after touching either:
  - `/etc/systemd/system/dns-blocklist-refresh.service` →
    `scripts/single_use/features/setup_dns_blocker.sh refresh`
  - `/etc/systemd/system/media-organizer.service` →
    `scripts/single_use/utils/organize_downloads.sh`

  Every other in-repo unit references an installed copy under `/usr/local/`,
  so those are only at risk if the _installer_ is what you split.

## Which scripts escape the repo (enumerated 2026-08-16)

A split is only safe if the file still resolves its libs from wherever it
actually runs. Two ways a script leaves the repo, both silent when broken:

- **Copied out** — only three, all under
  `scripts/periodic_background/hosts/guard/pacman-hooks/`, installed to
  `/usr/local/share/hosts-guard/` by `hosts/guard/install_pacman_hooks.sh`.
  Splitting any of those three means the installer must copy the new libs too,
  **in the same commit** — the same trap as `phone_focus_mode/deploy.sh`.
- **Symlinked in** — exactly one: `/usr/local/bin/start-player2` →
  `scripts/gaming/start-player2.sh`. `${BASH_SOURCE[0]%/*}` resolves to
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
