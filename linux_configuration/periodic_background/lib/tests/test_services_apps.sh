#!/usr/bin/env bash
# Tests for lib/services_apps.sh — the messaging-app launch wrappers and the
# LeechBlock browser extension check.
#
# check_compulsive_blocker has a three-way branch per app: a wrapper is
# installed (.orig backup present), the app is installed but unwrapped, or the
# app is absent entirely. `command -v` decides the second vs third case, so the
# tests create and remove fake executables on PATH via present_command /
# absent_command rather than shimming `command`, which is a bash builtin.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"
# shellcheck source=../services_apps.sh
. "${SCRIPT_DIR}/../services_apps.sh"

_t_called_in() { # <haystack> <needle> <what>
	if [[ "$1" == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (missing '$2')"
	fi
}

_t_not_in() { # <haystack> <needle> <what>
	if [[ "$1" == *"$2"* ]]; then
		_t_fail "$3 (unexpected '$2')"
	else
		_t_pass "$3"
	fi
}

# What install_wrapper leaves on /usr/bin/<app>: the marker the repair greps.
wrapper_marker() { # <relative-path>
	sysfile "$1"
	printf 'exec /usr/local/bin/block-compulsive-opening.sh wrapper x\n' >"${SYSROOT_DIR}/$1"
}

# Register <relative-path> as owned by <pkg> in the fixture pacman db.
own_path() { # <pkg> <relative-path>
	sysfile "var/lib/pacman/local/$1-1-1/files"
	printf '%%FILES%%\n%s\n' "$2" >"${SYSROOT_DIR}/var/lib/pacman/local/$1-1-1/files"
}

sys_state() { # <relative-path> -> present|absent
	if [[ -e "${SYSROOT_DIR}/$1" ]]; then echo present; else echo absent; fi
}

TEST_USER="${SUDO_USER:-$USER}"

echo "== check_compulsive_blocker: no target apps present =="
reset_state
absent_command beeper signal-desktop discord
sysfile usr/local/bin/block-compulsive-opening.sh
check_compulsive_blocker >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "No target apps" "an absent app set is reported as not applicable"
_t_eq "ok" "$(get_service_status "compulsive_blocker")" "with the blocker installed and no apps, status is ok"

echo "== check_compulsive_blocker: blocker script missing is an error =="
reset_state
absent_command beeper signal-desktop discord
make_installer "$COMPULSIVE_BLOCK_SCRIPT"
check_compulsive_blocker >/dev/null
_t_called 'ran block_compulsive_opening.sh install' "a missing blocker script runs the installer with 'install'"
_t_eq "1" "$FIXES_APPLIED" "the fix is counted"

echo "== check_compulsive_blocker: an installed but unwrapped app warns =="
reset_state
sysfile usr/local/bin/block-compulsive-opening.sh
present_command discord
absent_command beeper signal-desktop
check_compulsive_blocker >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "discord is installed but wrapper not applied" "the unwrapped app is named"
_t_eq "warning" "$(get_service_status "compulsive_blocker")" "an unwrapped app is a warning, not an error"
_t_not_called 'ran block_compulsive_opening' "a warning does not trigger the installer"

echo "== check_compulsive_blocker: a wrapped app is accepted =="
reset_state
sysfile usr/local/bin/block-compulsive-opening.sh
present_command discord
absent_command beeper signal-desktop
sysfile usr/bin/discord.orig
wrapper_marker usr/bin/discord
own_path discord usr/bin/discord
check_compulsive_blocker >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "discord wrapper installed" "a backed-up original counts as wrapped"
_t_eq "ok" "$(get_service_status "compulsive_blocker")" "a wrapped app leaves status ok"
_t_eq "0" "$FIXES_APPLIED" "an owned wrap is not touched"

echo "== check_compulsive_blocker: a .orig left by a package removal is stale =="
reset_state
sysfile usr/local/bin/block-compulsive-opening.sh
absent_command beeper signal-desktop discord
# pacman removed /usr/bin/discord (our wrapper) but not the backup; another
# package in the db proves the db is readable, so "unowned" is definite.
sysfile usr/bin/discord.orig
own_path signal-desktop usr/bin/signal-desktop
check_compulsive_blocker >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "stale discord.orig left after package removal" "the stale backup is named"
_t_not_in "$(cat "${TEST_TMPDIR}/out.txt")" "discord wrapper installed" "a stale backup is not reported as a wrapper"
_t_eq "warning" "$(get_service_status "compulsive_blocker")" "a stale backup is a warning"
_t_eq "absent" "$(sys_state usr/bin/discord.orig)" "the repair deletes the stale .orig"
_t_eq "1" "$FIXES_APPLIED" "the removal is counted as a fix"
_t_not_called 'ran block_compulsive_opening' "a stale backup does not rerun the installer"

echo "== check_compulsive_blocker: a stale .orig takes its dangling wrapper with it =="
reset_state
sysfile usr/local/bin/block-compulsive-opening.sh
absent_command beeper signal-desktop discord
sysfile usr/bin/discord.orig
wrapper_marker usr/bin/discord
own_path signal-desktop usr/bin/signal-desktop
check_compulsive_blocker >/dev/null
_t_eq "absent" "$(sys_state usr/bin/discord)" "our wrapper on an unowned path is deleted"
_t_eq "absent" "$(sys_state usr/bin/discord.orig)" "and so is its .orig"

echo "== check_compulsive_blocker: --status reports a stale .orig but keeps it =="
reset_state
sysfile usr/local/bin/block-compulsive-opening.sh
absent_command beeper signal-desktop discord
sysfile usr/bin/discord.orig
own_path signal-desktop usr/bin/signal-desktop
STATUS_ONLY=1
check_compulsive_blocker >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "stale discord.orig" "--status still names the stale backup"
_t_eq "present" "$(sys_state usr/bin/discord.orig)" "--status deletes nothing"

echo "== check_compulsive_blocker: --dry-run reports a stale .orig but keeps it =="
reset_state
sysfile usr/local/bin/block-compulsive-opening.sh
absent_command beeper signal-desktop discord
sysfile usr/bin/discord.orig
own_path signal-desktop usr/bin/signal-desktop
DRY_RUN=1
check_compulsive_blocker >/dev/null
_t_eq "present" "$(sys_state usr/bin/discord.orig)" "--dry-run deletes nothing"

echo "== check_compulsive_blocker: an unreadable pacman db never prunes =="
reset_state
sysfile usr/local/bin/block-compulsive-opening.sh
present_command discord
absent_command beeper signal-desktop
sysfile usr/bin/discord.orig
check_compulsive_blocker >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "discord wrapper installed" "no db: the backup still counts as a wrapper"
_t_eq "present" "$(sys_state usr/bin/discord.orig)" "no db: the .orig is kept"

echo "== check_compulsive_blocker: a symlinked wrapper without .orig is skipped =="
reset_state
sysfile usr/local/bin/block-compulsive-opening.sh
present_command discord
absent_command beeper signal-desktop
# A symlink at /usr/bin/<app> with no .orig beside it takes the outer branch but
# not the inner one -- neither "wrapped" nor "unwrapped", so nothing is said.
ln -sf "${SERVICES_ROOT}/usr/local/bin/block-compulsive-opening.sh" "${SERVICES_ROOT}/usr/bin/discord"
check_compulsive_blocker >/dev/null
_t_eq "ok" "$(get_service_status "compulsive_blocker")" "a symlink without .orig leaves status ok"

echo "== check_compulsive_blocker: an unwrapped app plus a missing blocker is an error =="
reset_state
make_installer "$COMPULSIVE_BLOCK_SCRIPT"
present_command discord
absent_command beeper signal-desktop
check_compulsive_blocker >/dev/null
# The error from the missing blocker must not be downgraded by the app warning.
_t_eq "error" "$(get_service_status "compulsive_blocker")" "an error is not downgraded by a later warning"
_t_called 'ran block_compulsive_opening' "the installer still runs"

echo "== check_compulsive_blocker: --status and a missing installer =="
reset_state
absent_command beeper signal-desktop discord
make_installer "$COMPULSIVE_BLOCK_SCRIPT"
STATUS_ONLY=1
check_compulsive_blocker >/dev/null
_t_not_called 'ran block_compulsive_opening' "--status never installs"

reset_state
absent_command beeper signal-desktop discord
rm -f "$COMPULSIVE_BLOCK_SCRIPT"
check_compulsive_blocker >/dev/null
_t_eq "1" "${#MISSING_SCRIPTS[@]}" "a missing installer is recorded"

echo "== check_leechblock: installed with a desktop entry =="
reset_state
sysfile "home/${TEST_USER}/.local/share/leechblockng/manifest.json"
sysfile "home/${TEST_USER}/.local/share/applications/thorium-leechblock.desktop"
check_leechblock >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "LeechBlock desktop entry found" "the desktop entry is found"
_t_eq "ok" "$(get_service_status "leechblock")" "a full install records ok"

echo "== check_leechblock: the capitalised glob is matched too =="
reset_state
sysfile "home/${TEST_USER}/.local/share/leechblockng/manifest.json"
sysfile "home/${TEST_USER}/.local/share/applications/LeechBlock-thorium.desktop"
check_leechblock >/dev/null
_t_eq "ok" "$(get_service_status "leechblock")" "a LeechBlock-cased entry also counts"

echo "== check_leechblock: installed but no desktop entry warns =="
reset_state
sysfile "home/${TEST_USER}/.local/share/leechblockng/manifest.json"
mkdir -p "${SERVICES_ROOT}/home/${TEST_USER}/.local/share/applications"
check_leechblock >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "No LeechBlock desktop entries found" "the missing entry is reported"
_t_eq "warning" "$(get_service_status "leechblock")" "a missing desktop entry is only a warning"
_t_not_called 'ran install_leechblock' "a warning does not trigger the installer"

echo "== check_leechblock: not installed at all runs the installer as the user =="
reset_state
make_installer "$LEECHBLOCK_SCRIPT"
check_leechblock >/dev/null
_t_called "sudo -u ${TEST_USER} bash" "the installer runs as the invoking user, not root"
_t_eq "1" "$FIXES_APPLIED" "the fix is counted"

echo "== check_leechblock: --status and a missing installer =="
reset_state
make_installer "$LEECHBLOCK_SCRIPT"
STATUS_ONLY=1
check_leechblock >/dev/null
_t_not_called 'sudo -u' "--status never installs"

reset_state
rm -f "$LEECHBLOCK_SCRIPT"
check_leechblock >/dev/null
_t_eq "1" "${#MISSING_SCRIPTS[@]}" "a missing leechblock installer is recorded"

_t_summary
