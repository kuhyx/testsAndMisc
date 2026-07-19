#!/bin/bash
# tests/test_security_hardening.sh
# Verify all security mechanisms are working
#
# Run with: bash tests/test_security_hardening.sh
# Some tests require root privileges

set -uo pipefail
# Note: NOT using -e because we need to handle test failures gracefully

PASS=0
FAIL=0
SKIP=0

# Roughly half this suite inspects a *configured machine* (chattr flags, systemd
# guard units, /usr/local payloads) rather than the repository. Those checks
# cannot pass in CI or a container, where none of it is installed — but the
# repo-file checks further down can and should still run. So live checks are
# reported as skipped off-host instead of failed, which keeps the suite
# meaningful in both places rather than permanently red in one.
# Detection must not consult `systemctl is-system-running`: it exits non-zero
# when the system is *degraded*, which is exactly the state a failed guard unit
# produces. Using it would make this suite skip the very failures it exists to
# catch. Test instead for systemd being init plus the guard payload being
# installed — both true on a configured host regardless of unit health.
IS_CONFIGURED_HOST=0
if [[ -d /run/systemd/system ]] && [[ -d /usr/local/share/hosts-guard ]]; then
	IS_CONFIGURED_HOST=1
fi
# Set to 1 while inside the live-host sections, 0 for repository checks.
LIVE_SECTION=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_result() {
	local name="$1"
	local result="$2"
	local reason="${3:-}"

	case "$result" in
	pass)
		echo -e "${GREEN}✅ PASS${NC}: $name"
		((PASS++))
		;;
	fail)
		if ((LIVE_SECTION == 1)) && ((IS_CONFIGURED_HOST == 0)); then
			# Off-host: the mechanism being absent is expected, not a defect.
			echo -e "${YELLOW}⏭️  SKIP${NC}: $name"
			echo -e "         ${YELLOW}Reason: not a configured host (CI/container)${NC}"
			((SKIP++))
			return
		fi
		echo -e "${RED}❌ FAIL${NC}: $name"
		[[ -n "$reason" ]] && echo -e "         ${RED}Reason: $reason${NC}"
		((FAIL++))
		;;
	skip)
		echo -e "${YELLOW}⏭️  SKIP${NC}: $name"
		[[ -n "$reason" ]] && echo -e "         ${YELLOW}Reason: $reason${NC}"
		((SKIP++))
		;;
	esac
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Security Hardening Test Suite"
echo "=========================================="
echo ""
echo "Testing components in: $REPO_DIR"
echo ""

# ==================================================================
# HOSTS GUARD TESTS
# ==================================================================
LIVE_SECTION=1  # live-host checks begin
echo "--- HOSTS GUARD ---"

# Test 1: /etc/hosts is immutable
if [[ -f /etc/hosts ]]; then
	if lsattr /etc/hosts 2>/dev/null | grep -q '^....i'; then
		test_result "/etc/hosts is immutable" "pass"
	else
		test_result "/etc/hosts is immutable" "fail" "chattr +i not set"
	fi
else
	test_result "/etc/hosts is immutable" "skip" "File not found"
fi

# Test 2: the hosts file watcher is active
# The 2026-07-17 guard-lib refactor replaced the standalone hosts-guard.path
# with the templated guard-file@hosts.path. Accept either, so this passes on a
# migrated host and on one still running the legacy unit. Checking only the old
# name reported the protection as down when it was simply renamed.
if systemctl is-active --quiet guard-file@hosts.path 2>/dev/null ||
	systemctl is-active --quiet hosts-guard.path 2>/dev/null; then
	test_result "hosts file watcher is active" "pass"
else
	test_result "hosts file watcher is active" "fail" \
		"neither guard-file@hosts.path nor hosts-guard.path is running"
fi

# Test 3: /etc/hosts is bind-mounted read-only
# guard-bind-mount@hosts.service superseded hosts-bind-mount.service. The mount
# itself is the thing that matters, so check that too — it is the real
# invariant, independent of which unit established it.
if systemctl is-active --quiet guard-bind-mount@hosts.service 2>/dev/null ||
	systemctl is-active --quiet hosts-bind-mount.service 2>/dev/null ||
	findmnt -no OPTIONS /etc/hosts 2>/dev/null | grep -q '\bro\b'; then
	test_result "/etc/hosts bind-mounted read-only" "pass"
