#!/bin/bash
# ============================================================================
# Grow /tmp to a 30G tmpfs and add a 64G disk-backed temp area at /var/disktmp.
#
# 1. /etc/systemd/system/tmp.mount.d/size.conf: the stock options with
#    size=30G, then one daemon-reload and a live remount (never an unmount:
#    the X11 sockets live in /tmp/.X11-unix).
# 2. Each logged-in user's /tmp cap raised live to 80% of 30G through
#    tmp_quota.py (quotactl_fd). systemd applies its own 80% at the next
#    login, so nothing about the cap is persisted.
# 3. A sparse 64G ext4 image, /var/lib/disktmp/disktmp.img, loop-mounted at
#    /var/disktmp (mode 1777) through one /etc/fstab line.
# 4. /etc/tmpfiles.d/disktmp.conf empties it at boot and ages it like /tmp.
#
# Idempotent: a second run changes nothing and says so in one line.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly REQUIRED_TOOLS=(findmnt stat mount systemctl truncate mkfs.ext4 blkid numfmt)

# shellcheck source=lib/tmp_space.sh
source "${SCRIPT_DIR}/lib/tmp_space.sh"
# shellcheck source=lib/tmp_space_verify.sh
source "${SCRIPT_DIR}/lib/tmp_space_verify.sh"

usage() {
	echo "Usage: sudo ${SCRIPT_NAME} [--verify-only]"
	echo "  (no option)    apply everything (root)"
	echo "  --verify-only  change nothing; print the state, exit 1 on drift"
	echo "  -h, --help     show this help"
}

require_tools() {
	local tool
	for tool in "${REQUIRED_TOOLS[@]}"; do
		if ! command -v "$tool" >/dev/null; then
			ts_err "${tool} not found"
			exit 1
		fi
	done
	if [[ ! -x "$TS_PYTHON" ]]; then
		ts_err "${TS_PYTHON} not found"
		exit 1
	fi
}

main() {
	local verify_only=false
	while (($# > 0)); do
		case "$1" in
		--verify-only) verify_only=true ;;
		-h | --help)
			usage
			exit 0
			;;
		*)
			usage >&2
			exit 2
			;;
		esac
		shift
	done
	if [[ "$verify_only" == true ]]; then
		require_tools
		ts_verify
		return
	fi
	if ((EUID != 0)); then
		ts_err "must run as root (sudo ${SCRIPT_NAME})"
		exit 1
	fi
	require_tools
	ts_apply
}

main "$@"
