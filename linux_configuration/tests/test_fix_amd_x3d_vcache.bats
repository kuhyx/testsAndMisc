#!/usr/bin/env bats
# Tests for fixes/fix_amd_x3d_vcache.sh against a fake driver sysfs tree and
# stubbed sudo/udevadm, so nothing touches /etc or the real X3D driver.
#
# Requires: bats (extra/bats). Run with:
#   bats linux_configuration/tests/test_fix_amd_x3d_vcache.bats

bats_require_minimum_version 1.5.0

setup() {
	REPO_DIR="$(cd -- "$(dirname -- "$BATS_TEST_FILENAME")/.." && pwd)"
	SCRIPT="$REPO_DIR/fixes/fix_amd_x3d_vcache.sh"
	export X3D_DRIVER_SYSFS="$BATS_TEST_TMPDIR/drivers/amd_x3d_vcache"
	export X3D_RULES_DIR="$BATS_TEST_TMPDIR/rules.d"
	mkdir -p "$X3D_DRIVER_SYSFS/AMDI0101:00" "$X3D_RULES_DIR" "$BATS_TEST_TMPDIR/bin"
	echo frequency >"$X3D_DRIVER_SYSFS/AMDI0101:00/amd_x3d_mode"
	export CALLS="$BATS_TEST_TMPDIR/calls"
	# sudo runs its command; udevadm "trigger" stands in for the kernel bind
	# event by flipping the fake attribute the way the installed rule would.
	cat >"$BATS_TEST_TMPDIR/bin/sudo" <<'STUB'
#!/bin/bash
echo "sudo $*" >>"$CALLS"
exec "$@"
STUB
	cat >"$BATS_TEST_TMPDIR/bin/udevadm" <<'STUB'
#!/bin/bash
echo "udevadm $*" >>"$CALLS"
if [[ "$1" == trigger && "${FAKE_RULE_WORKS:-1}" == 1 ]]; then
	echo cache >"$X3D_DRIVER_SYSFS/AMDI0101:00/amd_x3d_mode"
fi
STUB
	chmod +x "$BATS_TEST_TMPDIR/bin/sudo" "$BATS_TEST_TMPDIR/bin/udevadm"
	export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
}

@test "install puts the rule in place, triggers a bind event and ends on cache" {
	run "$SCRIPT"
	[ "$status" -eq 0 ]
	[ -f "$X3D_RULES_DIR/60-amd-x3d-vcache-mode.rules" ]
	grep -q 'DRIVER=="amd_x3d_vcache"' "$X3D_RULES_DIR/60-amd-x3d-vcache-mode.rules"
	grep -q 'ATTR{amd_x3d_mode}="cache"' "$X3D_RULES_DIR/60-amd-x3d-vcache-mode.rules"
	grep -q '^udevadm control --reload' "$CALLS"
	grep -q '^udevadm trigger --action=bind' "$CALLS"
	[ "$(cat "$X3D_DRIVER_SYSFS/AMDI0101:00/amd_x3d_mode")" = cache ]
}

@test "the rule hard-codes no device name" {
	run ! grep -q 'AMDI0101' "$REPO_DIR/fixes/60-amd-x3d-vcache-mode.rules"
}

@test "install fails loudly when the mode does not end on cache" {
	FAKE_RULE_WORKS=0 run "$SCRIPT"
	[ "$status" -eq 1 ]
	[[ "$output" == *"frequency"* ]]
}

@test "install without the driver installs the rule and skips the trigger" {
	rm -rf "$X3D_DRIVER_SYSFS"
	run "$SCRIPT"
	[ "$status" -eq 0 ]
	[ -f "$X3D_RULES_DIR/60-amd-x3d-vcache-mode.rules" ]
	run ! grep -q '^udevadm trigger' "$CALLS"
}

@test "install with the driver loaded but no X3D device installs the rule and succeeds" {
	rm -rf "${X3D_DRIVER_SYSFS:?}/AMDI0101:00"
	run "$SCRIPT"
	[ "$status" -eq 0 ]
	[[ "$output" == *"no X3D device"* ]]
	[ -f "$X3D_RULES_DIR/60-amd-x3d-vcache-mode.rules" ]
}

@test "--remove deletes the rule and reloads udev" {
	touch "$X3D_RULES_DIR/60-amd-x3d-vcache-mode.rules"
	run "$SCRIPT" --remove
	[ "$status" -eq 0 ]
	[ ! -e "$X3D_RULES_DIR/60-amd-x3d-vcache-mode.rules" ]
	grep -q '^udevadm control --reload' "$CALLS"
}

@test "--status reports rule and live mode" {
	run "$SCRIPT" --status
	[ "$status" -eq 0 ]
	[[ "$output" == *"frequency"* ]]
}

@test "unknown option exits 2" {
	run "$SCRIPT" --bogus
	[ "$status" -eq 2 ]
}