else
	test_result "/etc/hosts bind-mounted read-only" "fail" \
		"no bind-mount unit active and /etc/hosts is not mounted read-only"
fi

# Test 4: Canonical hosts copy exists
if [[ -f /usr/local/share/locked-hosts ]]; then
	test_result "Canonical hosts copy exists" "pass"
else
	test_result "Canonical hosts copy exists" "fail" "Not found at /usr/local/share/locked-hosts"
fi

# Test 5: the nsswitch watcher is active
# guard-file@nsswitch.path superseded nsswitch-guard.path. The legacy unit is
# left in a failed state on migrated hosts (it and the new watcher both
# enforced the same file, so it retriggered itself into systemd's start
# limit) — that is obsolete-unit noise, not a lapse in protection.
if systemctl is-active --quiet guard-file@nsswitch.path 2>/dev/null ||
	systemctl is-active --quiet nsswitch-guard.path 2>/dev/null; then
	test_result "nsswitch watcher is active" "pass"
else
	test_result "nsswitch watcher is active" "fail" \
		"neither guard-file@nsswitch.path nor nsswitch-guard.path is running"
fi

# Test 6: /etc/nsswitch.conf is immutable (NEW)
if [[ -f /etc/nsswitch.conf ]]; then
	if lsattr /etc/nsswitch.conf 2>/dev/null | grep -q '^....i'; then
		test_result "/etc/nsswitch.conf is immutable" "pass"
	else
		test_result "/etc/nsswitch.conf is immutable" "fail" "chattr +i not set"
	fi
else
	test_result "/etc/nsswitch.conf is immutable" "skip" "File not found"
fi

# Test 7: nsswitch.conf has correct hosts line
if [[ -f /etc/nsswitch.conf ]]; then
	hosts_line=$(grep "^hosts:" /etc/nsswitch.conf 2>/dev/null || true)
	if echo "$hosts_line" | grep -q 'files.*dns\|files.*myhostname'; then
		test_result "nsswitch.conf has 'files' before 'dns'" "pass"
	elif [[ -z "$hosts_line" ]]; then
		test_result "nsswitch.conf has 'files' before 'dns'" "fail" "No hosts: line found"
	else
		test_result "nsswitch.conf has 'files' before 'dns'" "fail" "hosts line: $hosts_line"
	fi
else
	test_result "nsswitch.conf has 'files' before 'dns'" "skip" "File not found"
fi

echo ""

# ==================================================================
# SHUTDOWN SCHEDULE TESTS
# ==================================================================
echo "--- SHUTDOWN SCHEDULE ---"

# Test 8: shutdown-schedule.conf is immutable
if [[ -f /etc/shutdown-schedule.conf ]]; then
	if lsattr /etc/shutdown-schedule.conf 2>/dev/null | grep -q '^....i'; then
		test_result "/etc/shutdown-schedule.conf is immutable" "pass"
	else
		test_result "/etc/shutdown-schedule.conf is immutable" "fail" "chattr +i not set"
	fi
else
	test_result "/etc/shutdown-schedule.conf is immutable" "skip" "Not installed"
fi

# Test 9: shutdown timer is active
if systemctl is-active --quiet day-specific-shutdown.timer 2>/dev/null; then
	test_result "day-specific-shutdown.timer is active" "pass"
else
	test_result "day-specific-shutdown.timer is active" "fail" "Timer not running"
fi

# Test 10: shutdown schedule guard
# The shutdown flow no longer powers the machine off — day-specific-shutdown
# now hands over to night-lockdown-enter.sh, which tears down the GUI and masks
# the TTY login while leaving the servers up. This guard was retired with the
# old poweroff path, so a *disabled* unit is the intended state, not a fault.
# An enabled-but-inactive unit would still mean something is wrong, so those
# two cases are distinguished rather than both being tolerated.
# `systemctl is-enabled` prints the state on stdout *and* exits non-zero when
# that state is "disabled", so `|| echo disabled` would append a second line
# and never compare equal. Capture stdout and discard the exit status instead.
shutdown_guard_enabled=$(systemctl is-enabled shutdown-schedule-guard.path 2>/dev/null || true)
[[ -n "$shutdown_guard_enabled" ]] || shutdown_guard_enabled=unknown
if systemctl is-active --quiet guard-file@shutdown-schedule.path 2>/dev/null ||
	systemctl is-active --quiet shutdown-schedule-guard.path 2>/dev/null; then
	# guard-file@shutdown-schedule.path is the guard-lib replacement and is the
	# unit actually protecting the schedule today, so this is a pass, not a
	# concession that the schedule went unguarded.
	test_result "shutdown schedule is guarded" "pass"
