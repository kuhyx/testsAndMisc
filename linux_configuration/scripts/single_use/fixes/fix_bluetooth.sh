#!/usr/bin/env bash

# Fix Bluetooth connectivity issues on Arch Linux
#
# Common issues addressed:
# 1. Bluetooth service not running or in bad state
# 2. Missing PipeWire/PulseAudio Bluetooth audio support (A2DP sink)
# 3. Stale pairing data causing connection hangs
# 4. Missing Broadcom firmware (.hcd files)
# 5. Stuck/unresponsive adapter requiring USB reset
# 6. USB autosuspend causing audio dropouts
# 7. Hung PipeWire/WirePlumber audio stack
# 8. Auto scan/pair/trust/connect when MAC is provided
# 9. SBC-XQ codec causing dropouts on older adapters
# 10. Stale HCI link state (link tx timeout) requiring btusb reload
# 11. A2DP ServicesResolved stuck at false after connect
# 12. PipeWire bluez audio card not appearing after connection
#
# Usage:
#   ./fix_bluetooth.sh                          # Diagnose and fix + connect JBL Charge 5
#   ./fix_bluetooth.sh --interactive            # Prompt before each fix
#   ./fix_bluetooth.sh <MAC>                    # Fix + auto-connect to device
#   ./fix_bluetooth.sh --interactive <MAC>      # Both
#
# Safe to re-run: all fixes are idempotent.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../../lib/common.sh
source "$SCRIPT_DIR/../../lib/common.sh"

parse_interactive_args "$@"
shift "$COMMON_ARGS_SHIFT"

TARGET_MAC="${1:-F8:5C:7E:0E:50:6B}"

require_root "$@"

print_setup_header "Bluetooth Troubleshooter"

FIXES_APPLIED=0
FIXES_SKIPPED=0

# ---------------------------------------------------------------------------
# Helper: run or skip a fix depending on --interactive
# ---------------------------------------------------------------------------
apply_fix() {
	local description="$1"
	shift

	echo ""
	log_info "$description"

	if [[ $INTERACTIVE_MODE == "true" ]]; then
		if ! ask_yes_no "  Apply this fix?"; then
			log_warn "Skipped."
			((FIXES_SKIPPED++)) || true
			return 0
		fi
	fi

	if "$@"; then
		log_ok "Done."
		((FIXES_APPLIED++)) || true
	else
		log_error "Failed (non-fatal, continuing)."
	fi
}

# ---------------------------------------------------------------------------
# Helper: run a bluetoothctl command reliably via stdin pipe.
# (bluetoothctl -- <cmd> returns empty when run non-interactively)
# ---------------------------------------------------------------------------
_btctl() {
	echo "$*" | bluetoothctl 2>/dev/null
}

# ==========================================================================
# 1. Check Bluetooth service status
# ==========================================================================
check_bluetooth_service() {
	echo ""
	log_info "Checking bluetooth.service status..."

	if ! systemctl is-active --quiet bluetooth.service; then
		log_warn "bluetooth.service is not running."
		apply_fix "Starting and enabling bluetooth.service" \
			systemctl enable --now bluetooth.service
	else
		log_ok "bluetooth.service is active."
	fi

	# Also check if the adapter is soft/hard blocked
	if has_cmd rfkill; then
		local blocked
		blocked=$(rfkill list bluetooth 2>/dev/null || true)
		if echo "$blocked" | grep -qi "Soft blocked: yes"; then
			apply_fix "Unblocking Bluetooth (rfkill)" rfkill unblock bluetooth
		elif echo "$blocked" | grep -qi "Hard blocked: yes"; then
			log_error "Bluetooth is HARD blocked (physical switch). Enable it manually."
		else
			log_ok "Bluetooth is not blocked by rfkill."
		fi
	fi
}

# ==========================================================================
# 2. Check for required packages (bluez, pipewire-pulse, etc.)
# ==========================================================================
check_packages() {
	echo ""
	log_info "Checking required Bluetooth packages..."

	local missing=()

	for pkg in bluez bluez-utils; do
		if ! pacman -Qi "$pkg" &>/dev/null; then
			missing+=("$pkg")
		else
			log_ok "$pkg is installed."
		fi
	done

	# Detect audio backend and check for BT audio support
	if pacman -Qi pipewire &>/dev/null; then
		log_info "PipeWire detected as audio server."
		if ! pacman -Qi pipewire-pulse &>/dev/null; then
			missing+=("pipewire-pulse")
		else
			log_ok "pipewire-pulse is installed."
		fi
	elif pacman -Qi pulseaudio &>/dev/null; then
		log_info "PulseAudio detected as audio server."
		if ! pacman -Qi pulseaudio-bluetooth &>/dev/null; then
			missing+=("pulseaudio-bluetooth")
		else
			log_ok "pulseaudio-bluetooth is installed."
		fi
	else
		log_warn "No PipeWire or PulseAudio detected. Bluetooth audio may not work."
	fi

	if [[ ${#missing[@]} -gt 0 ]]; then
		apply_fix "Installing missing packages: ${missing[*]}" \
			pacman -S --noconfirm "${missing[@]}"
	fi
}

# shellcheck source=lib/bt_adapter.sh
source "$SCRIPT_DIR/lib/bt_adapter.sh"
# shellcheck source=lib/bt_pairing.sh
source "$SCRIPT_DIR/lib/bt_pairing.sh"
# shellcheck source=lib/bt_audio.sh
source "$SCRIPT_DIR/lib/bt_audio.sh"
# shellcheck source=lib/bt_report.sh
source "$SCRIPT_DIR/lib/bt_report.sh"


# ==========================================================================
# Main
# ==========================================================================
main() {
	dump_diagnostics
	check_bluetooth_service
	check_packages
	check_firmware
	check_adapter_stuck
	remove_stale_pairing
	fix_usb_autosuspend
	check_pipewire_health
	restart_bluetooth

	echo ""
	echo "==========================================="
	printf "Fixes applied: %d | Skipped: %d\n" "$FIXES_APPLIED" "$FIXES_SKIPPED"
	echo "==========================================="

	if ! connect_device; then
		show_instructions
	fi

	set_audio_profile
}

main
