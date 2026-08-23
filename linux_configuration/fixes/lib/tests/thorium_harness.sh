#!/usr/bin/env bash
# lib/tests/thorium_harness.sh — shared setup for the Thorium repair lib
# tests (thorium_repairs.sh).
#
# Sourced, not executed. Builds on lib_test_core.sh and adds what the lib
# reads from its entry script, fix_thorium.sh:
#
#   * THORIUM_CONFIG_DIR, pointed into the throwaway tmpdir, plus the
#     DRY_RUN / AGGRESSIVE / TEST_AFTER flags and BACKUP_SUFFIX;
#   * backup_if_exists and remove_if_exists, redefined verbatim from the
#     entry script -- they live there rather than in any lib, the same
#     arrangement arch_desktop_harness.sh handles with apply_tweak;
#   * the colour variables the lib echoes;
#   * the real log_*/has_cmd helpers, via lib/common.sh.
#
# The lib takes EVERY path it touches from $THORIUM_CONFIG_DIR, so pointing
# that one variable at the tmpdir is enough to confine it -- no production
# seam had to be added, unlike the arch desktop family.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_ROOT="$(cd "${FIXES_DIR}/../.." && pwd)"

# shellcheck source=lib_test_core.sh
. "${SCRIPT_DIR}/lib_test_core.sh"

# shellcheck source=../../../lib/common.sh
. "${REPO_ROOT}/linux_configuration/lib/common.sh"

# --- globals and helpers owned by fix_thorium.sh ----------------------------

# Read by the lib under test, never by this harness, so static analysis
# cannot see the use; export makes the intent explicit.
export THORIUM_CONFIG_DIR="${TEST_TMPDIR}/thorium"
export BACKUP_SUFFIX=".bak.20260822_120000"
export DRY_RUN=false
export AGGRESSIVE=false
export TEST_AFTER=false
# test_thorium sleeps to see whether the browser stayed up. Four real
# seconds per case dominated this file's runtime (17s of a 110s suite);
# the stub browser sleeps far longer than this, so the check is unchanged.
export THORIUM_STARTUP_WAIT=0.2

# The lib echoes these directly; fix_thorium.sh defines them for a terminal.
# Empty here so assertions match on text rather than escape sequences.
export RED=''
export GREEN=''
export YELLOW=''
export NC=''

# Verbatim from fix_thorium.sh.
backup_if_exists() {
	local path="$1"
	local name
	name=$(basename "$path")

	if [[ -e $path ]]; then
		local backup_path="${path}${BACKUP_SUFFIX}"
		if [[ $DRY_RUN == true ]]; then
			echo "  [dry-run] Would backup: $name"
		else
			mv "$path" "$backup_path"
			log_ok "Backed up: $name -> $(basename "$backup_path")"
		fi
		return 0
	fi
	return 1
}

# Verbatim from fix_thorium.sh.
remove_if_exists() {
	local path="$1"
	local name
	name=$(basename "$path")

	if [[ -e $path ]]; then
		if [[ $DRY_RUN == true ]]; then
			echo "  [dry-run] Would remove: $name"
		else
			rm -rf "$path"
			log_ok "Removed: $name"
		fi
		return 0
	fi
	return 1
}

_thorium_default_stubs() {
	local tool
	for tool in python3 sqlite3 thorium-browser; do
		_t_stub "$tool" 'exit 0'
	done
}

# thorium_reset — start a test group from "nothing has happened yet".
thorium_reset() {
	_t_reset_calls
	DRY_RUN=false
	AGGRESSIVE=false
	TEST_AFTER=false
	export DRY_RUN AGGRESSIVE TEST_AFTER
	rm -rf "${THORIUM_CONFIG_DIR}"
	mkdir -p "${THORIUM_CONFIG_DIR}/Default"
	_t_full_path
	_thorium_default_stubs
}

# _t_profile PATH... — create files inside the Thorium profile.
_t_profile() {
	local rel
	for rel in "$@"; do
		mkdir -p "$(dirname "${THORIUM_CONFIG_DIR}/${rel}")"
		printf 'x\n' >"${THORIUM_CONFIG_DIR}/${rel}"
	done
}

# _t_exists REL — "yes"/"no" for a path inside the profile, for assertions
# that read better than a bare test.
_t_exists() {
	if [[ -e "${THORIUM_CONFIG_DIR}/$1" ]]; then
		printf 'yes\n'
	else
		printf 'no\n'
	fi
}

thorium_reset
