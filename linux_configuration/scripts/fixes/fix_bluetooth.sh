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
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

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
	adapter_list=$(_btctl list | grep "^Controller" || true)

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

# ---------------------------------------------------------------------------
# Helper: check if A2DP services are resolved for a connected device
# Returns 0 if resolved, 1 otherwise.
# ---------------------------------------------------------------------------
_services_resolved() {
	local mac="$1"
	local dbus_path="/org/bluez/hci0/dev_${mac//:/_}"
	local result
	result=$(dbus-send --system --print-reply \
		--dest=org.bluez "$dbus_path" \
		org.freedesktop.DBus.Properties.Get \
		string:"org.bluez.Device1" string:"ServicesResolved" 2>/dev/null || true)
	echo "$result" | grep -q "boolean true"
}

# ---------------------------------------------------------------------------
# Helper: full reset cycle — btusb reload + service restarts + reconnect.
# Fixes stale HCI link state ("link tx timeout" / ServicesResolved stuck).
# ---------------------------------------------------------------------------
_full_adapter_reset_and_connect() {
	local mac="$1"

	log_info "Performing full adapter reset (btusb reload)..."
	_btctl disconnect "$mac" >/dev/null 2>&1 || true
	sleep 1

	modprobe -r btusb && sleep 2 && modprobe btusb && sleep 5
	systemctl restart bluetooth.service
	sleep 3

	_restart_pipewire_stack
	sleep 3

	log_info "Reconnecting to $mac after adapter reset..."
	{ echo "agent on"; echo "default-agent"; sleep 1; echo "power on"; sleep 1; echo "connect $mac"; sleep 20; } \
		| bluetoothctl 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Helper: verify the Bluetooth audio sink appeared in PipeWire.
# ---------------------------------------------------------------------------
_verify_audio_sink() {
	local mac="$1"
	local card_name="bluez_card.${mac//:/_}"

	if ! has_cmd pactl; then
		return 0
	fi

	# Give PipeWire time to create the audio card
	local _attempt
	for _attempt in 1 2 3 4 5; do
		if _run_as_user pactl list cards short 2>/dev/null | grep -q "$card_name"; then
			log_ok "Bluetooth audio card detected in PipeWire."
			return 0
		fi
		sleep 3
	done

	log_warn "Bluetooth audio card not found in PipeWire after connection."
	return 1
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

	local info
	info=$(_btctl info "$TARGET_MAC" || true)

	if echo "$info" | grep -q "Device $TARGET_MAC"; then
		local paired
		paired=$(echo "$info" | grep "Paired:" | awk '{print $2}')
		local connected
		connected=$(echo "$info" | grep "Connected:" | awk '{print $2}')

		if [[ $paired == "yes" && $connected == "no" ]]; then
			log_warn "Device is paired but NOT connected — may have stale pairing."
			apply_fix "Removing stale pairing for $TARGET_MAC" \
				_btctl remove "$TARGET_MAC"
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
# 7. Disable USB autosuspend for Bluetooth adapter
# ==========================================================================
fix_usb_autosuspend() {
	echo ""
	log_info "Checking USB autosuspend for Bluetooth adapter..."

	local bt_usb
	bt_usb=$(lsusb 2>/dev/null | grep -i bluetooth | head -1 || true)
	if [[ -z $bt_usb ]]; then
		return 0
	fi

	local usb_id
	usb_id=$(echo "$bt_usb" | grep -oP 'ID \K[0-9a-f]{4}:[0-9a-f]{4}' || true)
	if [[ -z $usb_id ]]; then
		return 0
	fi

	local vendor="${usb_id%%:*}"
	local product="${usb_id##*:}"

	# Find the sysfs device path
	local sysfs_path=""
	local dev_path
	for dev_path in /sys/bus/usb/devices/*/; do
		if [[ -f "${dev_path}idVendor" && -f "${dev_path}idProduct" ]]; then
			local v p
			v=$(cat "${dev_path}idVendor" 2>/dev/null || true)
			p=$(cat "${dev_path}idProduct" 2>/dev/null || true)
			if [[ $v == "$vendor" && $p == "$product" ]]; then
				sysfs_path="$dev_path"
				break
			fi
		fi
	done

	if [[ -z $sysfs_path ]]; then
		log_warn "Could not find sysfs path for BT adapter."
		return 0
	fi

	local power_control="${sysfs_path}power/control"
	if [[ -f $power_control ]]; then
		local current
		current=$(cat "$power_control" 2>/dev/null || true)
		if [[ $current != "on" ]]; then
			log_warn "USB autosuspend is enabled ($current) — can cause audio dropouts."
			apply_fix "Disabling USB autosuspend for BT adapter" \
				_disable_usb_autosuspend "$power_control" "$vendor" "$product"
		else
			log_ok "USB autosuspend already disabled."
		fi
	fi
}

_disable_usb_autosuspend() {
	local power_control="$1"
	local vendor="$2"
	local product="$3"

	# Immediate fix
	echo "on" > "$power_control"

	# Persistent udev rule
	local rule_file="/etc/udev/rules.d/50-bluetooth-no-autosuspend.rules"
	local rule="ACTION==\"add\", SUBSYSTEM==\"usb\", ATTR{idVendor}==\"$vendor\", ATTR{idProduct}==\"$product\", ATTR{power/control}=\"on\""

	if [[ ! -f $rule_file ]] || ! grep -qF "$vendor" "$rule_file" 2>/dev/null; then
		echo "$rule" > "$rule_file"
		udevadm control --reload-rules 2>/dev/null || true
		log_info "Created persistent udev rule: $rule_file"
	fi
}

# ==========================================================================
# 8. Check PipeWire/WirePlumber health (hung audio stack)
# ==========================================================================
check_pipewire_health() {
	echo ""
	log_info "Checking PipeWire/WirePlumber health..."

	if ! has_cmd wpctl; then
		log_info "wpctl not found — skipping PipeWire health check."
		return 0
	fi

	# Test if PipeWire is responding within 3 seconds
	if timeout 3 _run_as_user wpctl status &>/dev/null; then
		log_ok "PipeWire is responsive."
		return 0
	fi

	log_warn "PipeWire/WirePlumber appears hung (wpctl timed out)."
	apply_fix "Restarting PipeWire + WirePlumber audio stack" \
		_restart_pipewire_stack
}

# ---------------------------------------------------------------------------
# Helper: run a command as the actual (non-root) user with PipeWire env.
# Needed because pactl/wpctl/systemctl --user talk to the user session.
# ---------------------------------------------------------------------------
_run_as_user() {
	local target_user
	target_user="${SUDO_USER:-$USER}"
	local target_uid
	target_uid=$(id -u "$target_user")

	sudo -u "$target_user" \
		XDG_RUNTIME_DIR="/run/user/$target_uid" \
		DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$target_uid/bus" \
		"$@"
}

_restart_pipewire_stack() {
	_run_as_user systemctl --user restart pipewire pipewire-pulse wireplumber

	sleep 3
	log_info "Waiting for audio stack to initialize..."
}

# ==========================================================================
# 9. Auto-connect target device
# ==========================================================================
connect_device() {
	if [[ -z $TARGET_MAC ]]; then
		return 0
	fi

	echo ""
	log_info "Attempting to connect to $TARGET_MAC..."

	# Check if already connected
	local info
	info=$(_btctl info "$TARGET_MAC" || true)
	if echo "$info" | grep -q "Connected: yes"; then
		log_ok "Device $TARGET_MAC is already connected."
		return 0
	fi

	# Power on adapter
	_btctl power on >/dev/null || true
	sleep 1

	# ---- Attempt 1: direct connect (existing pairing) ----
	if echo "$info" | grep -q "Paired: yes"; then
		log_info "Device is already paired. Trying direct connect..."
		{ echo "agent on"; echo "default-agent"; sleep 1; echo "power on"; sleep 1; echo "connect $TARGET_MAC"; sleep 15; } \
			| bluetoothctl 2>/dev/null || true

		if _check_connection_health "$TARGET_MAC"; then
			return 0
		fi

		# Direct connect failed — remove stale pairing and try fresh
		log_warn "Direct connect failed. Removing stale pairing for fresh start."
		_btctl remove "$TARGET_MAC" >/dev/null || true
		sleep 2
	fi

	# ---- Attempt 2: scan + pair from scratch ----
	log_info "Scanning for $TARGET_MAC (20 seconds)..."
	log_info "Make sure the device is in pairing mode."
	{ echo "power on"; sleep 1; echo "scan on"; sleep 20; echo "scan off"; sleep 2; } \
		| bluetoothctl 2>/dev/null || true

	# Check if device was found
	local devices
	devices=$(_btctl devices || true)
	if ! echo "$devices" | grep -qi "$TARGET_MAC"; then
		log_error "Device $TARGET_MAC not found during scan."
		log_info "Put the device in pairing mode and re-run the script."
		return 1
	fi

	log_ok "Device found during scan."

	# Pair
	log_info "Pairing..."
	{ echo "agent on"; echo "default-agent"; sleep 1; echo "power on"; sleep 1; echo "pair $TARGET_MAC"; sleep 5; } \
		| bluetoothctl 2>/dev/null || true

	# Trust (so it auto-reconnects in the future)
	log_info "Trusting..."
	{ echo "trust $TARGET_MAC"; sleep 2; } | bluetoothctl 2>/dev/null || true

	# Connect
	log_info "Connecting..."
	{ echo "agent on"; echo "default-agent"; sleep 1; echo "power on"; sleep 1; echo "connect $TARGET_MAC"; sleep 15; } \
		| bluetoothctl 2>/dev/null || true

	# Verify connection + services + audio
	if _check_connection_health "$TARGET_MAC"; then
		return 0
	fi

	log_error "Connection to $TARGET_MAC failed."
	log_info "Try putting the device in pairing mode and re-run."
	return 1
}

# ---------------------------------------------------------------------------
# Helper: verify connection is fully healthy (connected + services + audio).
# If connected but services stuck, triggers full adapter reset + retry.
# ---------------------------------------------------------------------------
_check_connection_health() {
	local mac="$1"
	local info

	sleep 2
	info=$(_btctl info "$mac" || true)

	# Not connected at all
	if ! echo "$info" | grep -q "Connected: yes"; then
		return 1
	fi

	# Connected — check if A2DP services resolved
	local _attempt
	for _attempt in 1 2 3; do
		if _services_resolved "$mac"; then
			log_ok "Connected to $mac with A2DP services resolved."
			_verify_audio_sink "$mac" || true
			return 0
		fi
		sleep 3
	done

	# Connected but ServicesResolved stuck at false — stale HCI link state.
	log_warn "Connected but A2DP services not resolved (stale HCI link state)."
	apply_fix "Full adapter reset to fix stale link" \
		_full_adapter_reset_and_connect "$mac"

	# Verify after reset
	sleep 3
	if _services_resolved "$mac"; then
		log_ok "Connected to $mac with A2DP services resolved after reset."
		_verify_audio_sink "$mac" || true
		return 0
	fi

	return 1
}

# ==========================================================================
# 10. Set audio profile (avoid SBC-XQ dropouts on older adapters)
# ==========================================================================
set_audio_profile() {
	if [[ -z $TARGET_MAC ]]; then
		return 0
	fi

	if ! has_cmd pactl; then
		return 0
	fi

	echo ""
	log_info "Checking audio profile..."

	# Wait a moment for PipeWire to set up the audio card
	sleep 3

	local card_name="bluez_card.${TARGET_MAC//:/_}"
	local card_info
	card_info=$(_run_as_user pactl list cards 2>/dev/null || true)

	if ! echo "$card_info" | grep -q "$card_name"; then
		log_info "No PipeWire audio card found for device (may not be an audio device)."
		return 0
	fi

	local current_profile
	current_profile=$(echo "$card_info" | grep -A 50 "$card_name" | grep "Active Profile:" | head -1 | awk '{print $3}' || true)

	if [[ $current_profile == *"sbc_xq"* ]]; then
		log_warn "SBC-XQ codec active — may cause audio dropouts on older adapters."
		apply_fix "Switching to standard SBC codec" \
			_run_as_user pactl set-card-profile "$card_name" a2dp-sink
	elif [[ -n $current_profile ]]; then
		log_ok "Audio profile: $current_profile"
	fi
}

# ==========================================================================
# 11. Show connection instructions
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
# 12. Dump diagnostic info
# ==========================================================================
dump_diagnostics() {
	echo ""
	log_info "=== Diagnostic Summary ==="

	echo ""
	echo "--- Bluetooth adapter ---"
	_btctl show | grep -v '\[bluetoothctl\]' | head -20 || true

	echo ""
	echo "--- Known devices ---"
	_btctl devices | grep '^Device' || true

	echo ""
	echo "--- Loaded Bluetooth kernel modules ---"
	lsmod | grep -i bluetooth || echo "(none loaded)"

	echo ""
	echo "--- rfkill status ---"
	rfkill list bluetooth 2>/dev/null || echo "(rfkill not available)"

	if [[ -n $TARGET_MAC ]]; then
		echo ""
		echo "--- Device info: $TARGET_MAC ---"
		_btctl info "$TARGET_MAC" || echo "(device not known)"
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
