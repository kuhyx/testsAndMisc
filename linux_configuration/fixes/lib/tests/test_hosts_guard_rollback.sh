#!/usr/bin/env bash
# lib/tests/test_hosts_guard_rollback.sh — tests for hosts_guard_rollback.sh:
# show_status, save_rollback_state and do_rollback.
#
# Calls go through _t_run rather than `out="$(...)"`: command substitution
# forks a subshell, and kcov does not register a lib whose first execution
# happens inside one.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=hosts_guard_harness.sh
. "${SCRIPT_DIR}/hosts_guard_harness.sh"

# shellcheck source=../hosts_guard_migrate.sh
. "${FIXES_DIR}/lib/hosts_guard_migrate.sh"

# shellcheck source=../hosts_guard_rollback.sh
. "${FIXES_DIR}/lib/hosts_guard_rollback.sh"

printf '\n-- show_status --\n'

# Case 1: nothing registered, hooks gone, units absent.
hosts_guard_reset
_t_stub systemctl 'exit 1'
_t_run show_status
_t_contains "$out" "hosts NOT registered" "show_status: reports an unregistered instance"
_t_contains "$out" "10-unlock-etc-hosts.hook retired" "show_status: reports a retired hook"
_t_contains "$out" "hosts-guard.path is absent" \
	"show_status: reports an absent unit rather than an empty state"

# Case 2: registered instances, hooks still present, a unit still enabled.
# `systemctl is-enabled` PRINTS the state but EXITS 1 for anything not
# enabled, which is why the lib cannot use `|| echo absent`.
hosts_guard_reset
_t_register hosts nsswitch resolved
: >"${HOOKS_DIR}/10-unlock-etc-hosts.hook"
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-enabled ]] && { echo enabled; exit 0; }
exit 0
STUB
_t_run show_status
_t_contains "$out" "hosts registered" "show_status: reports a registered instance"
_t_contains "$out" "10-unlock-etc-hosts.hook still present" \
	"show_status: warns about a surviving hook"
_t_contains "$out" "hosts-guard.path is enabled" "show_status: warns about an enabled unit"

# Case 3: a unit that is disabled rather than absent -- is-enabled prints the
# state AND exits non-zero, and the lib must keep the printed word.
hosts_guard_reset
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-enabled ]] && { echo disabled; exit 1; }
exit 0
STUB
_t_run show_status
_t_contains "$out" "hosts-guard.path is disabled" \
	"show_status: keeps the state systemd printed on a non-zero exit"
_t_lacks "$out" "hosts-guard.path is absent" \
	"show_status: does not overwrite a real state with 'absent'"

printf '\n-- save_rollback_state --\n'

# Case 4: hooks are backed up and unit states recorded.
hosts_guard_reset
: >"${HOOKS_DIR}/10-unlock-etc-hosts.hook"
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-enabled ]] && { echo enabled; exit 0; }
exit 0
STUB
_t_run save_rollback_state
_t_contains "$out" "backed up 10-unlock-etc-hosts.hook" \
	"save_rollback_state: backs up a present hook"
_t_eq "yes" "$([[ -f "${STATE_DIR}/hooks/10-unlock-etc-hosts.hook" ]] && echo yes || echo no)" \
	"save_rollback_state: the backup lands in the state dir"
_t_contains "$(cat "${STATE_DIR}/units.state")" "hosts-guard.path=enabled" \
	"save_rollback_state: records the exact prior enablement"

# Case 5: an existing backup is NOT overwritten -- the first capture is the
# pre-migration truth, and a second run must not clobber it.
hosts_guard_reset
mkdir -p "${STATE_DIR}/hooks"
printf 'ORIGINAL\n' >"${STATE_DIR}/hooks/10-unlock-etc-hosts.hook"
printf 'CHANGED\n' >"${HOOKS_DIR}/10-unlock-etc-hosts.hook"
_t_stub systemctl 'exit 0'
_t_run save_rollback_state
_t_eq "ORIGINAL" "$(cat "${STATE_DIR}/hooks/10-unlock-etc-hosts.hook")" \
	"save_rollback_state: keeps the first backup"

# Case 6: units.state is likewise written once only.
hosts_guard_reset
mkdir -p "${STATE_DIR}"
printf 'PRESERVED\n' >"${STATE_DIR}/units.state"
_t_stub systemctl 'exit 0'
_t_run save_rollback_state
_t_eq "PRESERVED" "$(cat "${STATE_DIR}/units.state")" \
	"save_rollback_state: does not rewrite units.state"