elif [[ "$shutdown_guard_enabled" == "disabled" ]]; then
	test_result "shutdown-schedule-guard.path is active" "skip" \
		"intentionally retired with the old poweroff flow (night lockdown replaced it)"
else
	test_result "shutdown-schedule-guard.path is active" "fail" \
		"unit is $shutdown_guard_enabled but not running"
fi

# Test 11: Unlock script has obscure name (no helpful path)
if [[ -f /usr/local/sbin/.sd-sched-mgmt ]]; then
	test_result "Unlock script uses obscure name" "pass"
elif [[ -f /usr/local/sbin/unlock-shutdown-schedule ]]; then
	test_result "Unlock script uses obscure name" "fail" "Still using obvious name"
else
	test_result "Unlock script uses obscure name" "skip" "Not installed"
fi

echo ""

# ==================================================================
# PACMAN WRAPPER TESTS
# ==================================================================
echo "--- PACMAN WRAPPER ---"

# Test 12: pacman wrapper is installed
if [[ -L /usr/bin/pacman ]] && [[ -f /usr/bin/pacman.orig ]]; then
	test_result "pacman wrapper installed" "pass"
else
	if [[ ! -L /usr/bin/pacman ]]; then
		test_result "pacman wrapper installed" "fail" "/usr/bin/pacman is not a symlink"
	else
		test_result "pacman wrapper installed" "fail" "/usr/bin/pacman.orig not found"
	fi
fi

LIVE_SECTION=0  # repository checks from here on

# Test 13: google-chrome is blocked
blocked_file="$REPO_DIR/scripts/periodic_background/digital_wellbeing/pacman/pacman_blocked_keywords.txt"
if [[ -f "$blocked_file" ]]; then
	if grep -qi "google-chrome" "$blocked_file"; then
		test_result "google-chrome in blocked list" "pass"
	else
		test_result "google-chrome in blocked list" "fail" "Not found in $blocked_file"
	fi
else
	test_result "google-chrome in blocked list" "skip" "Blocked keywords file not found"
fi

# Test 14: chromium is blocked
if [[ -f "$blocked_file" ]]; then
	if grep -qi "^chromium$" "$blocked_file"; then
		test_result "chromium in blocked list" "pass"
	else
		test_result "chromium in blocked list" "fail" "Not found in $blocked_file"
	fi
else
	test_result "chromium in blocked list" "skip" "Blocked keywords file not found"
fi

# Test 15: Policy integrity file exists
# Lives under /var on the configured host, so it is a live check despite
# sitting among the repository ones.
LIVE_SECTION=1
if [[ -f /var/lib/pacman-wrapper/policy.sha256 ]]; then
	test_result "Pacman policy integrity file exists" "pass"
else
	test_result "Pacman policy integrity file exists" "fail" "Not found"
fi
LIVE_SECTION=0

# Test 16: LeechBlock auto-install function exists in wrapper
wrapper_file="$REPO_DIR/scripts/periodic_background/digital_wellbeing/pacman/pacman_wrapper.sh"
if [[ -f "$wrapper_file" ]]; then
	if grep -q "auto_install_leechblock" "$wrapper_file"; then
		test_result "LeechBlock auto-install function exists" "pass"
	else
		test_result "LeechBlock auto-install function exists" "fail" "Function not found"
	fi
else
	test_result "LeechBlock auto-install function exists" "skip" "Wrapper file not found"
fi

echo ""

# ==================================================================
# COMPULSIVE BLOCK TESTS
# ==================================================================
echo "--- COMPULSIVE OPENING BLOCK ---"

compulsive_file="$REPO_DIR/scripts/periodic_background/digital_wellbeing/block_compulsive_opening.sh"

