#!/usr/bin/env bash
# Tests for lib/arch_perf_fixes.sh: fix_journal, fix_nm_wait_online and
# fix_media_organizer.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=arch_perf_harness.sh
. "${SCRIPT_DIR}/arch_perf_harness.sh"

# shellcheck source=../arch_perf_fixes.sh
. "${FIXES_DIR}/lib/arch_perf_fixes.sh"

dropin="${JOURNALD_CONF_DIR}/size-limit.conf"
unit="${SYSTEMD_UNIT_DIR}/media-organizer.service"

# --- fix_journal ------------------------------------------------------------

# A multi-gigabyte journal is vacuumed AND capped. This only fires because the
# size regex now tolerates journalctl's spaceless "4.2G" output; with the old
# pattern the vacuum was unreachable.
arch_reset
_t_stub journalctl 'echo "Archived and active journals take up 4.2G in the file system."'
fix_journal
_t_contains "$(_t_calls)" "journalctl --vacuum-size=300M" \
	"fix_journal: vacuums a multi-gigabyte journal"
_t_contains "$(cat "$dropin" 2>/dev/null)" "SystemMaxUse=300M" \
	"fix_journal: writes the permanent size cap"
_t_contains "$(_t_calls)" "systemctl restart systemd-journald" \
	"fix_journal: restarts journald after writing the cap"

# A journal already under a gigabyte is left alone, but still capped.
arch_reset
_t_stub journalctl 'echo "Archived and active journals take up 240.0M in the file system."'
out="$(fix_journal 2>&1)"
_t_contains "$out" "already under 1GiB" \
	"fix_journal: reports a journal that is already small enough"
_t_lacks "$(_t_calls)" "journalctl --vacuum-size" \
	"fix_journal: does not vacuum a journal measured in megabytes"
_t_contains "$(cat "$dropin" 2>/dev/null)" "SystemMaxUse=300M" \
	"fix_journal: still writes the cap for a small journal"

# The cap already exists: it is not rewritten and journald is not restarted.
arch_reset
_t_stub journalctl 'echo "120.0M"'
printf '[Journal]\nSystemMaxUse=300M\n' >"$dropin"
out="$(fix_journal 2>&1)"
_t_contains "$out" "size cap already configured" \
	"fix_journal: reports an already-configured size cap"
_t_lacks "$(_t_calls)" "systemctl restart systemd-journald" \
	"fix_journal: does not restart journald when the cap already exists"

# --- fix_nm_wait_online -----------------------------------------------------

arch_reset
_t_stub systemctl 'exit 0'
fix_nm_wait_online
_t_contains "$(_t_calls)" "systemctl disable NetworkManager-wait-online.service" \
	"fix_nm_wait_online: disables the wait-online unit when it is enabled"

arch_reset
_t_stub systemctl 'exit 1'
out="$(fix_nm_wait_online 2>&1)"
_t_contains "$out" "already disabled" \
	"fix_nm_wait_online: reports a unit that is already disabled"
_t_lacks "$(_t_calls)" "systemctl disable" \
	"fix_nm_wait_online: does not re-disable an already-disabled unit"

# --- fix_media_organizer ----------------------------------------------------

# The organizer script is nowhere to be found: the fix is skipped. Both
# candidate paths are absolute; the first is overridden into the tmpdir and
# the second is a real home path that does not exist on this machine.
arch_reset
if [[ -f /home/kuhy/linux-configuration/utils/organize_downloads.sh ]]; then
	_t_pass "fix_media_organizer: SKIP not-found case (the second candidate exists here)"
else
	out="$(fix_media_organizer 2>&1)"
	_t_contains "$out" "not found — skipping" \
		"fix_media_organizer: skips when no organize_downloads.sh exists"
	_t_lacks "$(_t_calls)" "systemctl daemon-reload" \
		"fix_media_organizer: writes no unit when the script is missing"
fi

# The script exists: the unit is written, reloaded and enabled.
arch_reset
printf '#!/bin/bash\necho organize\n' >"$ORGANIZE_SCRIPT_CANDIDATES"
out="$(SUDO_USER="kuhy" fix_media_organizer 2>&1)"
unit_text="$(cat "$unit" 2>/dev/null)"
_t_contains "$unit_text" "Description=Media File Organizer" \
	"fix_media_organizer: writes the unit description"
_t_contains "$unit_text" "User=kuhy" \
	"fix_media_organizer: runs the unit as the invoking user, not root"
_t_contains "$unit_text" "ExecStart=${ORGANIZE_SCRIPT_CANDIDATES}" \
	"fix_media_organizer: points ExecStart at the script it found"
_t_contains "$(_t_calls)" "systemctl daemon-reload" \
	"fix_media_organizer: reloads systemd after writing the unit"
_t_contains "$(_t_calls)" "systemctl enable media-organizer.service" \
	"fix_media_organizer: enables the unit"
_t_contains "$(_t_calls)" "systemctl stop media-organizer.service" \
	"fix_media_organizer: stops the old unit before replacing it"

# An already-correct unit is left alone.
arch_reset
printf '#!/bin/bash\n' >"$ORGANIZE_SCRIPT_CANDIDATES"
printf 'User=kuhy\nExecStart=%s\n' "$ORGANIZE_SCRIPT_CANDIDATES" >"$unit"
out="$(SUDO_USER="kuhy" fix_media_organizer 2>&1)"
_t_contains "$out" "already correctly configured" \
	"fix_media_organizer: skips a unit that is already correct"
_t_eq "" "$(_t_calls)" \
	"fix_media_organizer: runs no systemctl command when the unit is correct"

# A unit that exists but names the WRONG user is rewritten.
arch_reset
printf '#!/bin/bash\n' >"$ORGANIZE_SCRIPT_CANDIDATES"
printf 'User=someoneelse\nExecStart=%s\n' "$ORGANIZE_SCRIPT_CANDIDATES" >"$unit"
out="$(SUDO_USER="kuhy" fix_media_organizer 2>&1)"
_t_contains "$(cat "$unit")" "User=kuhy" \
	"fix_media_organizer: rewrites a unit that names the wrong user"

echo
echo "arch_perf_fixes: ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
