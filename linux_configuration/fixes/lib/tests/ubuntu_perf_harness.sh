#!/usr/bin/env bash
# lib/tests/ubuntu_perf_harness.sh — shared setup for the ubuntu performance
# lib tests (ubuntu_perf_more.sh, ubuntu_perf_fixes.sh).
#
# Sourced, not executed. Builds on lib_test_core.sh and adds what these libs
# read from their entry script, fix_ubuntu_performance.sh:
#
#   * UNDO_SCRIPT, pointed into the throwaway tmpdir, and add_undo which
#     appends to it -- both live in the entry script, not in any lib;
#   * the real log_*/has_cmd helpers, via lib/common.sh.
#
# JOURNALD_CONF_DIR and UNDO_DIR are the overrides ubuntu_perf_more.sh exposes
# so its two absolute write targets (/etc/systemd/journald.conf.d and /root)
# stay out of reach. run_all.sh runs UN-jailed in ci_mirror.sh and in CI, so a
# bind mount would protect only the coverage run.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_ROOT="$(cd "${FIXES_DIR}/../.." && pwd)"

# shellcheck source=lib_test_core.sh
. "${SCRIPT_DIR}/lib_test_core.sh"

# shellcheck source=../../../lib/common.sh
. "${REPO_ROOT}/linux_configuration/lib/common.sh"

# --- globals and helpers owned by fix_ubuntu_performance.sh -----------------

# Read by the libs under test, never by this harness, so static analysis
# cannot see the use; export makes the intent explicit.
export UNDO_SCRIPT="${TEST_TMPDIR}/undo.sh"
export JOURNALD_CONF_DIR="${TEST_TMPDIR}/journald.conf.d"
export UNDO_DIR="${TEST_TMPDIR}/undo_dir"
# The seams ubuntu_perf_fixes.sh exposes for its three write targets.
export SYSCTL_DROPIN_DIR="${TEST_TMPDIR}/sysctl.d"
export SYSTEMD_UNIT_DIR="${TEST_TMPDIR}/systemd_units"
export EARLYOOM_CONF_FILE="${TEST_TMPDIR}/earlyoom"

# Verbatim from fix_ubuntu_performance.sh.
add_undo() {
	echo "$1" >>"$UNDO_SCRIPT"
}

_ubuntu_default_stubs() {
	local tool
	for tool in systemctl journalctl snap apt-get update-grub sysctl \
		swapoff swapon nvidia-smi nvidia-persistenced dpkg; do
		_t_stub "$tool" 'exit 0'
	done
}

# ubuntu_reset — start a test group from "nothing has happened yet".
ubuntu_reset() {
	_t_reset_calls
	rm -rf "${JOURNALD_CONF_DIR}" "${UNDO_DIR}" "${SYSCTL_DROPIN_DIR}" \
		"${SYSTEMD_UNIT_DIR}"
	mkdir -p "${JOURNALD_CONF_DIR}" "${UNDO_DIR}" "${SYSCTL_DROPIN_DIR}" \
		"${SYSTEMD_UNIT_DIR}"
	rm -f "${EARLYOOM_CONF_FILE}" "${EARLYOOM_CONF_FILE}.bak"
	: >"$UNDO_SCRIPT"
	_t_full_path
	_ubuntu_default_stubs
}

# _t_unit FILE — the contents of a systemd unit written this round.
_t_unit() {
	cat "${SYSTEMD_UNIT_DIR}/$1" 2>/dev/null || true
}

# _t_sysctl_file — the contents of the sysctl drop-in written this round.
_t_sysctl_file() {
	cat "${SYSCTL_DROPIN_DIR}/99-performance-tuning.conf" 2>/dev/null || true
}

# _t_undo — the undo script's contents this round.
_t_undo() {
	cat "$UNDO_SCRIPT" 2>/dev/null || true
}

ubuntu_reset
