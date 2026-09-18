#!/bin/bash

# ============================================================================
# Logitech G29 Driving Force Shifter: make 1st/3rd engage reliably (HID-BPF)
#
# Builds g29_shifter.bpf.c (same dir) against the udev-hid-bpf headers and
# attaches it to the wheel. Why and what the numbers mean: ../docs/DOCS-g29-shifter.md.
#
#   fix_g29_shifter.sh            build + persistent install (udev rule)
#   fix_g29_shifter.sh --test     build + attach until unplug/--remove only
#   fix_g29_shifter.sh --remove   detach from the running device
#   fix_g29_shifter.sh --ensure   attach only if not attached (used by systemd)
#   fix_g29_shifter.sh --status   show whether a program is attached
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME SCRIPT_DIR
readonly SRC="$SCRIPT_DIR/g29_shifter.bpf.c"
readonly HEADERS_REPO="https://gitlab.freedesktop.org/libevdev/udev-hid-bpf.git"
readonly HEADERS_TAG="2.3.0-20260703" # must match the installed udev-hid-bpf
# HOME is unset under systemd, and `set -u` would abort before --ensure runs.
readonly CACHE_DIR="${XDG_CACHE_HOME:-${HOME:-/var/cache}/.cache}/g29_shifter"
readonly HEADERS_DIR="$CACHE_DIR/udev-hid-bpf"
readonly BUILD_DIR="$CACHE_DIR/build"
readonly OBJ="$BUILD_DIR/g29_shifter.bpf.o"
readonly INSTALLED_OBJ="/etc/udev-hid-bpf/g29_shifter.bpf.o"
readonly INSTALLED_RULE="/etc/udev/rules.d/99-hid-bpf-g29_shifter.rules"
readonly UNIT_NAME="g29-shifter-bpf.service"
readonly UNIT_SRC_DIR="$SCRIPT_DIR/systemd"
readonly ENSURE_RULE="/etc/udev/rules.d/99-g29-shifter-ensure.rules"
readonly PACKAGES=(udev-hid-bpf bpf clang libbpf git)

# shellcheck source=g29_wheel_mode.sh
source "$SCRIPT_DIR/g29_wheel_mode.sh"

MODE="install"

usage() {
	sed -n '4,13p' "$0" | sed 's/^# \{0,3\}//'
	exit 0
}

log() { echo "[$SCRIPT_NAME] $*"; }

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
}

# The Arch package ships no headers; fetch the matching upstream tag once.
fetch_headers() {
	if [[ -f "$HEADERS_DIR/src/bpf/hid_bpf_helpers.h" ]]; then
		return
	fi
	log "fetching udev-hid-bpf headers ($HEADERS_TAG)"
	rm -rf "$HEADERS_DIR"
	git clone -q --depth 1 --branch "$HEADERS_TAG" "$HEADERS_REPO" "$HEADERS_DIR"
}

# Mirrors upstream src/bpf/meson.build: clang -target bpf, then a bpftool strip.
build() {
	mkdir -p "$BUILD_DIR"
	log "compiling $(basename "$SRC")"
	clang -std=gnu11 -fno-stack-protector -O2 -target bpf -g -c \
		-fms-extensions -Wno-microsoft-anon-tag "-D__$(uname -m)__" \
		-I"$HEADERS_DIR/src/bpf" -idirafter /usr/include \
		"$SRC" -o "$OBJ.unstripped"
	bpftool gen object "$OBJ" "$OBJ.unstripped"
	log "built $OBJ"
}

# Native-mode device only; any other mode is named, not just "not found".
find_device() {
	local dev
	if dev="$(g29_sysfs_device "$G29_PID_NATIVE")"; then
		echo "$dev"
		return
	fi
	echo "Error: $(g29_mode_explanation "$(g29_wheel_mode)")" >&2
	exit 1
}

is_attached() {
	sudo udev-hid-bpf list-loaded 2>/dev/null | grep -q g29_shifter
}

