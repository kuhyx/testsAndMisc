#!/usr/bin/env bash
# Tests for lib/bt_pairing.sh: remove_stale_pairing, restart_bluetooth and
# fix_usb_autosuspend.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bt_harness.sh
. "${SCRIPT_DIR}/bt_harness.sh"

# shellcheck source=../bt_pairing.sh
. "${FIXES_DIR}/lib/bt_pairing.sh"

# _btctl_info BODY — stub bluetoothctl so `_btctl info <mac>` returns BODY.
_btctl_info() {
	local body="$1"
	local stub
	stub="$(
		cat <<'BTCTL_HEAD'
read -r cmd rest
if [[ "$cmd" == "info" ]]; then
	cat "${LIB_TEST_DEV}/btctl_info"
fi
exit 0
BTCTL_HEAD
	)"
	printf '%s\n' "$body" >"${DEV}/btctl_info"
	_t_stub bluetoothctl "$stub"
}

# --- remove_stale_pairing ---------------------------------------------------

bt_reset
TARGET_MAC=""
out="$(remove_stale_pairing)"
_t_eq "" "$out" "remove_stale_pairing: no output when TARGET_MAC is empty"
_t_eq "" "$(_t_fixes)" "remove_stale_pairing: applies no fix when TARGET_MAC is empty"

# Paired but not connected — the stale-pairing case the function exists for.
bt_reset
TARGET_MAC="AA:BB:CC:DD:EE:FF"
_btctl_info "Device AA:BB:CC:DD:EE:FF JBL
	Paired: yes
	Connected: no"
out="$(remove_stale_pairing 2>&1)"
_t_contains "$out" "stale pairing" \
	"remove_stale_pairing: warns when the device is paired but not connected"
_t_contains "$out" "Removing stale pairing for AA:BB:CC:DD:EE:FF" \
	"remove_stale_pairing: applies the removal fix for a stale pairing"

# Paired AND connected — healthy, nothing to do.
bt_reset
TARGET_MAC="AA:BB:CC:DD:EE:FF"
_btctl_info "Device AA:BB:CC:DD:EE:FF JBL
	Paired: yes
	Connected: yes"
out="$(remove_stale_pairing 2>&1)"
_t_contains "$out" "paired and connected" \
	"remove_stale_pairing: reports a healthy device as paired and connected"
_t_lacks "$out" "Removing stale pairing" \
	"remove_stale_pairing: applies no fix when the device is connected"

# Known to the adapter but not paired at all.
bt_reset
TARGET_MAC="AA:BB:CC:DD:EE:FF"
_btctl_info "Device AA:BB:CC:DD:EE:FF JBL
	Paired: no
	Connected: no"
out="$(remove_stale_pairing 2>&1)"
_t_contains "$out" "not currently paired" \
	"remove_stale_pairing: reports an unpaired device as not paired"
_t_lacks "$out" "Removing stale pairing" \
	"remove_stale_pairing: applies no fix when the device is not paired"

# Device entirely unknown to bluetoothctl.
bt_reset
TARGET_MAC="11:22:33:44:55:66"
_btctl_info "No default controller available"
out="$(remove_stale_pairing 2>&1)"
_t_contains "$out" "Fresh pairing needed" \
	"remove_stale_pairing: asks for fresh pairing when the device is unknown"

# --- restart_bluetooth ------------------------------------------------------

bt_reset
FIXES_APPLIED=0
out="$(restart_bluetooth 2>&1)"
_t_contains "$out" "skipping service restart" \
	"restart_bluetooth: skips the restart when no fixes were applied"

bt_reset
FIXES_APPLIED=2
out="$(restart_bluetooth 2>&1)"
_t_contains "$out" "Restarting bluetooth.service" \
	"restart_bluetooth: restarts the service when fixes were applied"

echo
echo "bt_pairing (stale pairing + restart): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
