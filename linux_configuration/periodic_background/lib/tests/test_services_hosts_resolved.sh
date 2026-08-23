#!/usr/bin/env bash
# Tests for the systemd-resolved half of check_hosts (lib/services_hosts.sh).
#
# Split out of test_services_hosts.sh for the repo-wide 250-line cap. Every
# case here is a way systemd-resolved can answer a query WITHOUT consulting
# /etc/hosts, which leaves the whole blocking stack inert while a correct,
# immutable, fully-populated hosts file sits on disk: ReadEtcHosts turned off,
# DNSOverTLS turned on, or either re-enabled by a drop-in override.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"
# shellcheck source=../services_hosts_fix.sh
. "${SCRIPT_DIR}/../services_hosts_fix.sh"
# shellcheck source=../services_hosts.sh
. "${SCRIPT_DIR}/../services_hosts.sh"

_t_called_in() { # <haystack> <needle> <what>
	if [[ "$1" == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (missing '$2')"
	fi
}

echo "== check_hosts: ReadEtcHosts=no is an error and is repaired =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
printf '[Resolve]\nReadEtcHosts=no\n' >"${SERVICES_ROOT}/etc/systemd/resolved.conf"
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "bypassed by systemd-resolved" "the resolved bypass is called out"
_t_called_in "$(cat "${SERVICES_ROOT}/etc/systemd/resolved.conf")" "ReadEtcHosts=yes" "the setting is repaired"
_t_called 'systemctl restart systemd-resolved' "systemd-resolved is restarted so the change takes"

echo "== check_hosts: DNSOverTLS enabled is an error and is repaired =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
printf '[Resolve]\nReadEtcHosts=yes\nDNSOverTLS=yes\n' >"${SERVICES_ROOT}/etc/systemd/resolved.conf"
check_hosts >"${TEST_TMPDIR}/out.txt"
# The message interpolates $SYSROOT, so match on the stable part of it.
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "DNSOverTLS='yes'" "DNSOverTLS is called out as a bypass"
_t_called_in "$(cat "${SERVICES_ROOT}/etc/systemd/resolved.conf")" "#DNSOverTLS=no" "it is commented out"

echo "== check_hosts: drop-in overrides are an error and are removed =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
# A drop-in can re-enable either bypass without touching resolved.conf, so the
# repairs above are not durable while one survives.
sysfile etc/systemd/resolved.conf.d/99-override.conf
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "drop-in override" "the drop-in is called out"
if [[ -f "${SERVICES_ROOT}/etc/systemd/resolved.conf.d/99-override.conf" ]]; then
	_t_fail "the drop-in is deleted"
else
	_t_pass "the drop-in is deleted"
fi

echo "== check_hosts: a missing resolved.conf warns =="
reset_state
stage_hosts_ok
sysrm etc/systemd/resolved.conf
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "resolved.conf does not exist" "the missing file is reported"

_t_summary
