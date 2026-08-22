#!/usr/bin/env bash
# Tests for lib/bt_audio.sh: connect_device and _check_connection_health.
# Split from test_bt_audio.sh for the 250-line cap.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bt_harness.sh
. "${SCRIPT_DIR}/bt_harness.sh"

# bt_audio.sh calls _services_resolved, _verify_audio_sink and
# _full_adapter_reset_and_connect, which live in bt_adapter.sh.
# fix_bluetooth.sh sources both libs, so sourcing both here reproduces the
# real resolution order instead of stubbing those helpers out.
# shellcheck source=../bt_adapter.sh
. "${FIXES_DIR}/lib/bt_adapter.sh"
# shellcheck source=../bt_audio.sh
. "${FIXES_DIR}/lib/bt_audio.sh"

# _btctl_script — stub bluetoothctl with a body read from stdin. The stub
# itself reads its command from stdin too, exactly as the real tool does when
# driven by _btctl.
_btctl_script() {
	_t_stub_stdin bluetoothctl
}

# The connect paths sleep 15-20s at a time; the stub keeps the suite fast
# while the calls stay recorded.
_no_sleep() {
	_t_stub sleep 'exit 0'
}

# --- connect_device ---------------------------------------------------------

bt_reset
TARGET_MAC=""
out="$(connect_device 2>&1)"
_t_eq "" "$out" "connect_device: does nothing when TARGET_MAC is empty"

# Already connected: reports and returns without scanning.
bt_reset
_no_sleep
TARGET_MAC="AA:BB:CC:DD:EE:FF"
printf 'Device AA:BB:CC:DD:EE:FF\n\tConnected: yes\n' >"${DEV}/btctl_info"
_btctl_script <<'STUB_BODY'
read -r cmd rest
[[ "$cmd" == "info" ]] && cat "${LIB_TEST_DEV}/btctl_info"
# Real bluetoothctl consumes its whole stdin. Draining it here keeps the
# writing block from taking SIGPIPE partway through, which would silently
# stop it executing (and reading) the rest of its lines.
cat >/dev/null
exit 0
STUB_BODY
out="$(connect_device 2>&1)"
_t_contains "$out" "already connected" \
	"connect_device: reports a device that is already connected"
_t_lacks "$out" "Scanning for" \
	"connect_device: does not scan when the device is already connected"

# Paired but not connected: the direct-connect attempt runs and succeeds.
bt_reset
_no_sleep
TARGET_MAC="AA:BB:CC:DD:EE:FF"
printf 'Device AA:BB:CC:DD:EE:FF\n\tPaired: yes\n\tConnected: no\n' >"${DEV}/btctl_info"
_btctl_script <<'STUB_BODY'
read -r cmd rest
[[ "$cmd" == "info" ]] && cat "${LIB_TEST_DEV}/btctl_info"
# Real bluetoothctl consumes its whole stdin. Draining it here keeps the
# writing block from taking SIGPIPE partway through, which would silently
# stop it executing (and reading) the rest of its lines.
cat >/dev/null
exit 0
STUB_BODY
out="$(
	eval '_check_connection_health() { return 0; }'
	connect_device 2>&1
)"
_t_contains "$out" "already paired. Trying direct connect" \
	"connect_device: tries a direct connect for an already-paired device"
_t_lacks "$out" "Scanning for" \
	"connect_device: does not scan when the direct connect succeeds"

# Direct connect fails, and the rescan does not find the device.
bt_reset
_no_sleep
TARGET_MAC="AA:BB:CC:DD:EE:FF"
printf 'Device AA:BB:CC:DD:EE:FF\n\tPaired: yes\n\tConnected: no\n' >"${DEV}/btctl_info"
_btctl_script <<'STUB_BODY'
read -r cmd rest
[[ "$cmd" == "info" ]] && cat "${LIB_TEST_DEV}/btctl_info"
# Real bluetoothctl consumes its whole stdin. Draining it here keeps the
# writing block from taking SIGPIPE partway through, which would silently
# stop it executing (and reading) the rest of its lines.
cat >/dev/null
exit 0
STUB_BODY
if out="$(
	eval '_check_connection_health() { return 1; }'
	connect_device 2>&1
)"; then
	_t_fail "connect_device: expected failure when the device is never found"
else
	_t_pass "connect_device: returns non-zero when the device is never found"
fi
_t_contains "$out" "Removing stale pairing for fresh start" \
	"connect_device: removes the stale pairing after a failed direct connect"
_t_contains "$out" "Scanning for AA:BB:CC:DD:EE:FF" \
	"connect_device: falls back to a scan after a failed direct connect"
_t_contains "$out" "not found during scan" \
	"connect_device: reports a device that never appears in the scan"

# Unpaired device that IS found by the scan: pair, trust, connect all run.
bt_reset
_no_sleep
TARGET_MAC="AA:BB:CC:DD:EE:FF"
_btctl_script <<'STUB_BODY'
read -r cmd rest
case "$cmd" in
info) printf "Device AA:BB:CC:DD:EE:FF\n\tPaired: no\n\tConnected: no\n" ;;
devices) echo "Device AA:BB:CC:DD:EE:FF JBL Charge 5" ;;
esac
cat >/dev/null
exit 0
STUB_BODY
out="$(
	eval '_check_connection_health() { return 0; }'
	connect_device 2>&1
)"
_t_contains "$out" "Device found during scan" \
	"connect_device: reports the device once the scan finds it"
_t_contains "$out" "Pairing..." "connect_device: pairs a device found by the scan"
_t_contains "$out" "Trusting..." "connect_device: trusts the device so it auto-reconnects"
_t_contains "$out" "Connecting..." "connect_device: connects after pairing and trusting"

# Found by the scan, but the connection never becomes healthy.
bt_reset
_no_sleep
TARGET_MAC="AA:BB:CC:DD:EE:FF"
_btctl_script <<'STUB_BODY'
read -r cmd rest
case "$cmd" in
info) printf "Device AA:BB:CC:DD:EE:FF\n\tPaired: no\n\tConnected: no\n" ;;
devices) echo "Device AA:BB:CC:DD:EE:FF JBL Charge 5" ;;
esac
cat >/dev/null
exit 0
STUB_BODY
if out="$(
	eval '_check_connection_health() { return 1; }'
	connect_device 2>&1
)"; then
	_t_fail "connect_device: expected failure when the connection stays unhealthy"
else
	_t_pass "connect_device: returns non-zero when the connection stays unhealthy"
fi
_t_contains "$out" "Connection to AA:BB:CC:DD:EE:FF failed" \
	"connect_device: reports the failure after pairing and connecting"

echo
echo "bt_audio (connect): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
