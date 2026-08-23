#!/usr/bin/env bash
# lib/tests/nvidia_config_harness.sh — shared setup for the nvidia_config.sh
# tests.
#
# Sourced, not executed. Builds on lib_test_core.sh and adds what the lib
# reads from its entry script, nvidia_troubleshoot.sh:
#
#   * INTERACTIVE_MODE, the flag that decides whether install_pyroveil
#     prompts or auto-installs;
#   * SUDO_USER, which the lib uses both to build the home path and as the
#     user it drops to for every git/cmake call;
#   * the real log_*/has_cmd helpers, via scripts/lib/common.sh.
#
# The four paths the lib writes to are behind overrides that default to the
# real locations, so nothing here can reach /etc or a real home directory.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_ROOT="$(cd "${FIXES_DIR}/../../../.." && pwd)"

# shellcheck source=lib_test_core.sh
. "${SCRIPT_DIR}/lib_test_core.sh"

# shellcheck source=../../../../lib/common.sh
. "${REPO_ROOT}/linux_configuration/scripts/lib/common.sh"

# --- globals owned by nvidia_troubleshoot.sh and the seams ------------------

# Read by the lib under test, never by this harness, so static analysis
# cannot see the use; export makes the intent explicit.
export XORG_CONF="${TEST_TMPDIR}/xorg.conf"
export XORG_CONF_D="${TEST_TMPDIR}/xorg.conf.d"
export PROFILE_FILE="${TEST_TMPDIR}/profile"
export USER_HOME="${TEST_TMPDIR}/home"
export INTERACTIVE_MODE="false"
export SUDO_USER="testuser"

_nvidia_default_stubs() {
	local tool
	for tool in git cmake ninja gcc sudo chown; do
		_t_stub "$tool" 'exit 0'
	done
}

# nvidia_reset — start a test group from "nothing has happened yet".
nvidia_reset() {
	_t_reset_calls
	INTERACTIVE_MODE="false"
	export INTERACTIVE_MODE
	rm -rf "${XORG_CONF_D}" "${USER_HOME}"
	mkdir -p "${XORG_CONF_D}" "${USER_HOME}"
	rm -f "${XORG_CONF}" "${XORG_CONF}".backup.* "${PROFILE_FILE}" \
		"${PROFILE_FILE}".backup.*
	: >"${PROFILE_FILE}"
	_t_full_path
	_nvidia_default_stubs
}

# _t_nvidia_conf — the NVIDIA xorg drop-in written this round.
_t_nvidia_conf() {
	cat "${XORG_CONF_D}/20-nvidia.conf" 2>/dev/null || true
}

# _t_profile_text — the profile file's contents this round.
_t_profile_text() {
	cat "${PROFILE_FILE}" 2>/dev/null || true
}

# _t_backups PATH — how many backup copies exist for PATH.
_t_backups() {
	local count
	count=$(find "$(dirname "$1")" -maxdepth 1 -name "$(basename "$1").backup.*" 2>/dev/null | wc -l)
	printf '%s\n' "$count"
}

nvidia_reset
