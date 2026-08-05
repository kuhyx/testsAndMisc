#!/bin/bash

# ============================================================================
# Get the phone onto the WireGuard tunnel, so it can reach the DoT resolver.
#
# Why this exists:
#   setup_dot_resolver.sh binds the DoT endpoint to 10.8.0.1 (WireGuard only),
#   which is what keeps it from being an open resolver on the internet. That
#   makes the tunnel a hard prerequisite: with it down, pinning Private DNS to
#   the resolver leaves the phone with no working DNS at all. This script
#   installs the client, pushes the config, and -- most importantly -- verifies
#   the tunnel actually carries DNS before anything starts depending on it.
#
# What it cannot do:
#   Android requires an explicit user tap to grant VPN permission and to
#   import a tunnel config; there is no ADB path around that, by design. The
#   script does everything either side of those taps and tells you exactly
#   what to press.
#
# Usage:
#   ./setup_phone_wireguard.sh [--serial <adb-serial>] [--check]
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly DEFAULT_SERIAL="23181JEGR08034"
readonly WG_PACKAGE="com.zaneschepke.wireguardautotunnel"
readonly WG_FALLBACK_PACKAGE="com.wireguard.android"
readonly SERVER_CONF="/etc/wireguard/wg0.conf"
readonly CLIENT_CONF="/etc/wireguard/clients/phone.conf"
readonly TUNNEL_ADDR="10.8.0.1"
readonly PHONE_ADDR="10.8.0.2"
readonly PUSH_PATH="/sdcard/Download/phone.conf"

SERIAL="$DEFAULT_SERIAL"
CHECK_ONLY=0

log() { printf '[phone-wg] %s\n' "$1"; }
die() {
	printf '[phone-wg] ERROR: %s\n' "$1" >&2
	exit 1
}

usage() {
	cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]
  --serial <id>   adb serial (default: $DEFAULT_SERIAL)
  --check         Verify the tunnel end to end, change nothing
  -h, --help      Show this help
EOF
	exit 0
}

adb_sh() { adb -s "$SERIAL" shell "$@" 2>/dev/null | tr -d '\r'; }

require_device() {
	command -v adb >/dev/null 2>&1 ||
		die "adb not found; install android-tools"
	adb -s "$SERIAL" get-state >/dev/null 2>&1 ||
		die "device $SERIAL not connected"
}

require_server() {
	sudo test -f "$SERVER_CONF" ||
		die "$SERVER_CONF missing - is WireGuard set up on this host?"
	sudo test -f "$CLIENT_CONF" ||
		die "$CLIENT_CONF missing - no client config to import"
	ip -brief addr show 2>/dev/null | grep -q "$TUNNEL_ADDR" ||
		die "$TUNNEL_ADDR is not up; start it with: sudo wg-quick up wg0"
}

installed_client() {
	# Echo whichever WireGuard client is present, preferring the one already
	# whitelisted in phone_focus_mode.
	local pkg
	for pkg in "$WG_PACKAGE" "$WG_FALLBACK_PACKAGE"; do
		if adb_sh "pm list packages $pkg" | grep -q .; then
			printf '%s' "$pkg"
			return 0
		fi
	done
	return 1
}

install_client() {
	local pkg
	if pkg="$(installed_client)"; then
		log "WireGuard client already installed: $pkg"
		return 0
	fi
	# Play Store installs cannot be driven headlessly. Open the listing and
	# let the user tap Install; re-running the script then proceeds.
	log "No WireGuard client installed. Opening the Play Store listing..."
	adb -s "$SERIAL" shell am start -a android.intent.action.VIEW \
		-d "market://details?id=$WG_PACKAGE" >/dev/null 2>&1 || true
	die "install WireGuard on the phone, then re-run $SCRIPT_NAME"
}

