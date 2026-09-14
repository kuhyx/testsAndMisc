#!/bin/bash

# ============================================================================
# Logitech G29: replace the in-tree hid-logitech FFB driver with new-lg4ff
#
# new-lg4ff (github.com/berarma/new-lg4ff) adds spring/damper/friction and
# periodic effects the in-tree lg4ff lacks (it only has constant force). Its
# dkms.conf installs the module AS hid-logitech under updates/dkms/, so it
# shadows the in-tree copy by name: no blacklist, no modules-load drop-in.
# Why this matters for BeamNG and the SDL env vars: ../docs/DOCS-g29-ffb.md.
#
#   install_new_lg4ff.sh            install from AUR, reload, regen initramfs
#   install_new_lg4ff.sh --status   which module owns the wheel + FFB caps
#   install_new_lg4ff.sh --revert   remove the package, back to in-tree
#
# Run as the desktop user (yay refuses root); sudo is used where needed.
# The initramfs regen is required: mkinitcpio's autodetect hook bundles
# hid-logitech because the wheel is plugged in at build time, and a stale
# in-tree copy in the initramfs would win at boot over the DKMS one.
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME SCRIPT_DIR
readonly AUR_PKG="new-lg4ff-dkms-git"
readonly DKMS_NAME="new-lg4ff"
readonly MODULE="hid_logitech"
readonly VID_PID="046D:C24F"
readonly SHIFTER_FIX="$SCRIPT_DIR/fix_g29_shifter.sh"
readonly PACKAGES=(dkms joyutils)

MODE="install"

usage() {
	sed -n '4,16p' "$0" | sed 's/^# \{0,3\}//'
	exit 0
}

log() { echo "[$SCRIPT_NAME] $*"; }
die() {
	echo "[$SCRIPT_NAME] ERROR: $*" >&2
	exit 1
}