# Case 7: under --dry-run no unit state is recorded at all.
hosts_guard_reset
DRY_RUN=1
_t_stub systemctl 'exit 0'
_t_run save_rollback_state
_t_eq "no" "$([[ -f "${STATE_DIR}/units.state" ]] && echo yes || echo no)" \
	"save_rollback_state: dry-run records no unit state"

printf '\n-- do_rollback --\n'

# Case 8: no state dir at all -> refuse.
hosts_guard_reset
rm -rf "${STATE_DIR}"
rc=0
(do_rollback >"${TEST_TMPDIR}/o" 2>&1) || rc=$?
out="$(cat "${TEST_TMPDIR}/o")"
_t_eq "1" "$rc" "do_rollback: exits 1 with no rollback state"
_t_contains "$out" "nothing to roll back to" "do_rollback: explains the refusal"

# Case 9: a full rollback -- uninstall keeps the canonical copy, hooks are
# restored, enabled units come back, and the legacy enforcement re-runs.
hosts_guard_reset
_t_register hosts
mkdir -p "${STATE_DIR}/hooks"
printf 'HOOK\n' >"${STATE_DIR}/hooks/10-unlock-etc-hosts.hook"
printf 'hosts-guard.path=enabled\nnsswitch-guard.path=disabled\n' >"${STATE_DIR}/units.state"
_t_run do_rollback
calls="$(_t_calls)"
_t_contains "$calls" "file-guard uninstall hosts --keep-canonical" \
	"do_rollback: keeps the canonical copy, so a rollback is not data loss"
_t_eq "HOOK" "$(cat "${HOOKS_DIR}/10-unlock-etc-hosts.hook")" \
	"do_rollback: restores the backed-up hook"
_t_contains "$calls" "enable --now hosts-guard.path" \
	"do_rollback: re-enables a unit that was enabled before"
_t_lacks "$calls" "enable --now nsswitch-guard.path" \
	"do_rollback: leaves a unit that was disabled before"
_t_contains "$calls" "start hosts-guard.service" \
	"do_rollback: re-runs the legacy enforcement"
_t_contains "$calls" "restart hosts-bind-mount.service" \
	"do_rollback: rebuilds the read-only bind mount last"
_t_contains "$out" "rollback complete" "do_rollback: reports completion"

# Case 10: no units.state -> warn and leave the units alone rather than
# guessing which of them ought to be enabled.
hosts_guard_reset
mkdir -p "${STATE_DIR}"
_t_run do_rollback
_t_contains "$out" "no units.state recorded" "do_rollback: warns when it cannot restore units"
_t_lacks "$(_t_calls)" "enable --now" "do_rollback: enables nothing without a record"

# Case 11: an instance that is not registered is not uninstalled.
hosts_guard_reset
mkdir -p "${STATE_DIR}"
_t_run do_rollback
_t_lacks "$(_t_calls)" "file-guard uninstall" \
	"do_rollback: does not uninstall an unregistered instance"

# Case 12: a unit systemd knows nothing about is recorded as "absent"
# rather than as an empty string, which is the fallback arm inside the
# state-writing loop.
hosts_guard_reset
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-enabled ]] && exit 1
exit 0
STUB
_t_run save_rollback_state
_t_contains "$(cat "${STATE_DIR}/units.state")" "hosts-guard.path=absent" \
	"save_rollback_state: records an unknown unit as absent"
_t_eq "0" "$(grep -c '=$' "${STATE_DIR}/units.state")" \
	"save_rollback_state: never writes a line with an empty state"

# Case 13: re-enabling a unit can fail, and the rollback must warn and carry
# on rather than abort with units half-restored.
hosts_guard_reset
mkdir -p "${STATE_DIR}"
printf 'hosts-guard.path=enabled\nresolved-guard.path=enabled\n' >"${STATE_DIR}/units.state"
_t_stub_stdin systemctl <<'STUB'
[[ $1 == enable ]] && exit 1
exit 0
STUB
_t_run do_rollback
_t_contains "$out" "could not re-enable hosts-guard.path" \
	"do_rollback: warns when a unit will not re-enable"
_t_contains "$out" "could not re-enable resolved-guard.path" \
	"do_rollback: keeps going after a failed re-enable"
_t_contains "$out" "rollback complete" "do_rollback: still completes"

printf '\nhosts_guard_rollback: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
