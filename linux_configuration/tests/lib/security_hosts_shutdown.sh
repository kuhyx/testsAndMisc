#!/bin/bash
# Security hardening tests: hosts guard + shutdown schedule.
# Sourced by test_security_hardening.sh; inherits its strict mode,
# colors, counters (PASS/FAIL/SKIP), LIVE_SECTION and test_result().

sec_tests_hosts_guard() {
	# ==================================================================
	# HOSTS GUARD TESTS
	# ==================================================================
	live_section 1 # live-host checks begin
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

}

sec_tests_shutdown_schedule() {
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

}
