#!/usr/bin/env bash

# Fix Bluetooth connectivity issues on Arch Linux
#
# Common issues addressed:
# 1. Bluetooth service not running or in bad state
# 2. Missing PipeWire/PulseAudio Bluetooth audio support (A2DP sink)
# 3. Stale pairing data causing connection hangs
# 4. Missing Broadcom firmware (.hcd files)
# 5. Stuck/unresponsive adapter requiring USB reset
#
# Usage:
#   ./fix_bluetooth.sh                          # Diagnose and fix all issues
#   ./fix_bluetooth.sh --interactive            # Prompt before each fix
#   ./fix_bluetooth.sh <MAC>                    # Target a specific device
#   ./fix_bluetooth.sh --interactive <MAC>      # Both
#
# Safe to re-run: all fixes are idempotent.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

parse_interactive_args "$@"
shift "$COMMON_ARGS_SHIFT"

TARGET_MAC="${1:-}"

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

# ==========================================================================
# 3. Check for missing Broadcom firmware
# ==========================================================================
check_firmware() {
	echo ""
	log_info "Checking for missing Bluetooth firmware..."

	local missing_fw
	missing_fw=$(dmesg 2>/dev/null | grep -o "brcm/BCM[^ ']*\.hcd" | sort -u || true)

	if [[ -z $missing_fw ]]; then
		log_ok "No missing firmware detected in dmesg."
		return 0
	fi

	local fw_name
	for fw_name in $missing_fw; do
		local fw_path="/usr/lib/firmware/$fw_name"
		if [[ -f $fw_path ]]; then
			log_ok "Firmware $fw_name already installed."
			continue
		fi

		local basename
		basename=$(basename "$fw_name")
		local url="https://github.com/winterheart/broadcom-bt-firmware/raw/master/brcm/$basename"

		log_warn "Missing firmware: $fw_name"
		apply_fix "Downloading $basename from broadcom-bt-firmware repo" \
			_download_firmware "$url" "$fw_path"
	done
}

_download_firmware() {
	local url="$1"
	local dest="$2"
	mkdir -p "$(dirname "$dest")"
	wget -q "$url" -O "$dest" || curl -sL "$url" -o "$dest"
}

# ==========================================================================
# 4. Reset stuck adapter via USB reset
# ==========================================================================
check_adapter_stuck() {
	echo ""
	log_info "Checking if Bluetooth adapter is responsive..."

	# Test if bluetoothctl can see the adapter
	local adapter_list
	adapter_list=$(echo "list" | bluetoothctl 2>/dev/null | grep "^Controller" || true)

	if [[ -n $adapter_list ]]; then
		log_ok "Adapter is responsive: $adapter_list"
		return 0
	fi

	log_warn "Adapter not responding to bluetoothctl."

	# Try USB reset if usbreset is available
	local bt_usb
	bt_usb=$(lsusb 2>/dev/null | grep -i bluetooth | head -1 || true)
	if [[ -n $bt_usb ]]; then
		local usb_id
		usb_id=$(echo "$bt_usb" | grep -oP 'ID \K[0-9a-f]{4}:[0-9a-f]{4}')
		if [[ -n $usb_id ]] && has_cmd usbreset; then
			apply_fix "USB-resetting Bluetooth adapter ($usb_id)" \
				usbreset "$usb_id"
		else
			log_info "Falling back to btusb module reload..."
			apply_fix "Reloading btusb kernel module" \
				_reload_btusb
		fi
	else
		log_error "No USB Bluetooth adapter found. Is the dongle plugged in?"
	fi
}

_reload_btusb() {
	modprobe -r btusb && sleep 1 && modprobe btusb && sleep 2
}

# ==========================================================================
# 5. Remove stale pairing for target device (if specified)
# ==========================================================================
remove_stale_pairing() {
	if [[ -z $TARGET_MAC ]]; then
		return 0
	fi

	echo ""
	log_info "Checking for stale pairing with $TARGET_MAC..."

	if bluetoothctl info "$TARGET_MAC" 2>/dev/null | grep -q "Device $TARGET_MAC"; then
		local paired
		paired=$(bluetoothctl info "$TARGET_MAC" 2>/dev/null | grep "Paired:" | awk '{print $2}')
		local connected
		connected=$(bluetoothctl info "$TARGET_MAC" 2>/dev/null | grep "Connected:" | awk '{print $2}')

		if [[ $paired == "yes" && $connected == "no" ]]; then
			log_warn "Device is paired but NOT connected — may have stale pairing."
			apply_fix "Removing stale pairing for $TARGET_MAC" \
				bluetoothctl remove "$TARGET_MAC"
		elif [[ $paired == "no" ]]; then
			log_info "Device is not currently paired."
		else
			log_ok "Device is paired and connected."
		fi
	else
		log_info "Device $TARGET_MAC not found in bluetoothctl. Fresh pairing needed."
	fi
}

# ==========================================================================
# 6. Restart Bluetooth service to apply changes
# ==========================================================================
restart_bluetooth() {
	echo ""
	if [[ $FIXES_APPLIED -gt 0 ]]; then
		apply_fix "Restarting bluetooth.service to apply changes" \
			systemctl restart bluetooth.service
	else
		log_info "No fixes applied — skipping service restart."
	fi
}

# ==========================================================================
# 7. Show connection instructions
# ==========================================================================
show_instructions() {
	echo ""
	echo "==========================================="
	echo " Next Steps"
	echo "==========================================="
	echo ""
	echo "1. Put your Bluetooth device in PAIRING mode"
	echo "   (e.g., hold the Bluetooth button until LED blinks rapidly)"
	echo ""
	echo "2. In bluetoothctl:"
	if [[ -n $TARGET_MAC ]]; then
		cat <<EOF
      scan on
      # Wait for device to appear
      pair $TARGET_MAC
      trust $TARGET_MAC
      connect $TARGET_MAC
EOF
	else
		cat <<EOF
      scan on
      # Wait for device to appear, note its MAC address
      pair <MAC>
      trust <MAC>
      connect <MAC>
EOF
	fi
	echo ""
	echo "3. If connection still fails, check logs:"
	echo "      journalctl -u bluetooth -f"
	echo ""
}

# ==========================================================================
# 8. Dump diagnostic info
# ==========================================================================
dump_diagnostics() {
	echo ""
	log_info "=== Diagnostic Summary ==="

	echo ""
	echo "--- Bluetooth adapter ---"
	echo "show" | bluetoothctl 2>/dev/null | grep -v '\[bluetoothctl\]' | head -20 || true

	echo ""
	echo "--- Known devices ---"
	echo "devices" | bluetoothctl 2>/dev/null | grep '^Device' || true

	echo ""
	echo "--- Loaded Bluetooth kernel modules ---"
	lsmod | grep -i bluetooth || echo "(none loaded)"

	echo ""
	echo "--- rfkill status ---"
	rfkill list bluetooth 2>/dev/null || echo "(rfkill not available)"

	if [[ -n $TARGET_MAC ]]; then
		echo ""
		echo "--- Device info: $TARGET_MAC ---"
		bluetoothctl info "$TARGET_MAC" 2>/dev/null || echo "(device not known)"
	fi

	echo ""
	echo "--- Recent bluetooth journal entries ---"
	journalctl -u bluetooth --no-pager -n 20 2>/dev/null || true
}

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
	restart_bluetooth

	echo ""
	echo "==========================================="
	printf "Fixes applied: %d | Skipped: %d\n" "$FIXES_APPLIED" "$FIXES_SKIPPED"
	echo "==========================================="

	show_instructions
}

main
