#!/bin/bash
# Security hardening tests: compulsive-opening block + screen locker.
# Sourced by test_security_hardening.sh; inherits its strict mode,
# colors, counters (PASS/FAIL/SKIP), LIVE_SECTION and test_result().

sec_tests_compulsive_block() {
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

}

sec_tests_screen_locker() {
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

}
