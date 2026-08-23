#!/usr/bin/env bash
# lib/tests/test_hosts_guard_migrate_flow.sh — tests for the migration flow
# itself: migrate_instance, stop_legacy_units_for, retire_legacy_hooks and
# do_migrate.
#
# Split from test_hosts_guard_migrate.sh to hold every file under the
# 250-line cap.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=hosts_guard_harness.sh
. "${SCRIPT_DIR}/hosts_guard_harness.sh"

# shellcheck source=../hosts_guard_migrate.sh
. "${FIXES_DIR}/lib/hosts_guard_migrate.sh"

# shellcheck source=../hosts_guard_rollback.sh
. "${FIXES_DIR}/lib/hosts_guard_rollback.sh"

printf '\n-- stop_legacy_units_for --\n'

# Case 1: only the units whose name matches the instance prefix are touched.
hosts_guard_reset
_t_run stop_legacy_units_for hosts
calls="$(_t_calls)"
_t_contains "$calls" "disable --now hosts-guard.path" \
	"stop_legacy_units_for: disables the matching path unit"
_t_contains "$calls" "disable --now hosts-bind-mount.service" \
	"stop_legacy_units_for: disables the matching bind-mount unit"
_t_lacks "$calls" "nsswitch-guard" \
	"stop_legacy_units_for: leaves another instance's units alone"

# Case 2: a unit systemd does not know about is skipped, not disabled.
hosts_guard_reset
_t_stub_stdin systemctl <<'STUB'
[[ $1 == list-unit-files ]] && exit 1
exit 0
STUB
_t_run stop_legacy_units_for hosts
_t_lacks "$(_t_calls)" "disable --now" \
	"stop_legacy_units_for: skips units systemd does not have"

printf '\n-- migrate_instance --\n'

# Case 3: an already-registered instance is skipped before anything is done.
hosts_guard_reset
_t_register hosts
_t_run migrate_instance hosts
_t_contains "$out" "already registered - skipping" \
	"migrate_instance: skips an instance guard-lib already owns"
_t_lacks "$(_t_calls)" "guardctl" "migrate_instance: does not call guardctl when skipping"

# Case 4: a target that does not exist is warned about, not migrated.
hosts_guard_reset
rm -f "${HOSTS_FILE}"
_t_run migrate_instance hosts
_t_contains "$out" "does not exist - skipping" \
	"migrate_instance: warns about a missing target"
_t_lacks "$(_t_calls)" "guardctl" "migrate_instance: does not migrate a missing target"

# Case 5: the hosts instance -- bind-mounted, no plugin.
hosts_guard_reset
_t_run migrate_instance hosts
calls="$(_t_calls)"
_t_contains "$calls" "guardctl file-guard install hosts" \
	"migrate_instance: installs the hosts instance"
_t_contains "$calls" "--bind-mount" "migrate_instance: passes --bind-mount for hosts"
_t_lacks "$calls" "--plugin" "migrate_instance: passes no plugin for hosts"
_t_contains "$calls" "chattr -i" "migrate_instance: clears the immutable flag first"

# Case 6: the resolved instance -- a plugin AND an --also-watch directory.
hosts_guard_reset
printf 'x\n' >"${TEST_TMPDIR}/resolved.conf"
_t_run migrate_instance resolved
calls="$(_t_calls)"
_t_contains "$calls" "--plugin" "migrate_instance: passes the plugin for resolved"
_t_contains "$calls" "resolved-plugin.sh" "migrate_instance: names the right plugin"
_t_contains "$calls" "--also-watch" "migrate_instance: passes the also-watch dir"
_t_lacks "$calls" "--bind-mount" "migrate_instance: does not bind-mount resolved"

printf '\n-- retire_legacy_hooks --\n'

# Case 7: no hooks left -> says so, removes nothing.
hosts_guard_reset
_t_run retire_legacy_hooks
_t_contains "$out" "already retired" "retire_legacy_hooks: reports nothing to do"

# Case 8: both hooks present -> both removed.
hosts_guard_reset
: >"${HOOKS_DIR}/10-unlock-etc-hosts.hook"
: >"${HOOKS_DIR}/90-relock-etc-hosts.hook"
_t_run retire_legacy_hooks
_t_eq "0" "$?" "retire_legacy_hooks: returns 0 after retiring"
_t_contains "$out" "retired 10-unlock-etc-hosts.hook" \
	"retire_legacy_hooks: names the unlock hook"
_t_contains "$out" "retired 90-relock-etc-hosts.hook" \
	"retire_legacy_hooks: names the relock hook"
_t_lacks "$out" "already retired" "retire_legacy_hooks: does not also claim there was nothing to do"

printf '\n-- do_migrate --\n'

# Case 9: nothing registers -> REFUSE to retire the legacy hooks. Retiring
# them after a failed migration would leave the files with no pacman unlock
# hook at all, and the next transaction would fight chattr +i.
hosts_guard_reset
_t_templates
: >"${HOOKS_DIR}/10-unlock-etc-hosts.hook"
cat >"${GUARDCTL}" <<'STUB'
#!/usr/bin/env bash
printf 'guardctl %s\n' "$*" >>"${LIB_TEST_DEV}/calls"
exit 0
STUB
chmod +x "${GUARDCTL}"
rc=0
(do_migrate >"${TEST_TMPDIR}/o" 2>&1) || rc=$?
out="$(cat "${TEST_TMPDIR}/o")"
_t_eq "1" "$rc" "do_migrate: exits 1 when no instance registered"
_t_contains "$out" "refusing to retire the legacy hooks" "do_migrate: explains the refusal"
_t_eq "yes" "$([[ -f "${HOOKS_DIR}/10-unlock-etc-hosts.hook" ]] && echo yes || echo no)" \
	"do_migrate: leaves the legacy hook in place after refusing"

# Case 10: a successful migration -- guardctl registers each instance, so the
# hooks are retired and the summary counts them.
hosts_guard_reset
_t_templates
printf 'x\n' >"${TEST_TMPDIR}/nsswitch.conf"
printf 'x\n' >"${TEST_TMPDIR}/resolved.conf"
: >"${HOOKS_DIR}/10-unlock-etc-hosts.hook"
cat >"${GUARDCTL}" <<'STUB'
#!/usr/bin/env bash
printf 'guardctl %s\n' "$*" >>"${LIB_TEST_DEV}/calls"
# Register the instance, the way the real guardctl would.
if [[ $2 == install ]]; then
	: >"${LIB_TEST_TARGETS}/$3.conf"
fi
exit 0
STUB
chmod +x "${GUARDCTL}"
LIB_TEST_TARGETS="${TARGETS_DIR}"
export LIB_TEST_TARGETS
_t_run do_migrate
_t_contains "$out" "migration complete (3 instance(s) registered)" \
	"do_migrate: counts every registered instance"
_t_eq "no" "$([[ -f "${HOOKS_DIR}/10-unlock-etc-hosts.hook" ]] && echo yes || echo no)" \
	"do_migrate: retires the legacy hooks once guard-lib owns something"

# Case 11: under --dry-run nothing registers, but the refusal must NOT fire --
# a dry run is expected to register nothing.
hosts_guard_reset
_t_templates
DRY_RUN=1
_t_run do_migrate
_t_eq "0" "$?" "do_migrate: dry-run does not trip the no-registration refusal"
_t_contains "$out" "DRY-RUN" "do_migrate: dry-run announces its intent"

printf '\nhosts_guard_migrate (flow): %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
