#!/bin/bash
# Security hardening tests: pacman wrapper and its policy files.
# Sourced by test_security_hardening.sh; inherits its strict mode,
# colors, counters (PASS/FAIL/SKIP), LIVE_SECTION and test_result().

sec_tests_pacman_wrapper() {
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

	live_section 0 # repository checks from here on

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
	live_section 1
	if [[ -f /var/lib/pacman-wrapper/policy.sha256 ]]; then
		test_result "Pacman policy integrity file exists" "pass"
	else
		test_result "Pacman policy integrity file exists" "fail" "Not found"
	fi
	live_section 0

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

}
