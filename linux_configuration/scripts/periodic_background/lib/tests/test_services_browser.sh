#!/usr/bin/env bash
# Tests for lib/services_browser.sh — the Chromium guest-mode policy check, the
# VirtualBox hosts-enforcement check, and the per-user workout locker service.
#
# All three are gated on something being present: a browser on PATH, VBoxManage
# on PATH, a user unit on the user bus. The harness owns PATH outright and the
# systemctl shim answers for the user bus, so every gate is drivable here.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=services_harness.sh
. "${SCRIPT_DIR}/services_harness.sh"
# shellcheck source=../services_browser.sh
. "${SCRIPT_DIR}/../services_browser.sh"

_t_called_in() { # <haystack> <needle> <what>
	if [[ "$1" == *"$2"* ]]; then
		_t_pass "$3"
	else
		_t_fail "$3 (missing '$2')"
	fi
}

TEST_USER="${SUDO_USER:-$USER}"
BROWSERS=(thorium-browser chromium google-chrome brave-browser)

# Write a managed-policy JSON carrying the guest-mode key into one browser's
# policy directory.
stage_policy() { # <policy-dir-relative>
	sysfile "$1/guest.json"
	printf '{"BrowserGuestModeEnabled": false}\n' >"${SERVICES_ROOT}/$1/guest.json"
}

echo "== check_guest_mode_removal: no browsers installed is not applicable =="
reset_state
absent_command "${BROWSERS[@]}"
check_guest_mode_removal >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "No Chromium-based browsers detected" "an absent browser set is skipped"
_t_eq "ok" "$(get_service_status "guest_mode_removal")" "no browsers leaves status ok"

echo "== check_guest_mode_removal: a browser with no policy is an error =="
reset_state
make_installer "$REMOVE_GUEST_MODE_SCRIPT"
absent_command "${BROWSERS[@]}"
present_command chromium
check_guest_mode_removal >/dev/null
_t_called 'ran remove_guest_mode' "an unpoliced browser runs the removal script"
_t_eq "1" "$FIXES_APPLIED" "the fix is counted"

echo "== check_guest_mode_removal: each browser's policy dir is honoured =="
for dir in etc/chromium/policies/managed etc/opt/chrome/policies/managed \
	etc/thorium/policies/managed etc/brave/policies/managed; do
	reset_state
	make_installer "$REMOVE_GUEST_MODE_SCRIPT"
	absent_command "${BROWSERS[@]}"
	present_command chromium
	stage_policy "$dir"
	check_guest_mode_removal >/dev/null
	_t_eq "ok" "$(get_service_status "guest_mode_removal")" "a policy in ${dir%%/policies*} satisfies the check"
	_t_not_called 'ran remove_guest_mode' "and runs no removal script"
done

echo "== check_guest_mode_removal: a policy dir without the guest key does not count =="
reset_state
make_installer "$REMOVE_GUEST_MODE_SCRIPT"
absent_command "${BROWSERS[@]}"
present_command chromium
sysfile etc/chromium/policies/managed/unrelated.json
printf '{"SomeOtherPolicy": true}\n' >"${SERVICES_ROOT}/etc/chromium/policies/managed/unrelated.json"
check_guest_mode_removal >/dev/null
_t_called 'ran remove_guest_mode' "a policy file without the guest-mode key is not enough"

echo "== check_guest_mode_removal: --status and a missing script =="
reset_state
make_installer "$REMOVE_GUEST_MODE_SCRIPT"
absent_command "${BROWSERS[@]}"
present_command chromium
STATUS_ONLY=1
check_guest_mode_removal >/dev/null
_t_not_called 'ran remove_guest_mode' "--status never repairs"

reset_state
rm -f "$REMOVE_GUEST_MODE_SCRIPT"
absent_command "${BROWSERS[@]}"
present_command chromium
check_guest_mode_removal >/dev/null
_t_eq "1" "${#MISSING_SCRIPTS[@]}" "a missing removal script is recorded"

echo "== check_vbox_hosts: VirtualBox absent is n/a, not a pass =="
reset_state
absent_command VBoxManage
check_vbox_hosts >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "not applicable" "an absent VirtualBox is reported as not applicable"
_t_eq "n/a" "$(get_service_status "vbox_hosts")" "the status is n/a rather than ok"

