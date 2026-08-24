#!/bin/bash
# Security hardening tests: compulsive-opening block + screen locker.
# Sourced by test_security_hardening.sh; inherits its strict mode,
# colors, counters (PASS/FAIL/SKIP), LIVE_SECTION and test_result().

sec_tests_compulsive_block() {
	# ==================================================================
	# COMPULSIVE BLOCK TESTS
	# ==================================================================
	echo "--- COMPULSIVE OPENING BLOCK ---"

	compulsive_dir="$DW_REPO"
	compulsive_file="$compulsive_dir/block_compulsive_opening.sh"

	# The blocker was split into lib/cco_*.sh under the 250-line cap, so these
	# two checks search the entry script AND its libs. Grepping the entry
	# script alone made them report "not found" for code that had simply moved
	# one file over — a false failure that says nothing about the feature.
	# Searching the set keeps the assertion about the FEATURE existing, which
	# is what it was always for, and survives the next split too.
	compulsive_sources=("$compulsive_file")
	for compulsive_lib in "$compulsive_dir"/lib/cco_*.sh; do
		[[ -f "$compulsive_lib" ]] && compulsive_sources+=("$compulsive_lib")
	done

	# Test 17: Auto-close timer configuration exists
	if [[ -f "$compulsive_file" ]]; then
		if grep -qs "AUTO_CLOSE_TIMEOUT_MINUTES" "${compulsive_sources[@]}"; then
			test_result "Auto-close timer configuration exists" "pass"
		else
			test_result "Auto-close timer configuration exists" "fail" "Variable not found"
		fi
	else
		test_result "Auto-close timer configuration exists" "skip" "Script not found"
	fi

	# Test 18: launch_with_timer function exists
	if [[ -f "$compulsive_file" ]]; then
		if grep -qs "launch_with_timer" "${compulsive_sources[@]}"; then
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

	# screen_locker was EXTRACTED to github.com/kuhyx/screen-locker. This used
	# to hardcode $HOME/testsAndMisc/python_pkg/screen_locker/, which stopped
	# existing -- so all five checks below silently SKIPPED, reporting a clean
	# run for tests that never executed. $HOME is also wrong under sudo; use the
	# shared resolver, which handles the sudo/systemd cases.
	local sl_repo sl_manual sl_types sl_fields
	sl_repo="$(extracted_repo_dir screen-locker)"
	screen_locker="$sl_repo/screen_locker/screen_lock.py"
	sl_manual="$sl_repo/screen_locker/_manual_workout.py"
	sl_types="$sl_repo/screen_locker/_manual_workout_types.py"
	sl_fields="$sl_repo/screen_locker/_manual_workout_sport_fields.py"

	# Test 20: Screen locker exists
	if [[ -f "$screen_locker" ]]; then
		test_result "Screen locker script exists" "pass"
	else
		test_result "Screen locker script exists" "skip" "Not found at $screen_locker"
	fi

	# Test 21: Running option removed.
	# The workout prompt was rewritten: the sport list is now the explicit
	# SPORT_CHOICES tuple in _manual_workout_types.py, so "Running is absent"
	# is asserted against that tuple rather than against a since-deleted
	# ask_workout_type function.
	if [[ -f "$sl_types" ]]; then
		if grep -A 4 "^SPORT_CHOICES" "$sl_types" | grep -qi "running"; then
			test_result "Running workout option removed" "fail" "Still present in SPORT_CHOICES"
		else
			test_result "Running workout option removed" "pass"
		fi
	else
		test_result "Running workout option removed" "skip" "Types module not found"
	fi

	# Test 22: Table tennis is a distinct, validated sport.
	if [[ -f "$sl_types" ]] && [[ -f "$sl_manual" ]]; then
		if grep -q "^SPORT_TABLE_TENNIS" "$sl_types" &&
			grep -q "_validate_table_tennis" "$sl_manual"; then
			test_result "Table tennis validation exists" "pass"
		else
			test_result "Table tennis validation exists" "fail" "Sport constant or validator missing"
		fi
	else
		test_result "Table tennis validation exists" "skip" "Manual-workout modules not found"
	fi

	# Test 23: Sets won/lost are captured and validated for table tennis.
	if [[ -f "$sl_fields" ]] && [[ -f "$sl_manual" ]]; then
		if grep -q "sets_won" "$sl_fields" && grep -q "Sets won" "$sl_manual"; then
			test_result "Table tennis set scores captured" "pass"
		else
			test_result "Table tennis set scores captured" "fail" "sets_won field or validation missing"
		fi
	else
		test_result "Table tennis set scores captured" "skip" "Sport-field modules not found"
	fi

	# Test 24: The reflection fields are enforced with a minimum length, which
	# is what makes a logged workout non-trivial to fake.
	if [[ -f "$sl_manual" ]]; then
		if grep -q "MANUAL_WORKOUT_REFLECTION_MIN_CHARS" "$sl_manual"; then
			test_result "Manual workout reflection minimum enforced" "pass"
		else
			test_result "Manual workout reflection minimum enforced" "fail" "Minimum not enforced"
		fi
	else
		test_result "Manual workout reflection minimum enforced" "skip" "Manual-workout module not found"
	fi

	echo ""

}
