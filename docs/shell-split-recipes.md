# Shell split recipes for the 250-line cap

Split out of `refactor_claude_todo_resume.md` (which is itself capped).
Applies to `linux_configuration/` and `phone_focus_mode/`.

`linux_configuration` and `phone_focus_mode` have **no test suite and no
coverage gate**, so none of the above transfers. Decision 6 governs:
`bash -n` + `shellcheck` + `systemctl cat` path checks, and **never execute an
enforcement script that mutates the live system or the phone.**

- After each split, `bash -n` and `shellcheck` the entry script _and_ every new
  lib. Neither catches a lib that is never sourced.
- So also: for each new `lib/*.sh`, grep the entry script for the `source`/`.`
  line naming it, and confirm the path resolves from where the script actually
  runs (`${BASH_SOURCE[0]%/*}` or absolute — never a bare relative `./lib/`).
- **Two live units point at repo paths** and break if a file moves or is
  renamed. `systemctl cat` them after touching either:
  - `/etc/systemd/system/dns-blocklist-refresh.service` →
    `scripts/single_use/features/setup_dns_blocker.sh refresh`
  - `/etc/systemd/system/media-organizer.service` →
    `scripts/single_use/utils/organize_downloads.sh`

  Every other in-repo unit references an installed copy under `/usr/local/`,
  so those are only at risk if the _installer_ is what you split.

- Prefer files that **nothing** references first — pure lint risk.
- Watch **jscpd** on the first multi-lib commit: repeated `set -euo pipefail` +
  source-guard headers across several new libs is exactly what pushes
  duplication toward the 2% threshold, and it only fires on the real
  `git commit`.
