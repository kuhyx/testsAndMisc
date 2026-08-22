#!/usr/bin/env bash
# Tests for lib/bt_audio.sh: _check_connection_health.
# Split from test_bt_audio.sh for the 250-line cap.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bt_harness.sh
. "${SCRIPT_DIR}/bt_harness.sh"

# _check_connection_health calls _services_resolved, _verify_audio_sink and
# _full_adapter_reset_and_connect, all defined in bt_adapter.sh, which
# fix_bluetooth.sh also sources.
# shellcheck source=../bt_adapter.sh
. "${FIXES_DIR}/lib/bt_adapter.sh"
# shellcheck source=../bt_audio.sh
. "${FIXES_DIR}/lib/bt_audio.sh"

# _record_reset ARGS... — stand-in for the real full-adapter reset.
_record_reset() {
	printf 'reset_called %s\n' "$*" >>"${DEV}/fixes"
}

# _info_says TEXT — stub bluetoothctl so `_btctl info` returns TEXT.
_info_says() {
	printf '%s\n' "$1" >"${DEV}/btctl_info"
	_t_stub_stdin bluetoothctl <<'STUB_BODY'
read -r cmd rest
[[ "$cmd" == "info" ]] && cat "${LIB_TEST_DEV}/btctl_info"
# Real bluetoothctl consumes its whole stdin. Draining it here keeps the
# writing block from taking SIGPIPE partway through, which would silently
# stop it executing (and reading) the rest of its lines.
cat >/dev/null
exit 0
STUB_BODY
}

# Not connected at all: fails immediately, without probing services.
bt_reset
_t_stub sleep 'exit 0'
_info_says "Device AA:BB:CC:DD:EE:FF
	Connected: no"
if _check_connection_health "AA:BB:CC:DD:EE:FF" >/dev/null 2>&1; then
	_t_fail "_check_connection_health: expected failure when not connected"
else
	_t_pass "_check_connection_health: fails when the device is not connected"
fi
_t_lacks "$(_t_calls)" "dbus-send" \
	"_check_connection_health: does not probe services when not connected"

# Connected with services resolved on the first probe: healthy.
bt_reset
_t_stub sleep 'exit 0'
_info_says "Device AA:BB:CC:DD:EE:FF
	Connected: yes"
_t_stub dbus-send 'echo "   variant       boolean true"'
_t_stub pactl 'echo "42 bluez_card.AA_BB_CC_DD_EE_FF module-bluez5-device.c"'
if out="$(_check_connection_health "AA:BB:CC:DD:EE:FF" 2>&1)"; then
	_t_pass "_check_connection_health: succeeds when connected with services resolved"
else
	_t_fail "_check_connection_health: expected success when services resolve"
fi
_t_contains "$out" "with A2DP services resolved" \
	"_check_connection_health: reports resolved A2DP services"
_t_lacks "$out" "Full adapter reset" \
	"_check_connection_health: does not reset the adapter when services resolve"

# Connected but services never resolve: three probes, then the full reset,
# and after the reset they resolve.
bt_reset
_t_stub sleep 'exit 0'
_info_says "Device AA:BB:CC:DD:EE:FF
	Connected: yes"
: >"${DEV}/dbus_calls"
_t_stub_stdin dbus-send <<'STUB_BODY'
n=$(cat "${LIB_TEST_DEV}/dbus_calls" 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" >"${LIB_TEST_DEV}/dbus_calls"
if ((n > 3)); then
	echo "   variant       boolean true"
else
	echo "   variant       boolean false"
fi
exit 0
STUB_BODY
_t_stub pactl 'echo "42 bluez_card.AA_BB_CC_DD_EE_FF module-bluez5-device.c"'
if out="$(
	eval '_full_adapter_reset_and_connect() { _record_reset "$@"; }'
	_check_connection_health "AA:BB:CC:DD:EE:FF" 2>&1
)"; then
	_t_pass "_check_connection_health: succeeds once services resolve after a reset"
else
	_t_fail "_check_connection_health: expected success after the adapter reset"
fi
_t_contains "$out" "services not resolved (stale HCI link state)" \
	"_check_connection_health: warns about a stale HCI link state"
_t_contains "$out" "Full adapter reset to fix stale link" \
	"_check_connection_health: applies the full adapter reset fix"
_t_contains "$out" "resolved after reset" \
	"_check_connection_health: reports services resolving after the reset"
_t_contains "$(_t_fixes)" "reset_called AA:BB:CC:DD:EE:FF" \
	"_check_connection_health: passes the MAC to the adapter reset"

# Services never resolve, even after the reset: the function fails.
bt_reset
_t_stub sleep 'exit 0'
_info_says "Device AA:BB:CC:DD:EE:FF
	Connected: yes"
_t_stub dbus-send 'echo "   variant       boolean false"'
if out="$(
	eval '_full_adapter_reset_and_connect() { _record_reset "$@"; }'
	_check_connection_health "AA:BB:CC:DD:EE:FF" 2>&1
)"; then
	_t_fail "_check_connection_health: expected failure when services never resolve"
else
	_t_pass "_check_connection_health: fails when services never resolve after a reset"
fi
_t_contains "$(_t_fixes)" "reset_called" \
	"_check_connection_health: still attempts the reset before giving up"

echo
echo "bt_audio (health): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
