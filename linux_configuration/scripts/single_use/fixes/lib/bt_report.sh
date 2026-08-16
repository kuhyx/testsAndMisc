#!/bin/bash
# User instructions and the diagnostics dump.
#
# Sourced by fix_bluetooth.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

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
