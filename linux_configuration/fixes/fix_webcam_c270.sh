#!/bin/bash

# ============================================================================
# Logitech C270: keep a steady 30 fps in low light (udev rule)
#
# Disables exposure_dynamic_framerate on every plug-in/boot, so auto exposure
# can no longer drop the camera to ~15 fps. Trade-off: a darker image in dim
# rooms. Rationale lives in 99-c270-fixed-framerate.rules.
#
#   fix_webcam_c270.sh            install the rule and apply it now
#   fix_webcam_c270.sh --remove   remove the rule (camera default returns on replug)
#   fix_webcam_c270.sh --status   show rule state and the live control value
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME SCRIPT_DIR
readonly RULE_NAME="99-c270-fixed-framerate.rules"
readonly RULE_SRC="$SCRIPT_DIR/$RULE_NAME"
readonly RULE_DST="/etc/udev/rules.d/$RULE_NAME"
readonly CONTROL="exposure_dynamic_framerate"
# Overridable so the tests can point it at a fake sysfs tree.
readonly V4L_SYSFS="${C270_V4L_SYSFS:-/sys/class/video4linux}"

log() { echo "[$SCRIPT_NAME] $*"; }

# The C270's capture node (index 0); empty when the camera is unplugged.
find_device() {
	local node
	for node in "$V4L_SYSFS"/video*; do
		[[ -e "$node" ]] || continue
		if [[ "$(cat "$node/index")" == 0 ]] &&
			grep -qx 0825 "$node/device/../idProduct" 2>/dev/null &&
			grep -qx 046d "$node/device/../idVendor" 2>/dev/null; then
			echo "/dev/$(basename "$node")"
			return
		fi
	done
}

install_rule() {
	pacman -Q v4l-utils &>/dev/null || sudo pacman -S --needed --noconfirm v4l-utils
	sudo install -m 644 "$RULE_SRC" "$RULE_DST"
	sudo udevadm control --reload
	log "installed $RULE_DST"
	local dev
	dev="$(find_device)"
	if [[ -n "$dev" ]]; then
		v4l2-ctl -d "$dev" -c "$CONTROL=0"
		log "applied to $dev now"
	else
		log "C270 not plugged in; rule applies on next plug-in"
	fi
}

remove_rule() {
	sudo rm -f "$RULE_DST"
	sudo udevadm control --reload
	log "removed $RULE_DST"
}

show_status() {
	if [[ -f "$RULE_DST" ]]; then
		log "rule: installed"
	else
		log "rule: not installed"
	fi
	local dev
	dev="$(find_device)"
	if [[ -n "$dev" ]]; then
		log "$dev: $(v4l2-ctl -d "$dev" -C "$CONTROL")"
	else
		log "C270 not plugged in"
	fi
}

case "${1:-}" in
"") install_rule ;;
--remove) remove_rule ;;
--status) show_status ;;
-h | --help) sed -n '4,13p' "$0" | sed 's/^# \{0,3\}//' ;;
*)
	log "unknown option: $1"
	exit 2
	;;
esac
