#!/usr/bin/env bash
# lib/tests/arch_perf_harness.sh — shared setup for the arch performance lib
# tests (arch_perf_report.sh, arch_perf_probes.sh).
#
# Sourced, not executed. Builds on lib_test_core.sh and adds the pieces these
# libs read from their entry script, diagnose_arch_performance.sh:
#
#   * REPORT_FILE, FINDINGS, ACTIONS and the APPLY_SAFE_FIXES flag;
#   * add_finding, add_action and run_and_log, redefined verbatim from the
#     entry script -- they live there rather than in any lib, the same
#     arrangement pacman_hook_stall_harness.sh handles with log_size;
#   * the real log_*/has_cmd helpers, via scripts/lib/common.sh.
#
# REPORT_FILE points into the throwaway tmpdir, so the probes' report writes
# never leave the sandbox.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_ROOT="$(cd "${FIXES_DIR}/../../../.." && pwd)"

# shellcheck source=lib_test_core.sh
. "${SCRIPT_DIR}/lib_test_core.sh"

# shellcheck source=../../../../lib/common.sh
. "${REPO_ROOT}/linux_configuration/scripts/lib/common.sh"

# --- globals and helpers owned by diagnose_arch_performance.sh --------------

# These four are read by the libs under test, never by this harness, so
# static analysis cannot see the use; export makes the intent explicit.
export REPORT_FILE="${TEST_TMPDIR}/report.log"
export APPLY_SAFE_FIXES="false"
export INSTALL_TOOLS="false"
declare -a FINDINGS=()
declare -a ACTIONS=()

# Verbatim from diagnose_arch_performance.sh.
add_finding() {
	FINDINGS+=("$1")
	log_warn "$1"
}

add_action() {
	ACTIONS+=("$1")
	log_info "$1"
}

run_and_log() {
	local header="$1"
	shift
	{
		echo
		echo "=== $header ==="
		"$@" 2>&1 || true
	} >>"$REPORT_FILE"
}

# --- external tool stubs ----------------------------------------------------

_arch_default_stubs() {
	local tool
	for tool in nvidia-smi lspci journalctl systemctl sysctl lsblk sensors \
		free uptime ps top swapon findmnt pacman systemd-analyze; do
		_t_stub "$tool" 'exit 0'
	done
}

# arch_reset — start a test group from "nothing has happened yet".
arch_reset() {
	_t_reset_calls
	FINDINGS=()
	ACTIONS=()
	APPLY_SAFE_FIXES="false"
	INSTALL_TOOLS="false"
	export APPLY_SAFE_FIXES INSTALL_TOOLS
	: >"$REPORT_FILE"
	_t_full_path
	_arch_default_stubs
}

# _t_report — the report file's contents this round.
_t_report() {
	cat "$REPORT_FILE" 2>/dev/null || true
}

# _t_findings / _t_actions — the recorded findings and actions, one per line.
_t_findings() {
	printf '%s\n' "${FINDINGS[@]:-}"
}

_t_actions() {
	printf '%s\n' "${ACTIONS[@]:-}"
}

arch_reset
