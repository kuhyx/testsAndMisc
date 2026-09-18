#!/bin/bash

# ============================================================================
# Logitech G29: which mode is the wheel in.
#
# Sourced by fix_g29_shifter.sh and tests/test_fix_g29_shifter.bats.
#
# The G29 has a physical PS3/PS4 selector. Only the PS3 position ends up as
# the native 046D:C24F device that hid-logitech (new-lg4ff) binds and the
# HID-BPF shifter fix targets. The PS4 position enumerates as 046D:C260:
# hid-generic, a different report layout, no kernel driver, no shifter fix.
# Nothing used to notice -- on the 2026-09-15 and 2026-09-17 boots the wheel
# came up in PS4 mode and 1st/3rd were dead all day while every layer of the
# safety net looked for C24F only. Details: ../docs/DOCS-g29-shifter.md.
# ============================================================================

[[ -n "${_G29_WHEEL_MODE_LOADED:-}" ]] && return 0
_G29_WHEEL_MODE_LOADED=1

# Overridable so tests can point at a fake sysfs tree.
G29_HID_SYSFS="${G29_HID_SYSFS:-/sys/bus/hid/devices}"
readonly G29_PID_NATIVE="0003:046D:C24F"
readonly G29_PID_PS4="0003:046D:C260"
readonly G29_PID_COMPAT="0003:046D:C294"

# Print the sysfs path of the first $1 device that has a report descriptor
# (the wheel exposes two HID interfaces; only the joystick one has one).
g29_sysfs_device() {
	local dev
	for dev in "$G29_HID_SYSFS/$1".*; do
		if [[ -s "$dev/report_descriptor" ]]; then
			echo "$dev"
			return 0
		fi
	done
	return 1
}

# Print one of: native | ps4 | compat | absent
g29_wheel_mode() {
	if g29_sysfs_device "$G29_PID_NATIVE" >/dev/null; then
		echo native
	elif g29_sysfs_device "$G29_PID_PS4" >/dev/null; then
		echo ps4
	elif g29_sysfs_device "$G29_PID_COMPAT" >/dev/null; then
		echo compat
	else
		echo absent
	fi
}

# One line a human can act on, for any non-native mode.
g29_mode_explanation() {
	case "$1" in
	ps4) echo "G29 is in PS4 mode (046D:C260): flip the PS3/PS4 selector on the wheel to PS3. The shifter fix, hid-logitech and FFB only work in PS3 mode." ;;
	compat) echo "G29 is stuck in compatibility mode (046D:C294): hid-logitech did not switch it to native. Check 'modinfo hid_logitech', then replug." ;;
	absent) echo "no G29 on the HID bus" ;;
	native) echo "G29 in native mode (046D:C24F)" ;;
	*) echo "unknown G29 mode '$1'" ;;
	esac
}