# The udev rule is the primary attach path; this unit exists because a missed
# attach is silent — the wheel still works, just with the old bad decode.
install_safety_net() {
	local unit="/etc/systemd/system/$UNIT_NAME"
	sed "s#__SCRIPT__#$SCRIPT_DIR/$SCRIPT_NAME#" "$UNIT_SRC_DIR/$UNIT_NAME" |
		sudo install -m 644 /dev/stdin "$unit"
	sudo install -m 644 "$UNIT_SRC_DIR/$(basename "$ENSURE_RULE")" "$ENSURE_RULE"
	sudo udevadm control --reload
	sudo systemctl daemon-reload
	sudo systemctl enable "$UNIT_NAME"
	log "safety net installed: $unit + $(basename "$ENSURE_RULE")"
}

show_status() {
	local mode
	mode="$(g29_wheel_mode)"
	log "wheel mode: $mode ($(g29_mode_explanation "$mode"))"
	if [[ "$mode" == native ]]; then
		log "device: $(find_device)"
	fi
	if [[ -f "$INSTALLED_OBJ" && -f "$INSTALLED_RULE" ]]; then
		log "persistent: $INSTALLED_OBJ + $(basename "$INSTALLED_RULE")"
	else
		log "persistent: not installed (run without --test)"
	fi
	if is_attached; then
		log "attached now: yes"
	else
		log "attached now: NO"
	fi
	if systemctl is-enabled --quiet "$UNIT_NAME" 2>/dev/null; then
		log "safety net: enabled"
	else
		log "safety net: NOT enabled"
	fi
}

main() {
	local dev
	case "$MODE" in
	status)
		show_status
		;;
	ensure)
		if is_attached; then
			log "already attached; nothing to do"
			exit 0
		fi
		case "$(g29_wheel_mode)" in
		native) ;;
		absent)
			# Not a failure: the udev rule re-runs this unit when it appears.
			log "$(g29_mode_explanation absent); nothing to attach to"
			exit 0
			;;
		*)
			# The wheel still "works" here -- with the bad 1st/3rd decode this
			# fix exists to remove -- so say it where it is seen. Exit 1 makes
			# the unit retry (and re-notify) until the selector is flipped.
			log "$(g29_mode_explanation "$(g29_wheel_mode)")" >&2
			g29_notify_desktop "G29 shifter fix NOT active" \
				"$(g29_mode_explanation "$(g29_wheel_mode)")"
			exit 1
			;;
		esac
		dev="$(find_device)"
		if [[ -f "$INSTALLED_OBJ" ]]; then
			sudo udev-hid-bpf add "$dev" "$INSTALLED_OBJ"
			log "re-attached $INSTALLED_OBJ to $dev (udev rule had missed it)"
		else
			log "not installed; run $SCRIPT_NAME without --test first" >&2
			exit 1
		fi
		;;
	remove)
		dev="$(find_device)"
		sudo udev-hid-bpf --verbose remove "$dev"
		log "detached from $dev"
		;;
	test)
		install_packages
		fetch_headers
		build
		dev="$(find_device)"
		sudo udev-hid-bpf --verbose add "$dev" "$OBJ"
		log "attached to $dev (non-persistent; --remove or re-plug undoes it)"
		;;
	install)
		install_packages
		fetch_headers
		build
		sudo udev-hid-bpf install --force "$OBJ"
		install_safety_net
		dev="$(find_device)"
		# Re-trigger so the new rules attach without a re-plug.
		sudo udevadm trigger --action=add "$dev"
		log "installed to /etc/udev-hid-bpf/ and attached to $dev"
		show_status
		;;
	esac
}

while [[ $# -gt 0 ]]; do
	case $1 in
	--test) MODE="test" ;;
	--ensure) MODE="ensure" ;;
	--remove) MODE="remove" ;;
	--status) MODE="status" ;;
	-h | --help) usage ;;
	*)
		echo "Unknown option: $1" >&2
		exit 1
		;;
	esac
	shift
done

main
