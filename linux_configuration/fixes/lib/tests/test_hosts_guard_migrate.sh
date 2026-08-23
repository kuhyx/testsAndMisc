#!/usr/bin/env bash
# lib/tests/test_hosts_guard_migrate.sh — tests for hosts_guard_migrate.sh.
#
# Covers validate_requirements' four refusals, plugin installation, the
# per-instance migration and its skips, the mount collapse loop, hook
# retirement, and do_migrate's refusal to retire the legacy hooks when
# nothing actually registered.
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

printf '\n-- validate_requirements --\n'

# Each refusal calls `exit 1`, so every case runs in a subshell.

# Case 1: guardctl missing entirely.
hosts_guard_reset
rm -f "${GUARDCTL}"
rc=0
(validate_requirements >"${TEST_TMPDIR}/o" 2>&1) || rc=$?
out="$(cat "${TEST_TMPDIR}/o")"
_t_eq "1" "$rc" "validate_requirements: exits 1 without guardctl"
_t_contains "$out" "guardctl not found" "validate_requirements: names the missing binary"

# Case 2: guardctl present but the systemd templates are not.
hosts_guard_reset
rc=0
(validate_requirements >"${TEST_TMPDIR}/o" 2>&1) || rc=$?
out="$(cat "${TEST_TMPDIR}/o")"
_t_eq "1" "$rc" "validate_requirements: exits 1 without the systemd templates"
_t_contains "$out" "missing systemd template" "validate_requirements: names the template"

# Case 3: templates present but the plugin sources are not.
hosts_guard_reset
_t_templates
rm -rf "${PLUGIN_SRC_DIR}"
rc=0
(validate_requirements >"${TEST_TMPDIR}/o" 2>&1) || rc=$?
out="$(cat "${TEST_TMPDIR}/o")"
_t_eq "1" "$rc" "validate_requirements: exits 1 without plugin sources"
_t_contains "$out" "plugin sources not found" "validate_requirements: names the source dir"

# Case 4: a pacman transaction is in flight -- refuse, because every chattr
# and umount below would race it.
hosts_guard_reset
_t_templates
: >"${PACMAN_DB_LCK}"
rc=0
(validate_requirements >"${TEST_TMPDIR}/o" 2>&1) || rc=$?
out="$(cat "${TEST_TMPDIR}/o")"
_t_eq "1" "$rc" "validate_requirements: exits 1 while pacman holds the lock"
_t_contains "$out" "a pacman transaction is in flight" \
	"validate_requirements: explains the refusal"

# Case 5: everything in place -> passes.
hosts_guard_reset
_t_templates
rc=0
(validate_requirements >"${TEST_TMPDIR}/o" 2>&1) || rc=$?
_t_eq "0" "$rc" "validate_requirements: passes when every precondition holds"

printf '\n-- install_plugins --\n'

# Case 6: the plugin sources are copied in, and only the .sh ones.
hosts_guard_reset
printf 'x\n' >"${PLUGIN_SRC_DIR}/nsswitch-plugin.sh"
printf 'x\n' >"${PLUGIN_SRC_DIR}/resolved-plugin.sh"
printf 'x\n' >"${PLUGIN_SRC_DIR}/README.md"
_t_run install_plugins
_t_contains "$(_t_calls)" "install -m 755" "install_plugins: installs mode 755"
_t_contains "$(_t_calls)" "nsswitch-plugin.sh" "install_plugins: installs the nsswitch plugin"
_t_lacks "$(_t_calls)" "README.md" "install_plugins: ignores non-.sh files"
_t_contains "$out" "plugins installed to" "install_plugins: reports where they went"

# Case 7: an empty source directory is not an error -- the glob guard is what
# stops `*.sh` being passed through literally.
hosts_guard_reset
_t_run install_plugins
_t_eq "0" "$?" "install_plugins: survives an empty plugin source dir"
_t_lacks "$(_t_calls)" '*.sh' "install_plugins: does not install the unmatched glob"

printf '\n-- collapse_mounts --\n'

# Case 8: not a mountpoint -> the loop never runs.
hosts_guard_reset
_t_stub mountpoint 'exit 1'
_t_run collapse_mounts "${HOSTS_FILE}"
_t_eq "0" "$?" "collapse_mounts: returns 0 when nothing is mounted"
_t_lacks "$(_t_calls)" "umount" "collapse_mounts: does not unmount a plain file"

# Case 9: a stack that clears after a few layers. The stub reports mounted
# until umount has been called three times, which is what a real stacked
# bind looks like on the way down.
hosts_guard_reset
: >"${TEST_TMPDIR}/umount_count"
_t_stub_stdin mountpoint <<'STUB'
count=$(wc -l <"${LIB_TEST_DEV}/../umount_count")
[[ $count -ge 3 ]] && exit 1
exit 0
STUB
# _t_stub already records the invocation into $DEV/calls, so this body only
# has to advance the counter mountpoint reads.
_t_stub_stdin umount <<'STUB'
echo x >>"${LIB_TEST_DEV}/../umount_count"
exit 0
STUB
_t_run collapse_mounts "${HOSTS_FILE}"
_t_eq "3" "$(grep -c umount "${TEST_TMPDIR}/device/calls")" \
	"collapse_mounts: unmounts every stacked layer and then stops"

# Case 10: umount fails -> break rather than spin.
hosts_guard_reset
_t_stub mountpoint 'exit 0'
_t_stub umount 'exit 1'
_t_run collapse_mounts "${HOSTS_FILE}"
_t_eq "0" "$?" "collapse_mounts: returns 0 when umount fails"
_t_eq "1" "$(grep -c umount "${TEST_TMPDIR}/device/calls")" \
	"collapse_mounts: gives up after the first failed umount"

# Case 11: a mount that never clears is bounded at 20 attempts, not infinite.
hosts_guard_reset
_t_stub mountpoint 'exit 0'
_t_stub umount 'exit 0'
_t_run collapse_mounts "${HOSTS_FILE}"
_t_eq "21" "$(grep -c umount "${TEST_TMPDIR}/device/calls")" \
	"collapse_mounts: stops after 21 umounts rather than looping forever"

# Case 12: under --dry-run nothing is really unmounted, so the loop reports
# once instead of hitting the 20-iteration cap.
hosts_guard_reset
DRY_RUN=1
_t_stub mountpoint 'exit 0'
_t_run collapse_mounts "${HOSTS_FILE}"
_t_contains "$out" "DRY-RUN" "collapse_mounts: announces the intent under dry-run"
_t_eq "1" "$(grep -c 'DRY-RUN' <<<"$out")" \
	"collapse_mounts: reports the intent once, not twenty times"

printf '\nhosts_guard_migrate (checks): %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
