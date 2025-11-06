#!/usr/bin/env bash

# Fix/diagnose Xbox One (and 360) controllers on Arch Linux over USB.
# - Detects the device, relevant kernel modules, and evdev/joystick nodes
# - Loads safe modules (xpad, joydev) if missing
# - Shows dmesg hints and permission status
# - Suggests next steps (packages to test: evtest, joystick; drivers for BT/dongle)
#
# Conventions: sudo re-exec, idempotent, log with timestamps.

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
LOG_FILE="/var/log/xbox-controller-fix.log"

timestamp() { date '+%Y-%m-%d %H:%M:%S%z'; }

log() {
	local msg="$1"
	echo "[$(timestamp)] $msg"
	if [[ -w "$(dirname "$LOG_FILE")" ]] || [[ ! -e "$LOG_FILE" && -w /var/log ]]; then
		echo "[$(timestamp)] $msg" >>"$LOG_FILE" || true
	fi
}

require_root() {
	if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
		echo "$SCRIPT_NAME needs root to load kernel modules and read some diagnostics. Re-executing with sudo..."
		exec sudo -E bash "$0" "$@"
	fi
}

print_header() {
	echo "=== $1 ==="
}

detect_distro() {
	if command -v pacman >/dev/null 2>&1; then
		echo "arch"
	else
		echo "other"
	fi
}

list_input_nodes() {
	print_header "Input device nodes"
	ls -l /dev/input/by-id 2>/dev/null | sed -n '1,120p' || true
	echo
	if compgen -G "/dev/input/*js*" >/dev/null; then
		ls -l /dev/input/js* || true
	else
		echo "No legacy /dev/input/js* nodes (joydev) present. That's okay for most apps using evdev."
	fi
	echo
}

show_lsusb() {
	print_header "USB devices (filtered)"
	if command -v lsusb >/dev/null 2>&1; then
		lsusb | grep -Ei 'microsoft|xbox|045e:' || { echo "No Microsoft/Xbox device found via lsusb."; true; }
	else
		echo "lsusb not found (usbutils). Install usbutils for richer diagnostics."
	fi
	echo
}

show_modules() {
	print_header "Kernel modules state"
	lsmod | grep -E '(^|\s)(xpad|joydev|hid_microsoft|hid_generic|hid_xpadneo|xone)(\s|$)' || echo "No matching modules currently loaded."
	echo
}

modprobe_safe() {
	local mod="$1"
	if ! lsmod | grep -q "^${mod}\b"; then
		if modprobe "$mod" 2>/dev/null; then
			log "Loaded module: $mod"
		else
			log "Module $mod not loaded (may be built-in or unavailable)."
		fi
	fi
}

show_dmesg_hints() {
	print_header "Recent kernel messages (xpad/xbox/hid/input)"
	dmesg --color=never | grep -Ei 'xbox|xpad|045e:|Microsoft|input:.*gamepad|event.*joystick|hid.*(xbox|microsoft)' | tail -n 200 || true
	echo
}

check_permissions() {
	print_header "Permissions on event/joystick nodes"
	local any=0
	for path in /dev/input/by-id/*-event-joystick /dev/input/js*; do
		if [[ -e "$path" ]]; then
			any=1
			printf '%s -> ' "$path"
			local dev
			dev=$(readlink -f "$path" 2>/dev/null || echo "$path")
			stat -c '%A %a %U:%G %n' "$dev" 2>/dev/null || true
		fi
	done
	if [[ $any -eq 0 ]]; then
		echo "No event-joystick or js nodes found to check permissions."
	fi
	echo
	if [[ $(detect_distro) == "arch" ]]; then
		echo "On Arch, prefer TAG+\"uaccess\"-based access over adding users to the 'input' group."
		echo "If access is denied in apps, install: pacman -S game-devices-udev (provides modern udev rules)."
	fi
	echo
}

suggest_tests() {
	print_header "Next steps / tests"
	echo "- Test evdev: install 'evtest' and run: evtest /dev/input/by-id/*-event-joystick"
	echo "- Test joystick API: install 'joystick' (jstest) and run: jstest /dev/input/js0 (if present)"
	echo "- For force feedback test (rumble): install 'linuxconsole' (fftest): fftest /dev/input/by-id/*-event-joystick"
	echo
	echo "Steam users: Ensure Steam Input settings match your use case. If rumble fails in SDL titles, try: SDL_JOYSTICK_HIDAPI=0"
	echo
	echo "If you are actually using Bluetooth: consider xpadneo (AUR: xpadneo-dkms)."
	echo "If you are using the official wireless USB adapter: consider xone (AUR: xone-dkms and xone-dongle-firmware)."
	echo
}

main() {
	require_root "$@"
	print_header "${SCRIPT_NAME} starting"
	log "Kernel: $(uname -r) | Distro: $(detect_distro)"

	show_lsusb
	show_modules

	# Load common modules safely (idempotent)
	modprobe_safe usbhid
	modprobe_safe xpad
	modprobe_safe joydev

		# If xpad failed to load and kernel says it's a module, but it's not present, hint about out-of-sync modules
		if ! lsmod | grep -q '^xpad\b'; then
			if command -v zcat >/dev/null 2>&1 && [[ -r /proc/config.gz ]] && zcat /proc/config.gz 2>/dev/null | grep -q '^CONFIG_JOYSTICK_XPAD=m'; then
				if ! find "/lib/modules/$(uname -r)" -type f -name 'xpad*.ko*' 2>/dev/null | grep -q .; then
					log "xpad is configured as a module but missing under /lib/modules/$(uname -r). Your kernel modules may be out-of-sync or incomplete."
					if [[ $(detect_distro) == "arch" ]]; then
						echo "Arch hint: reinstall the matching kernel package (e.g. 'sudo pacman -S linux' or your variant like linux-zen) and reboot."
					else
						echo "Hint: reinstall your running kernel's modules then reboot."
					fi
					echo
				fi
			fi
		fi

	list_input_nodes
	check_permissions
	show_dmesg_hints

	# Simple heuristic: do we see an Xbox/Microsoft event-joystick?
		if compgen -G "/dev/input/by-id/*-event-joystick" >/dev/null; then
			local found_label=0
			for f in /dev/input/by-id/*-event-joystick; do
				[[ -e "$f" ]] || continue
				if printf '%s' "$(basename "$f")" | grep -Eqi 'xbox|microsoft|controller|wireless'; then
					found_label=1
					break
				fi
			done
			if (( found_label == 1 )); then
				log "Controller event device detected."
			else
				log "Event-joystick device(s) exist but not obviously Xbox-labelled. Still likely usable."
			fi
		else
		log "No -event-joystick device found. If the controller vibrated but no input node exists, check the cable and try another USB port/cable."
		log "Also check dmesg for descriptor errors; for Xbox 360 Play&Charge cable: note it only charges and does not carry input."
	fi

	suggest_tests

	print_header "Done"
}

main "$@"