install_packages() {
	local -a missing=()
	local pkg
	for pkg in "${PACKAGES[@]}"; do
		pacman -Q "$pkg" &>/dev/null || missing+=("$pkg")
	done
	if ((${#missing[@]})); then
		log "installing: ${missing[*]}"
		sudo pacman -S --needed --noconfirm "${missing[@]}"
	fi
	# Headers for the RUNNING kernel, or dkms builds for a kernel nobody boots.
	[[ -d "/usr/lib/modules/$(uname -r)/build" ]] ||
		die "no headers for $(uname -r): install the matching linux*-headers"
}

# Path of the module modprobe would load: updates/dkms/... means new-lg4ff.
module_path() { modinfo -F filename "$MODULE" 2>/dev/null || echo "-"; }

is_new_lg4ff_active() {
	# The DKMS module registers itself as hid-logitech-new even though the
	# file is named hid-logitech; /proc/modules shows the registered name.
	grep -q '^hid_logitech_new ' /proc/modules
}

wheel_event_dev() {
	readlink -f /dev/input/by-id/usb-Logitech_G29_Driving_Force_Racing_Wheel-event-joystick 2>/dev/null || true
}

# Unbind and rebind the wheel so the freshly installed module takes over
# without a reboot. hid core rebinds the device on modprobe by itself.
reload_module() {
	log "reloading $MODULE"
	sudo modprobe -r "$MODULE"
	sudo modprobe "$MODULE"
	sleep 1
}

regen_initramfs() {
	# Only the images that actually carry the module need rebuilding.
	local img rebuilt=0
	for img in /boot/initramfs-*.img; do
		[[ -f $img ]] || continue
		if lsinitcpio -l "$img" 2>/dev/null | grep -q 'hid-logitech'; then
			rebuilt=1
		fi
	done
	if ((rebuilt)); then
		log "initramfs bundles hid-logitech: regenerating all presets"
		sudo mkinitcpio -P
	else
		log "initramfs does not bundle hid-logitech: nothing to regenerate"
	fi
}

show_status() {
	local dev caps
	log "package: $(pacman -Q "$AUR_PKG" 2>/dev/null || echo 'not installed')"
	# `dkms status <name>` is a prefix filter that prints everything on a miss.
	log "dkms: $(dkms status 2>/dev/null | grep "^$DKMS_NAME/" || echo 'none')"
	log "module file: $(module_path)"
	if is_new_lg4ff_active; then
		log "loaded now: hid-logitech-new (new-lg4ff)"
	elif grep -q '^hid_logitech ' /proc/modules; then
		log "loaded now: hid_logitech (in-tree)"
	else
		log "loaded now: none"
	fi
	local d
	for d in /sys/bus/hid/devices/*"$VID_PID"*; do
		[[ -e $d ]] || continue
		# USB interface 1 is unbound by design (hid-lg rejects it); only
		# interface 0 carries the wheel, so "none" there is normal.
		if [[ -e $d/driver ]]; then
			log "$(basename "$d") driver: $(basename "$(readlink -f "$d/driver")")"
		else
			log "$(basename "$d") driver: none"
		fi
	done
	dev="$(wheel_event_dev)"
	if [[ -n $dev ]]; then
		caps="$(cat "/sys/class/input/$(basename "$dev")/device/capabilities/ff")"
		# In-tree lg4ff: "300040000 0" (constant, gain, autocenter only).
		log "evdev $dev ff caps: $caps"
		local sysdev
		sysdev="$(readlink -f "/sys/class/input/$(basename "$dev")/device/device")"
		local knob
		for knob in range gain autocenter spring_level damper_level friction_level; do
			[[ -f $sysdev/$knob ]] && log "  $knob=$(cat "$sysdev/$knob")"
		done
	else
		log "wheel: not plugged in"
	fi
	# An `&&` list as the last statement would make the function return 1
	# when the shifter fix is absent, and set -e would abort on it.
	if [[ -x $SHIFTER_FIX ]]; then
		"$SHIFTER_FIX" --status | sed 's/^/  shifter: /'
	fi
}

do_install() {
	install_packages
	if pacman -Q "$AUR_PKG" &>/dev/null; then
		log "$AUR_PKG already installed"
	else
		command -v yay >/dev/null || die "yay not found; install it first"
		log "installing $AUR_PKG from AUR (builds against $(uname -r))"
		yay -S --needed --noconfirm "$AUR_PKG"
	fi
	dkms status | grep "^$DKMS_NAME/" | grep -q "$(uname -r).*installed" ||
		die "dkms did not install $DKMS_NAME for $(uname -r): $(dkms status | grep "^$DKMS_NAME/")"
	[[ "$(module_path)" == */updates/dkms/* ]] ||
		die "modprobe still resolves $MODULE to $(module_path)"
	regen_initramfs
	if [[ -n "$(wheel_event_dev)" ]]; then
		reload_module
		is_new_lg4ff_active || die "reload done but hid_logitech_new is not loaded"
	else
		log "wheel not plugged in: module swap takes effect on next plug/boot"
	fi
	show_status
	log "done. Feel check: fftest $(wheel_event_dev)"
}

do_revert() {
	if pacman -Q "$AUR_PKG" &>/dev/null; then
		# The dkms pacman hook removes the module from updates/dkms/.
		sudo pacman -Rns --noconfirm "$AUR_PKG"
	else
		log "$AUR_PKG not installed"
	fi
	sudo depmod -a
	[[ "$(module_path)" != */updates/dkms/* ]] ||
		die "in-tree module not restored: $(module_path)"
	regen_initramfs
	if [[ -n "$(wheel_event_dev)" ]]; then
		reload_module
		! is_new_lg4ff_active || die "reload done but hid_logitech_new still loaded"
	fi
	show_status
}

main() {
	case "$MODE" in
	install) do_install ;;
	revert) do_revert ;;
	status) show_status ;;
	esac
}

while [[ $# -gt 0 ]]; do
	case $1 in
	--status) MODE="status" ;;
	--revert) MODE="revert" ;;
	-h | --help) usage ;;
	*)
		echo "Unknown option: $1" >&2
		exit 1
		;;
	esac
	shift
done

main
