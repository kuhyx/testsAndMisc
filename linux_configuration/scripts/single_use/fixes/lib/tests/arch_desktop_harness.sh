#!/usr/bin/env bash
# lib/tests/arch_desktop_harness.sh — shared setup for the arch desktop
# optimization lib tests (arch_sysctl.sh, arch_cpu.sh, arch_hardware.sh).
#
# Sourced, not executed. Builds on lib_test_core.sh and adds the pieces these
# three libs read from their entry script, optimize_arch_desktop.sh:
#
#   * DRY_RUN, AGGRESSIVE, TWEAKS_APPLIED and TWEAKS_SKIPPED;
#   * apply_tweak, redefined verbatim from the entry script -- it lives there
#     rather than in any lib, the same arrangement arch_perf_harness.sh
#     handles with add_finding/add_action;
#   * the real log_*/has_cmd helpers, via scripts/lib/common.sh.
#
# NOT to be confused with arch_perf_harness.sh, which serves a different entry
# script (diagnose_arch_performance.sh) and a different set of libs. The two
# families were mis-grouped in an earlier handoff; the distinct names are the
# fix for that.
#
# Every absolute write target of these libs is behind an override defaulting
# to the real location, because run_all.sh runs UN-jailed in ci_mirror.sh and
# in CI, where a bind mount would protect nothing.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_ROOT="$(cd "${FIXES_DIR}/../../../.." && pwd)"

# shellcheck source=lib_test_core.sh
. "${SCRIPT_DIR}/lib_test_core.sh"

# shellcheck source=../../../../lib/common.sh
. "${REPO_ROOT}/linux_configuration/scripts/lib/common.sh"

# --- globals and helpers owned by optimize_arch_desktop.sh ------------------

# Read by the libs under test, never by this harness, so static analysis
# cannot see the use; export makes the intent explicit.
export SYSCTL_DROPIN_DIR="${TEST_TMPDIR}/sysctl.d"
export UDEV_RULES_DIR="${TEST_TMPDIR}/udev.rules.d"
export CPUPOWER_CONF_FILE="${TEST_TMPDIR}/cpupower"
export SYSTEMD_UNIT_DIR="${TEST_TMPDIR}/systemd_units"
export JOURNALD_CONF_DIR="${TEST_TMPDIR}/journald.conf.d"
export DRY_RUN="false"
export AGGRESSIVE="false"
export INTERACTIVE_MODE="false"
TWEAKS_APPLIED=0
TWEAKS_SKIPPED=0

# Verbatim from optimize_arch_desktop.sh.
apply_tweak() {
	local description="$1"
	shift

	echo ""
	log_info "$description"

	if [[ $DRY_RUN == "true" ]]; then
		echo "  [dry-run] Would run: $*"
		return 0
	fi

	if [[ $INTERACTIVE_MODE == "true" ]]; then
		if ! ask_yes_no "  Apply this optimization?"; then
			log_warn "Skipped."
			((TWEAKS_SKIPPED++)) || true
			return 0
		fi
	fi

	if "$@"; then
		log_ok "Done."
		((TWEAKS_APPLIED++)) || true
	else
		log_error "Failed (non-fatal, continuing)."
	fi
}

# --- external tool stubs ----------------------------------------------------

_arch_desktop_default_stubs() {
	local tool
	for tool in sysctl modprobe udevadm cpupower systemctl nvidia-smi \
		lsblk lscpu journalctl pacman; do
		_t_stub "$tool" 'exit 0'
	done
}

# arch_desktop_reset — start a test group from "nothing has happened yet".
arch_desktop_reset() {
	_t_reset_calls
	TWEAKS_APPLIED=0
	TWEAKS_SKIPPED=0
	DRY_RUN="false"
	AGGRESSIVE="false"
	INTERACTIVE_MODE="false"
	export DRY_RUN AGGRESSIVE INTERACTIVE_MODE
	rm -rf "${SYSCTL_DROPIN_DIR}" "${UDEV_RULES_DIR}" "${SYSTEMD_UNIT_DIR}" \
		"${JOURNALD_CONF_DIR}"
	mkdir -p "${SYSCTL_DROPIN_DIR}" "${UDEV_RULES_DIR}" "${SYSTEMD_UNIT_DIR}" \
		"${JOURNALD_CONF_DIR}"
	rm -f "${CPUPOWER_CONF_FILE}"
	_t_full_path
	_arch_desktop_default_stubs
}

# _t_dropin FILE — the contents of a sysctl drop-in written this round.
_t_dropin() {
	cat "${SYSCTL_DROPIN_DIR}/$1" 2>/dev/null || true
}

arch_desktop_reset
