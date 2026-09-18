#!/usr/bin/env bats
# Tests for fixes/g29_wheel_mode.sh and the --ensure / --status paths of
# fixes/fix_g29_shifter.sh, against a fake sysfs tree.
#
# Requires: bats (extra/bats). Run with:
#   bats linux_configuration/tests/test_fix_g29_shifter.bats
#
# The BPF build/attach itself needs the real wheel and root, so it is not
# covered here. What IS covered is the logic that failed silently on the
# 2026-09-15 and 2026-09-17 boots: telling "wheel in PS4 mode" apart from
# "no wheel", and turning that into an exit code plus a desktop notification.

setup() {
	REPO_DIR="$(cd -- "$(dirname -- "$BATS_TEST_FILENAME")/.." && pwd)"
	SCRIPT="$REPO_DIR/fixes/fix_g29_shifter.sh"
	export G29_HID_SYSFS="$BATS_TEST_TMPDIR/hid"
	export G29_RUN_USER_DIR="$BATS_TEST_TMPDIR/run"
	mkdir -p "$G29_HID_SYSFS" "$G29_RUN_USER_DIR"
	# sudo stub: records every invocation, never attached, never fails.
	STUB_LOG="$BATS_TEST_TMPDIR/sudo.log"
	export STUB_LOG
	mkdir -p "$BATS_TEST_TMPDIR/bin"
	cat >"$BATS_TEST_TMPDIR/bin/sudo" <<'STUB'
#!/bin/bash
echo "$*" >>"$STUB_LOG"
STUB
	chmod +x "$BATS_TEST_TMPDIR/bin/sudo"
	export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
	# shellcheck source=/dev/null
	source "$REPO_DIR/fixes/g29_wheel_mode.sh"
}

# $1 = PID (e.g. 0003:046D:C24F), $2 = instance, $3 = "desc" to give it a
# report descriptor. The wheel enumerates two interfaces; only one has one.
fake_hid() {
	local dir="$G29_HID_SYSFS/$1.$2"
	mkdir -p "$dir"
	if [[ "${3:-}" == desc ]]; then
		printf 'x' >"$dir/report_descriptor"
	else
		: >"$dir/report_descriptor"
	fi
}

# --- g29_wheel_mode --------------------------------------------------------

@test "mode: empty sysfs is absent" {
	[ "$(g29_wheel_mode)" = absent ]
}

@test "mode: native C24F with a descriptor" {
	fake_hid 0003:046D:C24F 0008
	fake_hid 0003:046D:C24F 0009 desc
	[ "$(g29_wheel_mode)" = native ]
	[ "$(g29_sysfs_device "$G29_PID_NATIVE")" = "$G29_HID_SYSFS/0003:046D:C24F.0009" ]
}

@test "mode: an interface with an empty descriptor does not count" {
	fake_hid 0003:046D:C24F 0001
	[ "$(g29_wheel_mode)" = absent ]
}

@test "mode: C260 is ps4 (the 2026-09-17 boot)" {
	fake_hid 0003:046D:C260 0001 desc
	[ "$(g29_wheel_mode)" = ps4 ]
}

@test "mode: C294 is compat" {
	fake_hid 0003:046D:C294 0008 desc
	[ "$(g29_wheel_mode)" = compat ]
}

@test "mode: native wins when a stale C294 node is also present" {
	fake_hid 0003:046D:C294 0008 desc
	fake_hid 0003:046D:C24F 0009 desc
	[ "$(g29_wheel_mode)" = native ]
}

@test "explanation: ps4 names the selector and the PID" {
	run g29_mode_explanation ps4
	[[ "$output" == *"PS4 mode"* && "$output" == *"C260"* && "$output" == *"PS3"* ]]
}

# --- g29_notify_desktop ----------------------------------------------------

@test "notify: reaches every user with a session bus, via sudo -u" {
	mkdir -p "$G29_RUN_USER_DIR/$(id -u)"
	: >"$G29_RUN_USER_DIR/$(id -u)/bus"
	g29_notify_desktop "title" "body"
	grep -q -- "-u $(id -nu) DBUS_SESSION_BUS_ADDRESS=unix:path=$G29_RUN_USER_DIR/$(id -u)/bus notify-send -u critical -r $G29_NOTIFY_ID" "$STUB_LOG"
}

@test "notify: no session bus means no call and no error" {
	g29_notify_desktop "title" "body"
	[ ! -e "$STUB_LOG" ]
}

# --- fix_g29_shifter.sh --ensure / --status --------------------------------

@test "ensure: no wheel exits 0 without notifying" {
	run "$SCRIPT" --ensure
	[ "$status" -eq 0 ]
	[[ "$output" == *"no G29 on the HID bus"* ]]
	run ! grep -q notify-send "$STUB_LOG"
}

@test "ensure: PS4 mode exits 1 and notifies the desktop" {
	fake_hid 0003:046D:C260 0001 desc
	mkdir -p "$G29_RUN_USER_DIR/$(id -u)"
	: >"$G29_RUN_USER_DIR/$(id -u)/bus"
	run "$SCRIPT" --ensure
	[ "$status" -eq 1 ]
	[[ "$output" == *"PS4 mode"* ]]
	grep -q "notify-send -u critical .*G29 shifter fix NOT active" "$STUB_LOG"
}

@test "ensure: already attached is a no-op even in PS4 mode" {
	fake_hid 0003:046D:C260 0001 desc
	cat >"$BATS_TEST_TMPDIR/bin/sudo" <<'STUB'
#!/bin/bash
[[ "$*" == *list-loaded* ]] && echo g29_shifter_bpf
STUB
	run "$SCRIPT" --ensure
	[ "$status" -eq 0 ]
	[[ "$output" == *"already attached"* ]]
}

@test "status: reports the wheel mode first" {
	fake_hid 0003:046D:C260 0001 desc
	run "$SCRIPT" --status
	[ "$status" -eq 0 ]
	[[ "$output" == *"wheel mode: ps4"* ]]
	[[ "$output" != *"device:"* ]]
}
