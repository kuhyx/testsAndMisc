#!/bin/bash
# Stale pairing removal, service restart and USB autosuspend.
#
# Sourced by fix_bluetooth.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

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
	echo "on" >"$power_control"

	# Persistent udev rule. UDEV_RULES_DIR defaults to the real directory and
	# is only overridden by the test suite, which cannot be allowed to write
	# to /etc: lib/tests/run_all.sh runs UN-jailed in ci_mirror.sh and in CI,
	# so a bind mount would protect the coverage run and nothing else.
	local rule_file="${UDEV_RULES_DIR:-/etc/udev/rules.d}/50-bluetooth-no-autosuspend.rules"
	local rule="ACTION==\"add\", SUBSYSTEM==\"usb\", ATTR{idVendor}==\"$vendor\", ATTR{idProduct}==\"$product\", ATTR{power/control}=\"on\""

	if [[ ! -f $rule_file ]] || ! grep -qF "$vendor" "$rule_file" 2>/dev/null; then
		echo "$rule" >"$rule_file"
		udevadm control --reload-rules 2>/dev/null || true
		log_info "Created persistent udev rule: $rule_file"
	fi
}
