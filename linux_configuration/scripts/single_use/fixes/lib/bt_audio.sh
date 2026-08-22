#!/bin/bash
# PipeWire health, device connection and audio profile.
#
# Sourced by fix_bluetooth.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

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

	# Timeout goes INSIDE _run_as_user: `timeout` is a binary and cannot
	# invoke a shell function, so wrapping it outside always returned 127
	# and reported a healthy PipeWire as hung.
	if _run_as_user timeout 3 wpctl status &>/dev/null; then
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
		{
			echo "agent on"
			echo "default-agent"
			sleep 1
			echo "power on"
			sleep 1
			echo "connect $TARGET_MAC"
			sleep 15
		} |
			bluetoothctl 2>/dev/null || true

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
	{
		echo "power on"
		sleep 1
		echo "scan on"
		sleep 20
		echo "scan off"
		sleep 2
	} |
		bluetoothctl 2>/dev/null || true

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
	{
		echo "agent on"
		echo "default-agent"
		sleep 1
		echo "power on"
		sleep 1
		echo "pair $TARGET_MAC"
		sleep 5
	} |
		bluetoothctl 2>/dev/null || true

	# Trust (so it auto-reconnects in the future)
	log_info "Trusting..."
	{
		echo "trust $TARGET_MAC"
		sleep 2
	} | bluetoothctl 2>/dev/null || true

	# Connect
	log_info "Connecting..."
	{
		echo "agent on"
		echo "default-agent"
		sleep 1
		echo "power on"
		sleep 1
		echo "connect $TARGET_MAC"
		sleep 15
	} |
		bluetoothctl 2>/dev/null || true

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