push_config() {
	# The config carries a private key, so it goes to Download/ only long
	# enough to be imported, and is deleted again in verify/cleanup.
	log "Pushing client config to $PUSH_PATH"
	local tmp
	tmp="$(mktemp)"
	# shellcheck disable=SC2064  # expand $tmp now, not at trap time
	trap "rm -f '$tmp'" RETURN
	# The redirect is to our own mktemp file, not to the root-owned source;
	# install(1) makes that explicit and keeps the copy mode-0600.
	sudo install -m 600 -o "$USER" "$CLIENT_CONF" "$tmp" ||
		die "could not read $CLIENT_CONF"
	grep -q "^Address *= *$PHONE_ADDR" "$tmp" ||
		die "client config does not assign $PHONE_ADDR - wrong peer?"
	adb -s "$SERIAL" push "$tmp" "$PUSH_PATH" >/dev/null ||
		die "adb push failed"
}

prompt_import() {
	local pkg
	pkg="$(installed_client)" || die "no WireGuard client installed"
	log "Opening $pkg - complete these steps on the phone:"
	log "  1. '+' -> Import from file -> Download/phone.conf"
	log "  2. Toggle the tunnel ON"
	log "  3. Accept Android's VPN permission dialog"
	adb -s "$SERIAL" shell monkey -p "$pkg" \
		-c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
}

cleanup_pushed_config() {
	# The pushed file contains a private key; do not leave it in Download/.
	adb_sh "rm -f $PUSH_PATH" >/dev/null 2>&1 || true
	log "Removed $PUSH_PATH from the phone"
}

run_check() {
	local ok=0

	if ! installed_client >/dev/null; then
		log "FAIL no WireGuard client installed"
		return 1
	fi

	# A handshake proves the tunnel is established from the server's side;
	# the phone's own interface list is not visible without root.
	local handshake
	handshake="$(sudo wg show wg0 latest-handshakes 2>/dev/null | awk '{print $2}' | head -1)"
	if [[ -z "$handshake" || "$handshake" == "0" ]]; then
		log "FAIL no WireGuard handshake yet - is the tunnel toggled on?"
		ok=1
	else
		log "OK handshake $(($(date +%s) - handshake))s ago"
	fi

	# The decisive test: not "is a VPN up" but "does the phone reach the
	# resolver". Everything downstream depends on this one answer.
	if adb_sh "ping -c 2 -W 3 $TUNNEL_ADDR" | grep -q " 0% packet loss"; then
		log "OK phone reaches $TUNNEL_ADDR over the tunnel"
	else
		log "FAIL phone cannot reach $TUNNEL_ADDR"
		ok=1
	fi

	# And that DNS actually resolves through it, which is the thing that
	# broke when this was attempted without a tunnel.
	if adb_sh "ping -c 2 -W 3 example.com" | grep -q " 0% packet loss"; then
		log "OK DNS resolves on the phone"
	else
		log "FAIL DNS does not resolve on the phone"
		ok=1
	fi

	if [[ $ok -eq 0 ]]; then
		log "Tunnel healthy. Safe to set in phone_focus_mode/config.sh:"
		log "  DNS_TRUSTED_DOT_HOST=\"dns.kuhy.duckdns.org\""
		log "  DNS_TRUSTED_DOT_IPS=\"$TUNNEL_ADDR\""
	fi
	return "$ok"
}

main() {
	require_device
	if [[ $CHECK_ONLY -eq 1 ]]; then
		run_check
		exit $?
	fi

	require_server
	install_client
	push_config
	prompt_import

	log "Waiting up to 180s for the tunnel to come up..."
	local deadline=$((SECONDS + 180))
	while ((SECONDS < deadline)); do
		if adb_sh "ping -c 1 -W 2 $TUNNEL_ADDR" | grep -q " 0% packet loss"; then
			log "Tunnel is up."
			break
		fi
		sleep 5
	done

	cleanup_pushed_config
	run_check || {
		log "Tunnel not verified. Re-run with --check after toggling it on."
		exit 1
	}
}

while [[ $# -gt 0 ]]; do
	case $1 in
	--serial)
		SERIAL="$2"
		shift 2
		;;
	--check)
		CHECK_ONLY=1
		shift
		;;
	-h | --help) usage ;;
	*) die "Unknown option: $1" ;;
	esac
done

main "$@"
