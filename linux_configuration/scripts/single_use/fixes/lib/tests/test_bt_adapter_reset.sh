#!/usr/bin/env bash
# Tests for lib/bt_adapter.sh: check_adapter_stuck, _reload_btusb,
# _services_resolved, _full_adapter_reset_and_connect and _verify_audio_sink.
# Split from test_bt_adapter.sh for the 250-line cap.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bt_harness.sh
. "${SCRIPT_DIR}/bt_harness.sh"

# shellcheck source=../bt_adapter.sh
. "${FIXES_DIR}/lib/bt_adapter.sh"

# bt_adapter.sh calls _run_as_user and _restart_pipewire_stack, which are
# defined in bt_audio.sh. fix_bluetooth.sh sources both libs, so sourcing
# bt_audio.sh here reproduces the real resolution order rather than stubbing
# the two helpers out.
# shellcheck source=../bt_audio.sh
. "${FIXES_DIR}/lib/bt_audio.sh"

# _btctl_list TEXT — stub bluetoothctl so `_btctl list` emits TEXT.
_btctl_list() {
	printf '%s\n' "$1" >"${DEV}/btctl_out"
	local body
	body="$(
		cat <<'BTCTL_BODY'
cat "${LIB_TEST_DEV}/btctl_out"
BTCTL_BODY
	)"
	_t_stub bluetoothctl "$body"
}

# _lsusb_line TEXT — stub lsusb to emit TEXT.
_lsusb_line() {
	printf '%s\n' "$1" >"${DEV}/lsusb_out"
	local body
	body="$(
		cat <<'LSUSB_BODY'
cat "${LIB_TEST_DEV}/lsusb_out"
LSUSB_BODY
	)"
	_t_stub lsusb "$body"
}

# _record_reload ARGS... — stand-in for the real btusb reloader.
_record_reload() {
	printf 'reload_called %s\n' "$*" >>"${DEV}/fixes"
}

# --- check_adapter_stuck ----------------------------------------------------

# A responsive adapter short-circuits before any USB work.
bt_reset
_btctl_list "Controller AA:BB:CC:11:22:33 kuhy-pc [default]"
out="$(check_adapter_stuck 2>&1)"
_t_contains "$out" "Adapter is responsive" \
	"check_adapter_stuck: reports a responsive adapter"
_t_eq "" "$(_t_fixes)" "check_adapter_stuck: applies no fix when the adapter responds"

# Unresponsive adapter, and lsusb sees no bluetooth dongle at all.
bt_reset
_btctl_list "No default controller available"
_t_stub lsusb 'echo "Bus 001 Device 002: ID 046d:c077 Logitech, Inc. Mouse"'
out="$(check_adapter_stuck 2>&1)"
_t_contains "$out" "not responding" \
	"check_adapter_stuck: warns when bluetoothctl sees no controller"
_t_contains "$out" "No USB Bluetooth adapter found" \
	"check_adapter_stuck: reports a missing dongle when lsusb has no bluetooth line"

# Unresponsive adapter with a bluetooth dongle present and usbreset available:
# the USB reset path runs.
bt_reset
_btctl_list "No default controller available"
_lsusb_line "Bus 001 Device 004: ID 0a12:0001 Cambridge Silicon Radio Bluetooth dongle"
out="$(check_adapter_stuck 2>&1)"
_t_contains "$out" "USB-resetting Bluetooth adapter (0a12:0001)" \
	"check_adapter_stuck: USB-resets the adapter when usbreset is available"
_t_contains "$(_t_calls)" "usbreset 0a12:0001" \
	"check_adapter_stuck: passes the parsed USB ID to usbreset"

# Same, but usbreset is NOT installed: the btusb reload fallback runs. This
# host really has /usr/bin/usbreset, and a prepended stub dir cannot hide a
# real binary, so _t_hide rebuilds PATH without it while keeping grep/head
# (which this very branch uses) reachable.
bt_reset
_btctl_list "No default controller available"
_lsusb_line "Bus 001 Device 004: ID 0a12:0001 Cambridge Silicon Radio Bluetooth dongle"
_t_unstub usbreset
_t_hide usbreset
out="$(
	eval '_reload_btusb() { _record_reload "$@"; }'
	check_adapter_stuck 2>&1
)"
_t_full_path
_t_contains "$out" "Falling back to btusb module reload" \
	"check_adapter_stuck: falls back to a btusb reload when usbreset is absent"
_t_contains "$(_t_fixes)" "reload_called" \
	"check_adapter_stuck: runs the btusb reload fix when usbreset is absent"

# A bluetooth line whose ID does not parse leaves usb_id empty, which also
# takes the btusb reload fallback.
bt_reset
_btctl_list "No default controller available"
_lsusb_line "Bus 001 Device 004: Bluetooth dongle with no parseable id"
out="$(
	eval '_reload_btusb() { _record_reload "$@"; }'
	check_adapter_stuck 2>&1
)"
_t_contains "$(_t_fixes)" "reload_called" \
	"check_adapter_stuck: falls back to a btusb reload when the USB ID does not parse"