echo "== check_vbox_hosts: installed with the marker present =="
reset_state
present_command VBoxManage
sysfile var/lib/vbox-hosts-enforced
check_vbox_hosts >/dev/null
_t_eq "ok" "$(get_service_status "vbox_hosts")" "an enforced install records ok"

echo "== check_vbox_hosts: installed without the marker is repaired =="
reset_state
make_installer "$VBOX_HOSTS_SCRIPT"
present_command VBoxManage
check_vbox_hosts >/dev/null
_t_called 'ran enforce_vbox_hosts' "a missing marker runs the enforcement script"
_t_eq "1" "$FIXES_APPLIED" "the fix is counted"

echo "== check_vbox_hosts: --status and a missing script =="
reset_state
make_installer "$VBOX_HOSTS_SCRIPT"
present_command VBoxManage
STATUS_ONLY=1
check_vbox_hosts >/dev/null
_t_not_called 'ran enforce_vbox_hosts' "--status never repairs"

reset_state
rm -f "$VBOX_HOSTS_SCRIPT"
present_command VBoxManage
check_vbox_hosts >/dev/null
_t_eq "1" "${#MISSING_SCRIPTS[@]}" "a missing enforcement script is recorded"

echo "== check_workout_locker: fully healthy =="
reset_state
: >"$WORKOUT_LOCKER_SCRIPT"
printf 'user:workout-locker.service\n' >"${DEV}/enabled"
printf 'user:workout-locker.service\n' >"${DEV}/active"
check_workout_locker >/dev/null
_t_eq "ok" "$(get_service_status "workout_locker")" "an enabled and active user service records ok"
_t_called 'systemctl --user --machine=' "the user bus is queried via --machine"

echo "== check_workout_locker: enabled but inactive is only a warning =="
reset_state
: >"$WORKOUT_LOCKER_SCRIPT"
make_installer "$WORKOUT_LOCKER_INSTALL_SCRIPT"
printf 'user:workout-locker.service\n' >"${DEV}/enabled"
: >"${DEV}/active"
check_workout_locker >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "expected at login time" "an inactive service is explained, not alarmed about"
_t_eq "warning" "$(get_service_status "workout_locker")" "inactive alone is a warning"
_t_not_called 'sudo -u' "a warning does not trigger the installer"

echo "== check_workout_locker: not enabled is repaired and re-verified =="
reset_state
: >"$WORKOUT_LOCKER_SCRIPT"
make_installer "$WORKOUT_LOCKER_INSTALL_SCRIPT"
: >"${DEV}/enabled"
: >"${DEV}/active"
check_workout_locker >/dev/null
_t_called "sudo -u ${TEST_USER} bash" "the installer runs as the invoking user"
_t_eq "1" "$FIXES_APPLIED" "the fix is counted"
_t_eq "error" "$(get_service_status "workout_locker")" "a fix that does not enable the unit stays an error"

echo "== check_workout_locker: a missing screen_lock.py is an error =="
reset_state
rm -f "$WORKOUT_LOCKER_SCRIPT"
make_installer "$WORKOUT_LOCKER_INSTALL_SCRIPT"
printf 'user:workout-locker.service\n' >"${DEV}/enabled"
printf 'user:workout-locker.service\n' >"${DEV}/active"
check_workout_locker >"${TEST_TMPDIR}/out.txt"
_t_called_in "$(cat "${TEST_TMPDIR}/out.txt")" "screen_lock.py not found" "the missing script is named"
_t_called "sudo -u ${TEST_USER} bash" "it triggers a reinstall"

echo "== check_workout_locker: --status and a missing installer =="
reset_state
: >"$WORKOUT_LOCKER_SCRIPT"
make_installer "$WORKOUT_LOCKER_INSTALL_SCRIPT"
STATUS_ONLY=1
: >"${DEV}/enabled"
check_workout_locker >/dev/null
_t_not_called 'sudo -u' "--status never installs"

reset_state
: >"$WORKOUT_LOCKER_SCRIPT"
rm -f "$WORKOUT_LOCKER_INSTALL_SCRIPT"
: >"${DEV}/enabled"
check_workout_locker >/dev/null
_t_eq "1" "${#MISSING_SCRIPTS[@]}" "a missing locker installer is recorded"

_t_summary
