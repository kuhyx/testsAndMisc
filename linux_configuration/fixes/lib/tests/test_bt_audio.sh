#!/usr/bin/env bash
# Tests for lib/bt_audio.sh: check_pipewire_health, _run_as_user,
# _restart_pipewire_stack and set_audio_profile.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bt_harness.sh
. "${SCRIPT_DIR}/bt_harness.sh"

# shellcheck source=../bt_audio.sh
. "${FIXES_DIR}/lib/bt_audio.sh"

# _stub_out NAME TEXT — stub NAME to print TEXT (kept out of a quoted string
# so no $ needs to survive quoting).
_stub_out() {
	printf '%s\n' "$2" >"${DEV}/out_$1"
	local body
	body="cat \"\${LIB_TEST_DEV}/out_$1\""
	_t_stub "$1" "$body"
}

# _record_restart ARGS... — stand-in for the real pipewire restarter.
_record_restart() {
	printf 'restart_called %s\n' "$*" >>"${DEV}/fixes"
}

# --- check_pipewire_health --------------------------------------------------

# wpctl absent: the check is skipped. This host really has wpctl, so _t_hide
# removes it from PATH rather than relying on a stub dir that cannot mask it.
bt_reset
_t_unstub wpctl
_t_hide wpctl
out="$(check_pipewire_health 2>&1)"
_t_full_path
_t_contains "$out" "wpctl not found" \
	"check_pipewire_health: skips the check when wpctl is not installed"
_t_eq "" "$(_t_fixes)" "check_pipewire_health: applies no fix when wpctl is absent"

# wpctl answers promptly: PipeWire is healthy. This case only passes because
# the timeout now runs INSIDE _run_as_user -- `timeout 3 _run_as_user ...`
# could never reach the stub, since timeout cannot invoke a shell function.
bt_reset
_t_stub wpctl 'exit 0'
_t_stub timeout 'shift; exec "$@"'
out="$(check_pipewire_health 2>&1)"
_t_contains "$out" "PipeWire is responsive" \
	"check_pipewire_health: reports a responsive PipeWire"
_t_eq "" "$(_t_fixes)" "check_pipewire_health: applies no fix when PipeWire responds"

# wpctl fails (as a timeout would): the restart fix runs.
bt_reset
_t_stub wpctl 'exit 1'
out="$(
	eval '_restart_pipewire_stack() { _record_restart "$@"; }'
	check_pipewire_health 2>&1
)"
_t_contains "$out" "appears hung" \
	"check_pipewire_health: warns when wpctl does not answer"
_t_contains "$out" "Restarting PipeWire + WirePlumber audio stack" \
	"check_pipewire_health: applies the audio-stack restart fix"
_t_contains "$(_t_fixes)" "restart_called" \
	"check_pipewire_health: calls the restart helper"

# --- _run_as_user -----------------------------------------------------------

bt_reset
_t_stub id 'echo 1000'
out="$(SUDO_USER="kuhy" _run_as_user echo hello 2>&1)"
_t_contains "$(_t_calls)" "sudo -u kuhy" \
	"_run_as_user: runs the command as SUDO_USER when it is set"
_t_contains "$out" "hello" "_run_as_user: passes the command through to be run"

bt_reset
_t_stub id 'echo 1000'
_t_reset_calls
(
	unset SUDO_USER
	USER="kuhy" _run_as_user echo hi >/dev/null 2>&1
)
_t_contains "$(_t_calls)" "sudo -u kuhy" \
	"_run_as_user: falls back to USER when SUDO_USER is unset"

# --- _restart_pipewire_stack ------------------------------------------------

bt_reset
_t_stub sleep 'exit 0'
out="$(_restart_pipewire_stack 2>&1)"
_t_contains "$(_t_calls)" "systemctl --user restart pipewire pipewire-pulse wireplumber" \
	"_restart_pipewire_stack: restarts pipewire, pipewire-pulse and wireplumber"
_t_contains "$out" "Waiting for audio stack to initialize" \
	"_restart_pipewire_stack: waits for the stack to come back"

# --- set_audio_profile ------------------------------------------------------

bt_reset
TARGET_MAC=""
out="$(set_audio_profile 2>&1)"
_t_eq "" "$out" "set_audio_profile: does nothing when TARGET_MAC is empty"

# pactl absent: returns before any probing. The host has a real pactl, so it
# has to leave PATH entirely.
bt_reset
TARGET_MAC="AA:BB:CC:DD:EE:FF"
_t_unstub pactl
_t_hide pactl
out="$(set_audio_profile 2>&1)"
_t_full_path
_t_eq "" "$out" "set_audio_profile: does nothing when pactl is not installed"

# No card for this device: the function reports and returns.
bt_reset
TARGET_MAC="AA:BB:CC:DD:EE:FF"
_t_stub sleep 'exit 0'
_stub_out pactl "Card #1
	Name: alsa_card.pci-0000_00_1f.3
	Active Profile: output:analog-stereo"
out="$(set_audio_profile 2>&1)"
_t_contains "$out" "No PipeWire audio card found" \
	"set_audio_profile: reports when the device has no PipeWire card"

# SBC-XQ active: the profile is switched to plain a2dp-sink.
bt_reset
TARGET_MAC="AA:BB:CC:DD:EE:FF"
_t_stub sleep 'exit 0'
_stub_out pactl "Card #2
	Name: bluez_card.AA_BB_CC_DD_EE_FF
	Active Profile: a2dp-sink-sbc_xq"
out="$(set_audio_profile 2>&1)"
_t_contains "$out" "SBC-XQ codec active" \
	"set_audio_profile: warns when the SBC-XQ codec is active"
_t_contains "$out" "Switching to standard SBC codec" \
	"set_audio_profile: applies the codec-switch fix"
_t_contains "$(_t_calls)" \
	"pactl set-card-profile bluez_card.AA_BB_CC_DD_EE_FF a2dp-sink" \
	"set_audio_profile: switches the card to a2dp-sink"

# A healthy non-SBC-XQ profile is reported and left alone.
bt_reset
TARGET_MAC="AA:BB:CC:DD:EE:FF"
_t_stub sleep 'exit 0'
_stub_out pactl "Card #2
	Name: bluez_card.AA_BB_CC_DD_EE_FF
	Active Profile: a2dp-sink"
out="$(set_audio_profile 2>&1)"
_t_contains "$out" "Audio profile: a2dp-sink" \
	"set_audio_profile: reports a healthy active profile"
_t_lacks "$out" "Switching to standard SBC codec" \
	"set_audio_profile: applies no fix for a healthy profile"

echo
echo "bt_audio (pipewire): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