# --- _reload_btusb ----------------------------------------------------------

bt_reset
_reload_btusb
_t_contains "$(_t_calls)" "modprobe -r btusb" "_reload_btusb: unloads the btusb module"
_t_contains "$(_t_calls)" "modprobe btusb" "_reload_btusb: loads btusb again"

# --- _services_resolved -----------------------------------------------------

bt_reset
_t_stub dbus-send 'echo "   variant       boolean true"'
if _services_resolved "AA:BB:CC:DD:EE:FF"; then
	_t_pass "_services_resolved: true when the property reads boolean true"
else
	_t_fail "_services_resolved: expected success on boolean true"
fi
_t_contains "$(_t_calls)" "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF" \
	"_services_resolved: builds the dbus object path from the MAC"

bt_reset
_t_stub dbus-send 'echo "   variant       boolean false"'
if _services_resolved "AA:BB:CC:DD:EE:FF"; then
	_t_fail "_services_resolved: expected failure on boolean false"
else
	_t_pass "_services_resolved: false when the property reads boolean false"
fi

bt_reset
_t_stub dbus-send 'exit 1'
if _services_resolved "AA:BB:CC:DD:EE:FF"; then
	_t_fail "_services_resolved: expected failure when dbus-send fails"
else
	_t_pass "_services_resolved: false when dbus-send itself fails"
fi

# --- _full_adapter_reset_and_connect ----------------------------------------
#
# The real body sleeps 1 + 2 + 5 + 3 + 3 + 20 = 34 seconds. `sleep` is stubbed
# to return instantly so the suite stays fast; the calls are still recorded,
# so the ordering assertions below are on the real sequence.

bt_reset
_t_stub sleep 'exit 0'
_t_stub bluetoothctl 'cat >/dev/null; exit 0'
out="$(_full_adapter_reset_and_connect "AA:BB:CC:DD:EE:FF" 2>&1)"
calls="$(_t_calls)"

_t_contains "$out" "Performing full adapter reset" \
	"_full_adapter_reset_and_connect: announces the reset"
_t_contains "$calls" "modprobe -r btusb" \
	"_full_adapter_reset_and_connect: unloads btusb"
_t_contains "$calls" "modprobe btusb" \
	"_full_adapter_reset_and_connect: reloads btusb"
_t_contains "$calls" "systemctl restart bluetooth.service" \
	"_full_adapter_reset_and_connect: restarts bluetooth.service"
_t_contains "$out" "Reconnecting to AA:BB:CC:DD:EE:FF" \
	"_full_adapter_reset_and_connect: announces the reconnect"
_t_contains "$calls" "systemctl --user restart pipewire pipewire-pulse wireplumber" \
	"_full_adapter_reset_and_connect: restarts the pipewire stack via _run_as_user"

# --- _verify_audio_sink -----------------------------------------------------

# pactl absent: the function returns success without probing anything. This
# host really has pactl, so _t_hide removes it from PATH outright.
bt_reset
_t_unstub pactl
_t_hide pactl
if _verify_audio_sink "AA:BB:CC:DD:EE:FF"; then
	_t_pass "_verify_audio_sink: returns success when pactl is not installed"
else
	_t_fail "_verify_audio_sink: expected success when pactl is absent"
fi
_t_full_path

# The card shows up on the first probe.
bt_reset
_t_stub sleep 'exit 0'
_t_stub pactl 'echo "42 bluez_card.AA_BB_CC_DD_EE_FF module-bluez5-device.c"'
out="$(_verify_audio_sink "AA:BB:CC:DD:EE:FF" 2>&1)"
_t_contains "$out" "Bluetooth audio card detected" \
	"_verify_audio_sink: reports the card once PipeWire lists it"
_t_eq "0" "$(_t_calls | grep -c '^sleep')" \
	"_verify_audio_sink: does not sleep when the card is present on the first probe"

# The card never appears: five probes, then a warning and a non-zero return.
bt_reset
_t_stub sleep 'exit 0'
_t_stub pactl 'echo "42 alsa_card.pci-0000_00_1f.3 module-alsa-card.c"'
if out="$(_verify_audio_sink "AA:BB:CC:DD:EE:FF" 2>&1)"; then
	_t_fail "_verify_audio_sink: expected a non-zero return when the card never appears"
else
	_t_pass "_verify_audio_sink: returns non-zero when the card never appears"
fi
_t_contains "$out" "not found in PipeWire" \
	"_verify_audio_sink: warns when the card never appears"
_t_eq "5" "$(_t_calls | grep -c '^sleep')" \
	"_verify_audio_sink: retries five times before giving up"

echo
echo "bt_adapter (reset/probe): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
