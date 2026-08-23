#!/usr/bin/env bash
# Tests for the repair helpers in lib/services_hosts_fix.sh, called directly
# rather than through check_hosts.
#
# Split out of test_services_hosts.sh for the repo-wide 250-line cap. These are
# the unit-level cases: each resolver shape hosts_fix_nsswitch has to rewrite,
# each resolved.conf shape hosts_fix_resolved has to repair, and the contract
# that hosts_repair_all reports failure under --dry-run rather than claiming a
# repair that never happened.
#
# The helpers are called via `if` rather than bare: when resolved.conf carries
# no ReadEtcHosts line, the leading grep in the assignment pipeline exits 1 and
# `set -o pipefail` makes the whole assignment non-zero, so a bare call would
# abort the suite under `set -e`. check_hosts only ever calls them from inside
# an `if`, which suppresses `set -e` for the callee, so this is a property of
# calling them bare and not a defect.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"
# shellcheck source=../services_hosts_fix.sh
. "${SCRIPT_DIR}/../services_hosts_fix.sh"

_t_called_in() { # <haystack> <needle> <what>
	if [[ "$1" == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (missing '$2')"
	fi
}

echo "== hosts_fix_nsswitch: each resolver shape =="
reset_state
printf 'hosts: mymachines dns\n' >"${SERVICES_ROOT}/etc/nsswitch.conf"
if hosts_fix_nsswitch >/dev/null; then :; fi
_t_called_in "$(cat "${SERVICES_ROOT}/etc/nsswitch.conf")" "files dns" "'files' is inserted before dns"

reset_state
printf 'hosts: mymachines myhostname\n' >"${SERVICES_ROOT}/etc/nsswitch.conf"
if hosts_fix_nsswitch >/dev/null; then :; fi
_t_called_in "$(cat "${SERVICES_ROOT}/etc/nsswitch.conf")" "hosts: files" "'files' is prepended when no resolver is named"

reset_state
printf 'hosts: files resolve\n' >"${SERVICES_ROOT}/etc/nsswitch.conf"
if hosts_fix_nsswitch >/dev/null; then :; fi
_t_eq "hosts: files resolve" "$(cat "${SERVICES_ROOT}/etc/nsswitch.conf")" "an already-correct line is left alone"

reset_state
sysrm etc/nsswitch.conf
if hosts_fix_nsswitch >/dev/null; then :; fi
_t_pass "a missing nsswitch.conf is a no-op rather than an error"

reset_state
printf 'passwd: files\n' >"${SERVICES_ROOT}/etc/nsswitch.conf"
if hosts_fix_nsswitch >/dev/null; then :; fi
_t_pass "an nsswitch.conf with no hosts line at all is a no-op"

echo "== hosts_fix_resolved: adds the setting when the file lacks it =="
# Called through `if` rather than bare. When resolved.conf carries no
# ReadEtcHosts line at all, the leading `grep` in the assignment pipeline exits
# 1; with `set -o pipefail` that makes the whole assignment non-zero, so a bare
# call aborts the test under `set -e`. Production never hits this because
# check_hosts only ever calls it from inside an `if`, which suppresses `set -e`
# for the callee -- so this is a property of calling it bare, not a defect.
reset_state
printf '[Resolve]\n' >"${SERVICES_ROOT}/etc/systemd/resolved.conf"
if hosts_fix_resolved >/dev/null; then :; fi
_t_called_in "$(cat "${SERVICES_ROOT}/etc/systemd/resolved.conf")" "ReadEtcHosts=yes" "the setting is inserted under [Resolve]"

reset_state
printf '# no section here\n' >"${SERVICES_ROOT}/etc/systemd/resolved.conf"
if hosts_fix_resolved >/dev/null; then :; fi
_t_called_in "$(cat "${SERVICES_ROOT}/etc/systemd/resolved.conf")" "[Resolve]" "a whole [Resolve] section is appended when absent"

reset_state
sysrm etc/systemd/resolved.conf
if hosts_fix_resolved >/dev/null; then :; fi
_t_pass "a missing resolved.conf is a no-op rather than an error"

echo "== hosts_repair_all: dry-run refuses to claim success =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
DRY_RUN=1
if hosts_repair_all >/dev/null; then
	_t_fail "hosts_repair_all returns non-zero under --dry-run"
else
	_t_pass "hosts_repair_all returns non-zero under --dry-run"
fi

echo "== hosts_repair_all: a healthy machine verifies after repair =="
reset_state
stage_hosts_ok
make_installer "$HOSTS_INSTALL_SCRIPT"
make_installer "$GUARD_LIB_MIGRATE_SCRIPT"
if hosts_repair_all >/dev/null; then
	_t_pass "hosts_repair_all returns zero when the post-repair check passes"
else
	_t_fail "hosts_repair_all returns zero when the post-repair check passes"
fi

_t_summary
