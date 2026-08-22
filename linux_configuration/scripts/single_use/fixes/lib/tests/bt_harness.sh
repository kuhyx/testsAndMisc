#!/usr/bin/env bash
# lib/tests/bt_harness.sh — shared setup for the fix_bluetooth.sh lib tests
# (bt_report.sh, bt_adapter.sh, bt_pairing.sh, bt_audio.sh).
#
# Sourced, not executed. Builds on lib_test_core.sh (tmpdir, $FAKE_BIN on
# PATH, the _t_* assertions) and adds the three things the bt libs need:
#
#   1. the real log_*/has_cmd helpers, by sourcing scripts/lib/common.sh --
#      it is inert at source time (a load guard, two exports and three
#      sub-sources), so the libs get the exact helpers they see in production
#      rather than reimplementations that could drift;
#   2. _btctl and apply_fix, which live in fix_bluetooth.sh itself rather
#      than in any lib. Redefined here verbatim from the entry script so the
#      libs resolve them exactly as they do when sourced for real -- the same
#      approach pacman_hook_stall_harness.sh takes with log_size;
#   3. stubs for the external tools the bt libs shell out to.
#
# Every tool these libs call (dmesg, wget, lsusb, modprobe, pactl, usbreset,
# bluetoothctl, rfkill...) genuinely exists on an Arch desktop, so a
# PREPENDED stub dir cannot exercise a "not installed" branch. _t_only_path
# below drops PATH to $FAKE_BIN alone for exactly those cases.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_ROOT="$(cd "${FIXES_DIR}/../../../.." && pwd)"

# shellcheck source=lib_test_core.sh
. "${SCRIPT_DIR}/lib_test_core.sh"

# Real logging/has_cmd/ask_yes_no helpers, as the entry script gets them.
# shellcheck source=../../../../lib/common.sh
. "${REPO_ROOT}/linux_configuration/scripts/lib/common.sh"

# --- pieces that live in fix_bluetooth.sh, not in a lib ---------------------

# Verbatim from fix_bluetooth.sh: bluetoothctl returns empty when driven with
# `-- <cmd>`, so the real script pipes the command in on stdin.
_btctl() {
	echo "$*" | bluetoothctl 2>/dev/null
}

FIXES_APPLIED=0
FIXES_SKIPPED=0
INTERACTIVE_MODE="false"

# Verbatim from fix_bluetooth.sh. The libs call apply_fix for every mutating
# action, so it is the seam most assertions read: $DEV/fixes records the
# description of each fix that actually ran.
apply_fix() {
	local description="$1"
	shift

	echo ""
	log_info "$description"
	printf '%s\n' "$description" >>"${DEV}/fixes"

	if [[ $INTERACTIVE_MODE == "true" ]]; then
		if ! ask_yes_no "  Apply this fix?"; then
			log_warn "Skipped."
			((FIXES_SKIPPED++)) || true
			return 0
		fi
	fi

	if "$@"; then
		log_ok "Done."
		((FIXES_APPLIED++)) || true
	else
		log_error "Failed (non-fatal, continuing)."
	fi
}

# --- external tool stubs ----------------------------------------------------

# Default every tool the bt libs touch to a quiet success. Individual tests
# re-stub the one tool they care about via _t_stub.
_bt_default_stubs() {
	local tool
	for tool in dmesg wget curl lsusb modprobe dbus-send pactl wpctl \
		bluetoothctl rfkill lsmod usbreset systemctl journalctl sudo id \
		udevadm; do
		_t_stub "$tool" 'exit 0'
	done
	# `id -u <user>` feeds _run_as_user's XDG_RUNTIME_DIR path.
	_t_stub id 'echo 1000'
	# sudo -u <user> VAR=... <cmd> ... -- drop sudo's own arguments and exec
	# the wrapped command, so _run_as_user reaches the stubbed tool. Held in
	# a quoted heredoc: every $ in here belongs to the stub, not to us.
	local sudo_body
	sudo_body="$(
		cat <<'SUDO_BODY'
shift 2 2>/dev/null || true
while [[ "${1:-}" == *=* ]]; do shift; done
[[ $# -gt 0 ]] || exit 0
exec "$@"
SUDO_BODY
	)"
	_t_stub sudo "$sudo_body"
}

# _t_hide TOOL... — make TOOL genuinely unfindable, so has_cmd/command -v
# report it absent.
#
# A prepended stub dir cannot do this: every tool these libs probe for
# (usbreset, pactl, wpctl) really exists on an Arch desktop, so PATH has to
# stop resolving it. Dropping PATH to $FAKE_BIN alone is NOT the answer
# either -- that also hides grep, head, awk and sort, which these libs use
# on the very branch under test, turning a "not installed" case into a
# cascade of "command not found".
#
# Instead a shim dir is built containing a symlink to every real executable
# on PATH EXCEPT the hidden ones, and PATH is pointed at it.
_t_hide() {
	local hide_dir="${TEST_TMPDIR}/hidden_path"
	rm -rf "$hide_dir"
	mkdir -p "$hide_dir"

	local -A hidden=()
	local tool
	for tool in "$@"; do
		hidden["$tool"]=1
	done

	local dir entry name
	local IFS=':'
	for dir in ${LIB_TEST_ORIG_PATH}; do
		[[ -d "$dir" ]] || continue
		for entry in "$dir"/*; do
			name="${entry##*/}"
			[[ -n "${hidden[$name]:-}" ]] && continue
			[[ -x "$entry" && ! -d "$entry" ]] || continue
			[[ -e "${hide_dir}/${name}" ]] && continue
			ln -s "$entry" "${hide_dir}/${name}" 2>/dev/null || true
		done
	done

	PATH="${FAKE_BIN}:${hide_dir}"
	hash -r
}

# _t_full_path — restore the prepended-stub PATH set up by lib_test_core.sh.
_t_full_path() {
	PATH="${FAKE_BIN}:${LIB_TEST_ORIG_PATH}"
	hash -r
}

export LIB_TEST_ORIG_PATH="${PATH#"${FAKE_BIN}:"}"

# bt_reset — start a test group from "nothing has happened yet".
bt_reset() {
	_t_reset_calls
	: >"${DEV}/fixes"
	FIXES_APPLIED=0
	FIXES_SKIPPED=0
	INTERACTIVE_MODE="false"
	TARGET_MAC="F8:5C:7E:0E:50:6B"
	_t_full_path
	_bt_default_stubs
}

# _t_fixes — the descriptions of the fixes apply_fix ran this round.
_t_fixes() {
	cat "${DEV}/fixes" 2>/dev/null || true
}

# TARGET_MAC is read by the bt libs under test, never by this harness, so
# static analysis cannot see the use. export makes the intent explicit.
export TARGET_MAC="F8:5C:7E:0E:50:6B"
bt_reset
