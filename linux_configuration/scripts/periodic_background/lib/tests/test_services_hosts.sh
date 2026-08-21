#!/usr/bin/env bash
# Tests for lib/services_hosts.sh and lib/services_hosts_fix.sh — the /etc/hosts
# blocking stack: the hosts file, its immutable attribute, the three guard-lib
# instances, the pacman hook pair, and the systemd-resolved settings that can
# silently bypass /etc/hosts.
#
# This is the highest-stakes check in the family, so the repair half gets its
# own cases: nsswitch losing 'files', ReadEtcHosts turning off, DNSOverTLS
# turning on, and drop-in overrides appearing. Each of those is a real bypass
# that leaves every blocked domain resolvable while the check still finds a
# hosts file sitting there.
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

echo "== check_hosts: a fully healthy stack records ok =="
reset_state
stage_hosts_ok
check_hosts >"${TEST_TMPDIR}/out.txt"
out="$(cat "${TEST_TMPDIR}/out.txt")"
_t_called_in "$out" "immutable attribute set" "the immutable attribute is recognised"
_t_called_in "$out" "guard-lib 'hosts' instance is active" "the hosts guard is recognised"
_t_called_in "$out" "Pacman hooks installed" "the hook pair is recognised"
_t_eq "ok" "$(get_service_status "hosts")" "a healthy stack records ok"
_t_not_called 'ran migrate_hosts_guard' "a healthy stack runs no migration"

echo "== check_hosts: a short hosts file warns =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
sysfile etc/hosts 10
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "may not be installed" "a short hosts file is reported"
_t_called 'ran hosts_install' "a short hosts file is reinstalled"

echo "== check_hosts: a missing hosts file is an error =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
sysrm etc/hosts
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "/etc/hosts does not exist" "the missing file is reported"
_t_called 'ran hosts_install' "it is reinstalled"

echo "== check_hosts: a mutable hosts file warns =="
reset_state
stage_hosts_ok
: >"${DEV}/immutable"
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "not immutable" "a mutable hosts file is reported"

echo "== check_hosts: a missing StevenBlack cache warns =="
reset_state
stage_hosts_ok
sysrm etc/hosts.stevenblack
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "StevenBlack cache not found" "the missing cache is reported"

echo "== check_hosts: nsswitch without 'files' is an error and is repaired =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
# Without 'files' the resolver answers first and every /etc/hosts entry is
# bypassed -- the whole blocking stack is inert while looking installed.
printf 'hosts: resolve dns\n' >"${SERVICES_ROOT}/etc/nsswitch.conf"
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "/etc/hosts is bypassed" "the bypass is called out"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "adding 'files'" "the repair announces itself"
_t_called_in "$(grep '^hosts:' "${SERVICES_ROOT}/etc/nsswitch.conf")" "files" "'files' is put back on the hosts line"

echo "== check_hosts: a missing nsswitch.conf is an error =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
sysrm etc/nsswitch.conf
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "/etc/nsswitch.conf does not exist" "the missing file is reported"

echo "== check_hosts: an unhealthy guard-lib instance is repaired =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
printf '%s\n' hosts resolved >"${DEV}/guard_healthy"
printf 'nsswitch\n' >"${DEV}/guard_degraded"
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "'nsswitch' instance is missing or unhealthy" "the degraded instance is named"
_t_called 'ran migrate_hosts_guard' "the guard-lib migration is re-run"

echo "== check_hosts: missing pacman hooks trigger the migration =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
sysrm etc/pacman.d/hooks/90-guard-lib-relock-all.hook
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "Pacman hooks not installed" "the missing hook is reported"
_t_called 'ran migrate_hosts_guard' "the migration is re-run to reinstate them"

echo "== check_hosts: a repaired stack is promoted back to ok =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
# Only the resolver config is wrong; the guard-lib trio and hooks stay healthy,
# so the post-repair re-verify passes and the row goes back to ok.
printf 'hosts: resolve dns\n' >"${SERVICES_ROOT}/etc/nsswitch.conf"
check_hosts >/dev/null
_t_eq "ok" "$(get_service_status "hosts")" "a stack that verifies after repair is promoted to ok"

