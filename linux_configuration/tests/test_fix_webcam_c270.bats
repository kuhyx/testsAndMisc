#!/usr/bin/env bats
# Tests for fixes/fix_webcam_c270.sh against a fake sysfs tree and stubbed
# sudo/v4l2-ctl/pacman, so nothing touches /etc or a real camera.
#
# Requires: bats (extra/bats). Run with:
#   bats linux_configuration/tests/test_fix_webcam_c270.bats

bats_require_minimum_version 1.5.0

setup() {
	REPO_DIR="$(cd -- "$(dirname -- "$BATS_TEST_FILENAME")/.." && pwd)"
	SCRIPT="$REPO_DIR/fixes/fix_webcam_c270.sh"
	export C270_V4L_SYSFS="$BATS_TEST_TMPDIR/v4l"
	mkdir -p "$C270_V4L_SYSFS" "$BATS_TEST_TMPDIR/bin"
	export CALLS="$BATS_TEST_TMPDIR/calls"
	# One recording stub, linked under each tool name it stands in for.
	cat >"$BATS_TEST_TMPDIR/bin/stub" <<'STUB'
#!/bin/bash
echo "$(basename "$0") $*" >>"$CALLS"
STUB
	chmod +x "$BATS_TEST_TMPDIR/bin/stub"
	local tool
	for tool in sudo v4l2-ctl pacman; do
		ln -s stub "$BATS_TEST_TMPDIR/bin/$tool"
	done
	export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
}

# $1 = node name, $2 = index, $3 = vendor, $4 = product
fake_node() {
	local usb="$BATS_TEST_TMPDIR/usb-$1"
	mkdir -p "$usb/intf" "$C270_V4L_SYSFS/$1"
	echo "$3" >"$usb/idVendor"
	echo "$4" >"$usb/idProduct"
	echo "$2" >"$C270_V4L_SYSFS/$1/index"
	ln -s "$usb/intf" "$C270_V4L_SYSFS/$1/device"
}

@test "install without a camera installs the rule and skips v4l2-ctl" {
	run "$SCRIPT"
	[ "$status" -eq 0 ]
	[[ "$output" == *"not plugged in"* ]]
	grep -q "sudo install -m 644 .*99-c270-fixed-framerate.rules /etc/udev/rules.d/" "$CALLS"
	run ! grep -q "^v4l2-ctl" "$CALLS"
}

@test "install applies to the C270 capture node, not its metadata node or other cams" {
	fake_node video0 0 046d 0999
	fake_node video2 1 046d 0825
	fake_node video3 0 046d 0825
	run "$SCRIPT"
	[ "$status" -eq 0 ]
	grep -qx "v4l2-ctl -d /dev/video3 -c exposure_dynamic_framerate=0" "$CALLS"
	[ "$(grep -c '^v4l2-ctl' "$CALLS")" -eq 1 ]
}

@test "--remove deletes the rule and reloads udev" {
	run "$SCRIPT" --remove
	[ "$status" -eq 0 ]
	grep -qx "sudo rm -f /etc/udev/rules.d/99-c270-fixed-framerate.rules" "$CALLS"
	grep -qx "sudo udevadm control --reload" "$CALLS"
}

@test "--status reports the live control" {
	fake_node video0 0 046d 0825
	run "$SCRIPT" --status
	[ "$status" -eq 0 ]
	grep -qx "v4l2-ctl -d /dev/video0 -C exposure_dynamic_framerate" "$CALLS"
}

@test "unknown option exits 2" {
	run "$SCRIPT" --bogus
	[ "$status" -eq 2 ]
}
