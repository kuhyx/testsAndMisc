#!/usr/bin/env bash
# Tests for lib/bt_pairing.sh: fix_usb_autosuspend and
# _disable_usb_autosuspend, split from test_bt_pairing.sh for the 250-line cap.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bt_harness.sh
. "${SCRIPT_DIR}/bt_harness.sh"

# shellcheck source=../bt_pairing.sh
. "${FIXES_DIR}/lib/bt_pairing.sh"

# --- fix_usb_autosuspend ----------------------------------------------------
#
# This function globs the REAL /sys/bus/usb/devices/*/ -- the path is
# hardcoded, with no env override to point elsewhere. Rather than bind-mount
# or write anything, each case drives the branch it wants through the stubbed
# `lsusb` output:
#
#   * a vendor:product of ffff:ffff matches no device on any machine, so the
#     loop runs to exhaustion and takes the "could not find sysfs path" arm;
#   * a vendor:product that IS present on this host reaches the power/control
#     read, and _disable_usb_autosuspend is stubbed IN A SUBSHELL for those
#     cases so the udev rule and the sysfs write never happen.
#
# A top-level redefinition would shadow the real function for every later
# assertion, so each override is confined to its own subshell.

# _lsusb_line TEXT — stub lsusb to emit a single line of TEXT.
_lsusb_line() {
	printf '%s\n' "$1" >"${DEV}/lsusb_out"
	_t_stub_cat lsusb lsusb_out
}

# No bluetooth device in lsusb at all: the function returns before any lookup.
bt_reset
_t_stub lsusb 'echo "Bus 001 Device 002: ID 046d:c077 Logitech, Inc. Mouse"'
out="$(fix_usb_autosuspend 2>&1)"
_t_contains "$out" "Checking USB autosuspend" \
	"fix_usb_autosuspend: announces the check"
_t_eq "" "$(_t_fixes)" \
	"fix_usb_autosuspend: applies no fix when lsusb lists no bluetooth device"

# A bluetooth line with no parseable ID: the usb_id guard returns early.
bt_reset
_lsusb_line "Bus 001 Device 003: Bluetooth adapter with no id field"
out="$(fix_usb_autosuspend 2>&1)"
_t_eq "" "$(_t_fixes)" \
	"fix_usb_autosuspend: applies no fix when the bluetooth line has no ID"

# A well-formed ID that matches no real device: the sysfs scan finds nothing.
bt_reset
_lsusb_line "Bus 001 Device 004: ID ffff:ffff Bluetooth Device"
out="$(fix_usb_autosuspend 2>&1)"
_t_contains "$out" "Could not find sysfs path" \
	"fix_usb_autosuspend: warns when no sysfs device matches the USB ID"
_t_eq "" "$(_t_fixes)" \
	"fix_usb_autosuspend: applies no fix when the sysfs path is not found"

# A device whose power/control is already "on" needs no change. 046d:c077 is
# present on this host with control=on; skipped if that ever stops holding.
bt_reset
if grep -qx "on" /sys/bus/usb/devices/1-11/power/control 2>/dev/null; then
	_lsusb_line "Bus 001 Device 005: ID 046d:c077 Bluetooth Device"
	out="$(fix_usb_autosuspend 2>&1)"
	_t_contains "$out" "already disabled" \
		"fix_usb_autosuspend: reports autosuspend already disabled when control is on"
	_t_eq "" "$(_t_fixes)" \
		"fix_usb_autosuspend: applies no fix when control is already on"
else
	_t_pass "fix_usb_autosuspend: SKIP already-on case (1-11 control is not 'on' here)"
fi

# _record_disable ARGS... — stand-in for the real writer, recording only.
_record_disable() {
	printf 'disable_called %s\n' "$*" >>"${DEV}/fixes"
}

