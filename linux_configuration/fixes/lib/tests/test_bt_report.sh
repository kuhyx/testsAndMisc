#!/usr/bin/env bash
# Tests for lib/bt_report.sh: show_instructions and dump_diagnostics.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bt_harness.sh
. "${SCRIPT_DIR}/bt_harness.sh"

# shellcheck source=../bt_report.sh
. "${FIXES_DIR}/lib/bt_report.sh"

# --- show_instructions ------------------------------------------------------

bt_reset
TARGET_MAC="AA:BB:CC:DD:EE:FF"
out="$(show_instructions)"
_t_contains "$out" "Next Steps" "show_instructions: prints the Next Steps header"
_t_contains "$out" "PAIRING mode" "show_instructions: tells the user to enter pairing mode"
_t_contains "$out" "pair AA:BB:CC:DD:EE:FF" \
	"show_instructions: interpolates TARGET_MAC into the pair command"
_t_contains "$out" "trust AA:BB:CC:DD:EE:FF" \
	"show_instructions: interpolates TARGET_MAC into the trust command"
_t_contains "$out" "connect AA:BB:CC:DD:EE:FF" \
	"show_instructions: interpolates TARGET_MAC into the connect command"
_t_lacks "$out" "pair <MAC>" \
	"show_instructions: omits the placeholder form when a MAC is known"
_t_contains "$out" "journalctl -u bluetooth -f" \
	"show_instructions: points at the bluetooth journal on failure"

# With no MAC known, the placeholder branch runs instead.
bt_reset
TARGET_MAC=""
out="$(show_instructions)"
_t_contains "$out" "pair <MAC>" \
	"show_instructions: falls back to the <MAC> placeholder when TARGET_MAC is empty"
_t_contains "$out" "note its MAC address" \
	"show_instructions: tells the user to note the MAC when none is known"
_t_lacks "$out" "trust AA:BB" \
	"show_instructions: does not emit a concrete MAC when TARGET_MAC is empty"

# --- dump_diagnostics -------------------------------------------------------

bt_reset
TARGET_MAC="AA:BB:CC:DD:EE:FF"
# _btctl pipes the command in on stdin, so the stub dispatches on what it
# reads there. Quoted heredoc: the $ belong to the stub, not to this file.
btctl_body="$(
	cat <<'BTCTL_BODY'
read -r cmd rest
case "$cmd" in
show) echo "Controller AA:11 [bluetoothctl]"; echo "	Powered: yes" ;;
devices) echo "Device AA:BB:CC:DD:EE:FF JBL Charge 5" ;;
info) echo "	Connected: yes" ;;
esac
exit 0
BTCTL_BODY
)"
_t_stub bluetoothctl "$btctl_body"
# `lsmod | grep -i bluetooth` matches on the module NAME, so the fixture has
# to carry a row whose text actually contains "bluetooth" -- bare "btusb" is
# filtered out by the lib's own grep, exactly as it would be in production.
_t_stub lsmod '
echo "btusb                  73728  0"
echo "bluetooth             995328  9 btrtl,btmtk,btintel,btbcm,btusb"
'
_t_stub rfkill 'echo "0 bluetooth hci0 unblocked unblocked"'
_t_stub journalctl 'echo "bluetoothd[1]: Bluetooth daemon"'

out="$(dump_diagnostics)"
_t_contains "$out" "=== Diagnostic Summary ===" "dump_diagnostics: prints the summary header"
_t_contains "$out" "--- Bluetooth adapter ---" "dump_diagnostics: prints the adapter section"
_t_contains "$out" "Powered: yes" "dump_diagnostics: includes bluetoothctl show output"
_t_lacks "$out" "[bluetoothctl]" \
	"dump_diagnostics: filters the [bluetoothctl] prompt noise out of show output"
_t_contains "$out" "Device AA:BB:CC:DD:EE:FF" "dump_diagnostics: lists known devices"
_t_contains "$out" "bluetooth             995328" \
	"dump_diagnostics: reports loaded bluetooth kernel modules"
_t_lacks "$out" "(none loaded)" \
	"dump_diagnostics: omits the '(none loaded)' fallback when a module matches"
_t_contains "$out" "--- rfkill status ---" "dump_diagnostics: prints the rfkill section"
_t_contains "$out" "--- Device info: AA:BB:CC:DD:EE:FF ---" \
	"dump_diagnostics: dumps info for the target device when a MAC is set"
_t_contains "$out" "Bluetooth daemon" "dump_diagnostics: includes recent journal entries"

# Empty results still print their section, via the `|| echo`/`|| true` arms.
bt_reset
TARGET_MAC=""
_t_stub bluetoothctl 'exit 0'
_t_stub lsmod 'echo "ext4                  1000  0"'
_t_stub rfkill 'exit 1'
_t_stub journalctl 'exit 1'

out="$(dump_diagnostics)"
_t_contains "$out" "(none loaded)" \
	"dump_diagnostics: reports '(none loaded)' when no bluetooth module matches"
_t_contains "$out" "(rfkill not available)" \
	"dump_diagnostics: reports rfkill unavailable when the command fails"
_t_lacks "$out" "--- Device info:" \
	"dump_diagnostics: skips the device-info section when TARGET_MAC is empty"

# A device the adapter does not know about takes the `|| echo` arm.
bt_reset
TARGET_MAC="11:22:33:44:55:66"
btctl_body="$(
	cat <<'BTCTL_INFO_FAILS'
read -r cmd rest
[[ "$cmd" == "info" ]] && exit 1
exit 0
BTCTL_INFO_FAILS
)"
_t_stub bluetoothctl "$btctl_body"
out="$(dump_diagnostics)"
_t_contains "$out" "(device not known)" \
	"dump_diagnostics: reports an unknown device when bluetoothctl info fails"

echo
echo "bt_report: ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
