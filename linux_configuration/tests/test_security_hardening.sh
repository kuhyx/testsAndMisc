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

# Setter for LIVE_SECTION. The section libs are linted in isolation, where a
# bare `LIVE_SECTION=1` looks like an unused variable (SC2034) because its only
# reader — test_result, above — lives in this file. Going through a function
# makes the write a real reference instead of needing a suppression.
live_section() {
	LIVE_SECTION="$1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Security Hardening Test Suite"
echo "=========================================="
echo ""
echo "Testing components in: $REPO_DIR"
echo ""

# The test sections live in libs to keep this file under the 250-line cap.
# They are functions, but they mutate this script's counters and LIVE_SECTION
# exactly as the former top-level blocks did — sourcing shares the shell.
LIB_DIR="$SCRIPT_DIR/lib"
# shellcheck source=lib/security_hosts_shutdown.sh
source "$LIB_DIR/security_hosts_shutdown.sh"
# shellcheck source=lib/security_pacman.sh
source "$LIB_DIR/security_pacman.sh"
# shellcheck source=lib/security_apps.sh
source "$LIB_DIR/security_apps.sh"

# Order matters: it is the order the sections ran in before the split.
sec_tests_hosts_guard
sec_tests_shutdown_schedule
sec_tests_pacman_wrapper
sec_tests_compulsive_block
sec_tests_screen_locker

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
