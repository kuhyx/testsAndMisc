#!/bin/bash
# ============================================================================
# warp_window.sh -- let the LAN use Cloudflare WARP on work-from-home days.
#
# Gateway mode (setup_dns_blocker.sh gateway) drops the WARP tunnel, because
# WARP carries all traffic past the DNS block. This opens it for every LAN
# device, but ONLY Mon/Thu/Fri 08:00-16:00 by this PC's clock: the open adds one
# element to the nft set warp_open whose timeout ends at 16:00, so the kernel
# closes it again with nothing left to fail. The office days (Tue/Wed) need
# nothing here: the home gateway never touches the work network.
#
# The laptop (warp_home.sh) asks over an SSH key whose forced command is
# `sudo -n /usr/local/sbin/warp-window ssh`, which accepts only open|status.
# The window check runs here, so the laptop's clock cannot widen it.
#
# Usage:
#   sudo ./warp_window.sh open | close | status
#   sudo ./warp_window.sh install <laptop-key.pub>
#
# Standalone on purpose: install copies this one file to /usr/local/sbin.
# ============================================================================

set -euo pipefail

readonly WINDOW_DAYS=" 1 4 5 " # date +%u: Monday, Thursday, Friday
readonly OPEN_SEC=$((8 * 3600)) CLOSE_SEC=$((16 * 3600))
readonly NFT_SET="inet filter warp_open"
readonly KEY_FROM="192.168.1.0/24" # the key works only from the LAN
INSTALL_PATH="/usr/local/sbin/warp-window"
SUDOERS_FILE="/etc/sudoers.d/warp-window"
KEY_USER="${SUDO_USER:-kuhy}"
KEY_HOME="$(getent passwd "$KEY_USER" | cut -d: -f6 || true)"

die() {
	printf 'warp-window: %s\n' "$1" >&2
	exit 1
}

# Seconds until 16:00 while the window is open; fails when it is closed.
# Plain arithmetic, not `date -d 16:00`: DST never changes on a window day.
window_seconds_left() {
	local day h m s now
	read -r day h m s <<<"$(date '+%u %H %M %S')"
	now=$((10#$h * 3600 + 10#$m * 60 + 10#$s))
	[[ $WINDOW_DAYS == *" $day "* ]] || return 1
	((now >= OPEN_SEC && now < CLOSE_SEC)) || return 1
	printf '%s\n' "$((CLOSE_SEC - now))"
}

cmd_open() {
	local left
	left="$(window_seconds_left)" || die "WARP window is Mon/Thu/Fri 08:00-16:00 only."
	# Re-opening must refresh the timeout, and add keeps an old one: flush first.
	# shellcheck disable=SC2086 # NFT_SET is three words on purpose
	nft flush set $NFT_SET 2>/dev/null || die "no warp_open set: is gateway mode on?"
	# shellcheck disable=SC2086
	nft add element $NFT_SET "{ 0.0.0.0/0 timeout ${left}s }"
	printf 'WARP open for the LAN until 16:00.\nseconds_left=%s\n' "$left"
}

cmd_close() {
	# shellcheck disable=SC2086
	nft flush set $NFT_SET
	printf 'WARP blocked again.\n'
}

cmd_status() {
	local set
	# shellcheck disable=SC2086
	set="$(nft list set $NFT_SET)" || die "no warp_open set: is gateway mode on?"
	if [[ $set == *expires* ]]; then
		printf 'open (%s)\n' "$(grep -o 'expires [0-9hms]*' <<<"$set")"
	else
		printf 'closed\n'
	fi
}

# The forced-command entry point. SSH_ORIGINAL_COMMAND is whatever the client
# typed, so it is matched whole: "open; anything" is not "open".
cmd_ssh() {
	case "${SSH_ORIGINAL_COMMAND:-}" in
	open) cmd_open ;;
	status) cmd_status ;;
	*) die "allowed over ssh: open, status" ;;
	esac
}

cmd_install() {
	local pub="${1:-}" tmp key keys
	[[ -f $pub ]] || die "usage: install <laptop-key.pub>"
	[[ -n $KEY_HOME ]] || die "no home directory for $KEY_USER"
	install -m 0755 "${BASH_SOURCE[0]}" "$INSTALL_PATH"

	tmp="$(mktemp)"
	# sudo scrubs the environment; cmd_ssh needs the client's command to filter it.
	printf 'Defaults!%s env_keep += "SSH_ORIGINAL_COMMAND"\n' "$INSTALL_PATH" >"$tmp"
	printf '%s ALL=(root) NOPASSWD: %s ssh\n' "$KEY_USER" "$INSTALL_PATH" >>"$tmp"
	visudo -cf "$tmp" >/dev/null || {
		rm -f "$tmp"
		die "sudoers drop-in failed visudo -c"
	}
	install -m 0440 "$tmp" "$SUDOERS_FILE"
	rm -f "$tmp"

	# One line per laptop key: drop any older copy of it, keep every other key.
	read -r key <"$pub"
	keys="$KEY_HOME/.ssh/authorized_keys"
	mkdir -p "$KEY_HOME/.ssh"
	touch "$keys"
	grep -vF "$key" "$keys" >"$keys.new" || true
	printf 'restrict,from="%s",command="sudo -n %s ssh" %s\n' \
		"$KEY_FROM" "$INSTALL_PATH" "$key" >>"$keys.new"
	mv "$keys.new" "$keys"
	chmod 600 "$keys"
	chown "$KEY_USER:" "$keys"
	printf 'Installed %s; the laptop key may now run open/status.\n' "$INSTALL_PATH"
}

main() {
	case "${1:-}" in
	open | close | status | ssh) "cmd_$1" ;;
	install) cmd_install "${2:-}" ;;
	*)
		printf 'usage: %s open|close|status|install <key.pub>\n' "$0" >&2
		exit 2
		;;
	esac
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
	main "$@"
fi
