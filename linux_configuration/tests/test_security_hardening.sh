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

# Test 2: hosts-guard.path is active
if systemctl is-active --quiet hosts-guard.path 2>/dev/null; then
	test_result "hosts-guard.path is active" "pass"
else
	test_result "hosts-guard.path is active" "fail" "Service not running"
fi

# Test 3: hosts-bind-mount.service is active
if systemctl is-active --quiet hosts-bind-mount.service 2>/dev/null; then
	test_result "hosts-bind-mount.service is active" "pass"
else
	test_result "hosts-bind-mount.service is active" "fail" "Service not running"
fi

# Test 4: Canonical hosts copy exists
if [[ -f /usr/local/share/locked-hosts ]]; then
	test_result "Canonical hosts copy exists" "pass"
else
	test_result "Canonical hosts copy exists" "fail" "Not found at /usr/local/share/locked-hosts"
fi

# Test 5: nsswitch-guard.path is active (NEW)
if systemctl is-active --quiet nsswitch-guard.path 2>/dev/null; then
	test_result "nsswitch-guard.path is active" "pass"
else
	test_result "nsswitch-guard.path is active" "fail" "Service not running"
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

# Test 10: shutdown schedule guard is active
if systemctl is-active --quiet shutdown-schedule-guard.path 2>/dev/null; then
	test_result "shutdown-schedule-guard.path is active" "pass"
else
	test_result "shutdown-schedule-guard.path is active" "fail" "Guard not running"
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

# Test 13: google-chrome is blocked
blocked_file="$REPO_DIR/scripts/digital_wellbeing/pacman/pacman_blocked_keywords.txt"
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
if [[ -f /var/lib/pacman-wrapper/policy.sha256 ]]; then
	test_result "Pacman policy integrity file exists" "pass"
else
	test_result "Pacman policy integrity file exists" "fail" "Not found"
fi

# Test 16: LeechBlock auto-install function exists in wrapper
wrapper_file="$REPO_DIR/scripts/digital_wellbeing/pacman/pacman_wrapper.sh"
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

compulsive_file="$REPO_DIR/scripts/digital_wellbeing/block_compulsive_opening.sh"

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
# FOCUS MODE DAEMON TESTS
# ==================================================================
echo "--- FOCUS MODE DAEMON ---"

focus_daemon="$REPO_DIR/scripts/digital_wellbeing/focus_mode_daemon.py"
focus_installer="$REPO_DIR/scripts/digital_wellbeing/install_focus_mode_daemon.sh"

# Test 20: Focus mode daemon script exists
if [[ -f "$focus_daemon" ]]; then
	test_result "Focus mode daemon script exists" "pass"
else
	test_result "Focus mode daemon script exists" "fail" "Not found at $focus_daemon"
fi

# Test 21: Focus mode installer exists
if [[ -f "$focus_installer" ]]; then
	test_result "Focus mode installer exists" "pass"
else
	test_result "Focus mode installer exists" "fail" "Not found at $focus_installer"
fi

# Test 22: Focus mode daemon is running (user service)
if systemctl --user is-active --quiet focus-mode.service 2>/dev/null; then
	test_result "Focus mode daemon is running" "pass"
else
	test_result "Focus mode daemon is running" "fail" "User service not running"
fi

echo ""

# ==================================================================
# SCREEN LOCKER TESTS
# ==================================================================
echo "--- SCREEN LOCKER ---"

screen_locker="$HOME/testsAndMisc/python_pkg/screen_locker/screen_lock.py"

# Test 23: Screen locker exists
if [[ -f "$screen_locker" ]]; then
	test_result "Screen locker script exists" "pass"
else
	test_result "Screen locker script exists" "skip" "Not found at expected location"
fi

# Test 24: Running option removed
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

# Test 25: Table tennis minimum sets validation
if [[ -f "$screen_locker" ]]; then
	if grep -q "MIN_TABLE_TENNIS_SETS" "$screen_locker"; then
		test_result "Table tennis minimum sets validation exists" "pass"
	else
		test_result "Table tennis minimum sets validation exists" "fail" "Constant not found"
	fi
else
	test_result "Table tennis minimum sets validation exists" "skip" "Script not found"
fi

# Test 26: Table tennis verification question
if [[ -f "$screen_locker" ]]; then
	if grep -q "ask_table_tennis_verification" "$screen_locker"; then
		test_result "Table tennis verification question exists" "pass"
	else
		test_result "Table tennis verification question exists" "fail" "Function not found"
	fi
else
	test_result "Table tennis verification question exists" "skip" "Script not found"
fi

# Test 27: 60 second submit delay for table tennis
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
