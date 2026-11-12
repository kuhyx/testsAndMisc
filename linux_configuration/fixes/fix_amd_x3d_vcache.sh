#!/bin/bash

# ============================================================================
# AMD X3D: set the V-cache scheduling mode to "cache" (udev rule)
#
# The scheduler then prefers the V-cache CCD for games. The rule re-applies the
# setting on every boot and driver rebind; rationale lives in
# 60-amd-x3d-vcache-mode.rules.
#
#   fix_amd_x3d_vcache.sh            install the rule and apply it now
#   fix_amd_x3d_vcache.sh --remove   remove the rule (firmware default returns on reboot)
#   fix_amd_x3d_vcache.sh --status   show rule state and the live mode
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME SCRIPT_DIR
readonly RULE_NAME="60-amd-x3d-vcache-mode.rules"
readonly RULE_SRC="$SCRIPT_DIR/$RULE_NAME"
# Both overridable so the tests can point them at a scratch tree.
readonly RULE_DST="${X3D_RULES_DIR:-/etc/udev/rules.d}/$RULE_NAME"
readonly DRIVER_SYSFS="${X3D_DRIVER_SYSFS:-/sys/bus/platform/drivers/amd_x3d_vcache}"

log() { echo "[$SCRIPT_NAME] $*"; }

# Live mode of every bound X3D device, one "<device>=<mode>" per line.
live_modes() {
	local f
	for f in "$DRIVER_SYSFS"/*/amd_x3d_mode; do
		[[ -e $f ]] || continue
		echo "$(basename "$(dirname "$f")")=$(cat "$f")"
	done
}

install_rule() {
	sudo install -m 644 "$RULE_SRC" "$RULE_DST"
	sudo udevadm control --reload
	log "installed $RULE_DST"
	# No driver, or a driver with no device (a VM): nothing to apply yet.
	if [[ -z "$(live_modes)" ]]; then
		log "no X3D device; rule applies when the driver binds"
		return
	fi
	# A synthetic bind event runs the rule against the live device by driver,
	# so no device name is needed here either.
	sudo udevadm trigger --action=bind --subsystem-match=platform \
		--property-match=DRIVER=amd_x3d_vcache
	sudo udevadm settle --timeout=10
	local modes
	modes="$(live_modes)"
	if [[ -n $modes ]] && ! grep -qv '=cache$' <<<"$modes"; then
		log "applied: $modes"
	else
		log "mode is not cache after trigger: ${modes:-no device}"
		exit 1
	fi
}

remove_rule() {
	sudo rm -f "$RULE_DST"
	sudo udevadm control --reload
	log "removed $RULE_DST"
}

show_status() {
	if [[ -f $RULE_DST ]]; then
		log "rule: installed"
	else
		log "rule: not installed"
	fi
	log "mode: $(live_modes | tr '\n' ' ')"
}

case "${1:-}" in
"") install_rule ;;
--remove) remove_rule ;;
--status) show_status ;;
-h | --help) sed -n '4,12p' "$0" | sed 's/^# \{0,3\}//' ;;
*)
	log "unknown option: $1"
	exit 2
	;;
esac