# Test 17: Auto-close timer configuration exists
if [[ -f "$compulsive_file" ]]; then
	if grep -q "AUTO_CLOSE_TIMEOUT_MINUTES" "$compulsive_file"; then
		test_result "Auto-close timer configuration exists" "pass"
	else
		test_result "Auto-close timer configuration exists" "fail" "Variable not found"
	fi
else
	test_result "Auto-close timer configuration exists" "skip" "Script not found"
fi

# Test 18: launch_with_timer function exists
if [[ -f "$compulsive_file" ]]; then
	if grep -q "launch_with_timer" "$compulsive_file"; then
		test_result "launch_with_timer function exists" "pass"
	else
		test_result "launch_with_timer function exists" "fail" "Function not found"
	fi
else
	test_result "launch_with_timer function exists" "skip" "Script not found"
fi

# Test 19: Compulsive block wrappers installed
wrappers_ok=true
for app in beeper signal-desktop discord; do
	if [[ -f "/usr/bin/$app" ]]; then
		if grep -q "block-compulsive-opening" "/usr/bin/$app" 2>/dev/null; then
			: # OK
		else
			wrappers_ok=false
		fi
	fi
done
if [[ "$wrappers_ok" == true ]]; then
	test_result "Compulsive block wrappers installed" "pass"
else
	test_result "Compulsive block wrappers installed" "fail" "Some wrappers missing or incorrect"
fi

echo ""

# ==================================================================
# SCREEN LOCKER TESTS
# ==================================================================
echo "--- SCREEN LOCKER ---"

screen_locker="$HOME/testsAndMisc/python_pkg/screen_locker/screen_lock.py"

# Test 20: Screen locker exists
if [[ -f "$screen_locker" ]]; then
	test_result "Screen locker script exists" "pass"
else
	test_result "Screen locker script exists" "skip" "Not found at expected location"
fi

# Test 21: Running option removed
if [[ -f "$screen_locker" ]]; then
	# Check that there's no "Running" button in ask_workout_type
	if grep -A 20 "def ask_workout_type" "$screen_locker" | grep -q '"Running"'; then
		test_result "Running workout option removed" "fail" "Still present in ask_workout_type"
	else
		test_result "Running workout option removed" "pass"
	fi
else
	test_result "Running workout option removed" "skip" "Script not found"
fi

# Test 22: Table tennis minimum sets validation
if [[ -f "$screen_locker" ]]; then
	if grep -q "MIN_TABLE_TENNIS_SETS" "$screen_locker"; then
		test_result "Table tennis minimum sets validation exists" "pass"
	else
		test_result "Table tennis minimum sets validation exists" "fail" "Constant not found"
	fi
else
	test_result "Table tennis minimum sets validation exists" "skip" "Script not found"
fi

# Test 23: Table tennis verification question
if [[ -f "$screen_locker" ]]; then
	if grep -q "ask_table_tennis_verification" "$screen_locker"; then
		test_result "Table tennis verification question exists" "pass"
	else
		test_result "Table tennis verification question exists" "fail" "Function not found"
	fi
else
	test_result "Table tennis verification question exists" "skip" "Script not found"
fi

# Test 24: 60 second submit delay for table tennis
if [[ -f "$screen_locker" ]]; then
	if grep -q "TABLE_TENNIS_SUBMIT_DELAY = 60" "$screen_locker"; then
		test_result "Table tennis 60-second submit delay" "pass"
	else
		test_result "Table tennis 60-second submit delay" "fail" "Constant not set to 60"
	fi
else
	test_result "Table tennis 60-second submit delay" "skip" "Script not found"
fi

echo ""

# ==================================================================
# SUMMARY
# ==================================================================
echo "=========================================="
echo "RESULTS SUMMARY"
echo "=========================================="
echo ""
echo -e "${GREEN}Passed:  $PASS${NC}"
echo -e "${RED}Failed:  $FAIL${NC}"
echo -e "${YELLOW}Skipped: $SKIP${NC}"
echo ""
echo "=========================================="

if [[ $FAIL -gt 0 ]]; then
	echo -e "${RED}Some tests failed! Review the output above.${NC}"
	exit 1
else
	echo -e "${GREEN}All active tests passed!${NC}"
	exit 0
fi