echo "== check_hosts: --status reports without repairing =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
STATUS_ONLY=1
printf 'hosts: resolve dns\n' >"${SERVICES_ROOT}/etc/nsswitch.conf"
check_hosts >/dev/null
_t_called_in "$(grep '^hosts:' "${SERVICES_ROOT}/etc/nsswitch.conf")" "resolve" "--status leaves nsswitch untouched"
if grep -q 'files' "${SERVICES_ROOT}/etc/nsswitch.conf"; then
	_t_fail "--status applies no repair"
else
	_t_pass "--status applies no repair"
fi
_t_not_called 'ran migrate_hosts_guard' "--status runs no migration"

echo "== check_hosts: --dry-run never claims a repair landed =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
DRY_RUN=1
printf 'hosts: resolve dns\n' >"${SERVICES_ROOT}/etc/nsswitch.conf"
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "DRY-RUN:" "the repair is announced, not performed"
# The re-verify is skipped under --dry-run, so the row must NOT be promoted:
# nothing was actually repaired.
_t_eq "error" "$(get_service_status "hosts")" "a dry run never promotes the row to ok"

echo "== check_hosts: missing repair scripts are recorded =="
reset_state
stage_hosts_ok
rm -f "$HOSTS_INSTALL_SCRIPT" "$GUARD_LIB_MIGRATE_SCRIPT"
sysrm etc/hosts
printf '%s\n' hosts resolved >"${DEV}/guard_healthy"
printf 'nsswitch\n' >"${DEV}/guard_degraded"
check_hosts >/dev/null
_t_eq "2" "${#MISSING_SCRIPTS[@]}" "both missing repair scripts are recorded"

echo "== check_hosts: resolved.conf immutable attribute is recognised =="
reset_state
stage_hosts_ok
printf '%s\n' "${SERVICES_ROOT}/etc/hosts" \
	"${SERVICES_ROOT}/etc/systemd/resolved.conf" >"${DEV}/immutable"
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "resolved.conf has immutable attribute" "the resolved.conf attribute is recognised"

echo "== check_hosts: each guard-lib instance failing alone is reported =="
for inst in hosts nsswitch resolved; do
	reset_state
	stage_hosts_ok
	make_installer "$HOSTS_INSTALL_SCRIPT"
	make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
	# Everything healthy except this one instance.
	printf '%s\n' hosts nsswitch resolved | grep -vx "$inst" >"${DEV}/guard_healthy"
	check_hosts >"${TEST_TMPDIR}/out.txt"
	_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "'${inst}' instance is missing or unhealthy" \
		"a failing '${inst}' guard is named"
	_t_called 'ran migrate_hosts_guard' "and the migration is re-run for '${inst}'"
done

echo "== check_hosts: a warning must never mask an error =="
# Regression test for the status-downgrade bug: several checks assigned
# status="warning" unconditionally, so a check running LATER in the function
# could overwrite the status="error" an earlier one had set. Because
# report_and_fix (and check_hosts' own repair gate) only act on "error", the
# downgraded fault was reported and then silently never repaired.
#
# Here the guard-lib 'hosts' instance is broken (an error) AND the pacman hook
# pair is missing (a warning, and checked afterwards). The row must stay
# "error" and the repair must run.
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
printf '%s\n' nsswitch resolved >"${DEV}/guard_healthy"
sysrm etc/pacman.d/hooks/10-guard-lib-unlock-all.hook
sysrm etc/pacman.d/hooks/90-guard-lib-relock-all.hook
check_hosts >"${TEST_TMPDIR}/out.txt"
_t_called 'ran migrate_hosts_guard' "a broken guard is still repaired when a later check warns"

# The same shape with the short-hosts-file warning, which is checked FIRST and
# so cannot mask anything -- but the immutable/cache warnings after it can.
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
printf '%s\n' nsswitch resolved >"${DEV}/guard_healthy"
: >"${DEV}/immutable"
sysrm etc/hosts.stevenblack
check_hosts >/dev/null
_t_called 'ran migrate_hosts_guard' "a broken guard survives the immutable and cache warnings"

_t_summary