# A device whose power/control is "auto" gets the fix. _disable_usb_autosuspend
# is replaced INSIDE the subshell so this case proves the arguments handed to
# the writer without letting the real writer touch /sys or /etc; the real
# writer gets its own direct tests further down. The redefinition must stay in
# the subshell, since a top-level one would shadow the real function for every
# later assertion in this file.
bt_reset
if grep -qx "auto" /sys/bus/usb/devices/1-10/power/control 2>/dev/null; then
	_lsusb_line "Bus 001 Device 006: ID 046d:0825 Bluetooth Device"
	# _record_disable is defined at top level (so it is plainly a called
	# function) but only BOUND to the writer's name inside the subshell.
	out="$(
		eval '_disable_usb_autosuspend() { _record_disable "$@"; }'
		fix_usb_autosuspend 2>&1
	)"
	_t_contains "$out" "USB autosuspend is enabled" \
		"fix_usb_autosuspend: warns when autosuspend is enabled"
	_t_contains "$out" "Disabling USB autosuspend" \
		"fix_usb_autosuspend: applies the disable fix when control is auto"
	_t_contains "$(_t_fixes)" "disable_called /sys/bus/usb/devices/1-10/power/control 046d 0825" \
		"fix_usb_autosuspend: passes the control path, vendor and product to the writer"
else
	_t_pass "fix_usb_autosuspend: SKIP auto case (1-10 control is not 'auto' here)"
fi

# --- _disable_usb_autosuspend ----------------------------------------------
#
# Called directly, with the REAL body running. Both of its writes are
# redirected out of the way rather than stubbed:
#
#   * the sysfs power/control file is already a parameter, so a tmpdir file
#     covers it;
#   * the udev rule path is the UDEV_RULES_DIR override the lib exposes for
#     exactly this. A bind mount was rejected: run_all.sh runs UN-jailed in
#     ci_mirror.sh and in CI, so binding /etc would make the coverage run
#     safe and leave every bare run writing to the real file.
#
# udevadm is already stubbed by _bt_default_stubs.

bt_reset
control_file="${TEST_TMPDIR}/power_control"
rules_dir="${TEST_TMPDIR}/udev_rules"
rule_file="${rules_dir}/50-bluetooth-no-autosuspend.rules"
rm -rf "$rules_dir"
mkdir -p "$rules_dir"
echo "auto" >"$control_file"

out="$(UDEV_RULES_DIR="$rules_dir" \
	_disable_usb_autosuspend "$control_file" "046d" "0825" 2>&1)"

_t_eq "on" "$(cat "$control_file")" \
	"_disable_usb_autosuspend: writes 'on' to the sysfs power/control file"
_t_contains "$out" "Created persistent udev rule" \
	"_disable_usb_autosuspend: reports creating the udev rule"
_t_contains "$(cat "$rule_file")" 'ATTR{idVendor}=="046d"' \
	"_disable_usb_autosuspend: writes the vendor into the udev rule"
_t_contains "$(cat "$rule_file")" 'ATTR{idProduct}=="0825"' \
	"_disable_usb_autosuspend: writes the product into the udev rule"
_t_contains "$(cat "$rule_file")" 'ATTR{power/control}="on"' \
	"_disable_usb_autosuspend: pins power/control to on in the udev rule"
_t_contains "$(_t_calls)" "udevadm control --reload-rules" \
	"_disable_usb_autosuspend: reloads udev rules after writing"

# Second call with the rule already present for this vendor: the guard must
# skip the rewrite, so the existing file survives untouched.
bt_reset
printf '%s\n' "# pre-existing rule for 046d" >"$rule_file"
echo "auto" >"$control_file"
out="$(UDEV_RULES_DIR="$rules_dir" \
	_disable_usb_autosuspend "$control_file" "046d" "0825" 2>&1)"
_t_eq "# pre-existing rule for 046d" "$(cat "$rule_file")" \
	"_disable_usb_autosuspend: leaves an existing rule for the same vendor alone"
_t_lacks "$out" "Created persistent udev rule" \
	"_disable_usb_autosuspend: does not claim to create a rule that already existed"
_t_eq "on" "$(cat "$control_file")" \
	"_disable_usb_autosuspend: still writes power/control on the idempotent path"

# A rule file that exists but covers a DIFFERENT vendor must be rewritten.
bt_reset
printf '%s\n' "# rule for some other vendor 1234" >"$rule_file"
echo "auto" >"$control_file"
out="$(UDEV_RULES_DIR="$rules_dir" \
	_disable_usb_autosuspend "$control_file" "046d" "0825" 2>&1)"
_t_contains "$(cat "$rule_file")" 'ATTR{idVendor}=="046d"' \
	"_disable_usb_autosuspend: rewrites a rule file that covers a different vendor"

echo
echo "bt_pairing (usb autosuspend): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
