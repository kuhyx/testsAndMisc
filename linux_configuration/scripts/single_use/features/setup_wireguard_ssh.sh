#!/bin/bash
# Self-hosted WireGuard VPN + hardened SSH for remote terminal access from
# Android, working across different networks (no relay, no third-party
# coordination server -- point-to-point WireGuard via a port-forwarded UDP
# port and DuckDNS for the dynamic public IP).
#
# Usage:
#   sudo ./setup_wireguard_ssh.sh setup             - full first-time setup
#   sudo ./setup_wireguard_ssh.sh add-peer <name>    - provision a new phone/laptop
#   ./setup_wireguard_ssh.sh status                 - show current state
#   sudo ./setup_wireguard_ssh.sh revoke <name>      - remove a peer
#   ./setup_wireguard_ssh.sh help

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../../lib/common.sh
source "$SCRIPT_DIR/../../lib/common.sh"

readonly WG_IFACE="wg0"
readonly WG_PORT="51820"
readonly WG_SUBNET="10.8.0.0/24"
readonly WG_SERVER_IP="10.8.0.1"
readonly WG_DIR="/etc/wireguard"
readonly WG_CONF="${WG_DIR}/${WG_IFACE}.conf"
readonly WG_CLIENTS_DIR="${WG_DIR}/clients"
readonly NFT_CONF="/etc/nftables.conf"
readonly SSHD_DROPIN="/etc/ssh/sshd_config.d/10-wireguard-only.conf"
readonly DUCKDNS_DIR="/opt/duckdns"
readonly CONFIG_FILE="${SCRIPT_DIR}/.wireguard_ssh.conf"

# Load saved config (DuckDNS domain/token, LAN subnet override) if present.
if [[ -f $CONFIG_FILE ]]; then
	# shellcheck source=/dev/null
	source "$CONFIG_FILE"
fi
DUCKDNS_DOMAIN="${DUCKDNS_DOMAIN:-}"
DUCKDNS_TOKEN="${DUCKDNS_TOKEN:-}"
LAN_SUBNET="${LAN_SUBNET:-}"
export ALLOW_WEB="${ALLOW_WEB:-false}"
export ALLOW_DNS="${ALLOW_DNS:-false}"

die() {
	log_error "$1"
	exit 1
}

save_config() {
	cat >"$CONFIG_FILE" <<EOF
DUCKDNS_DOMAIN="${DUCKDNS_DOMAIN}"
DUCKDNS_TOKEN="${DUCKDNS_TOKEN}"
LAN_SUBNET="${LAN_SUBNET}"
ALLOW_WEB="${ALLOW_WEB}"
ALLOW_DNS="${ALLOW_DNS}"
EOF
	chmod 600 "$CONFIG_FILE"
}

detect_lan_subnet() {
	if [[ -n $LAN_SUBNET ]]; then
		return 0
	fi
	local lan_ip
	lan_ip=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')
	if [[ -z $lan_ip ]]; then
		die "Could not auto-detect LAN IP. Set LAN_SUBNET=192.168.x.0/24 and re-run."
	fi
	LAN_SUBNET="${lan_ip%.*}.0/24"
	log_info "Detected LAN subnet: $LAN_SUBNET"
	save_config
}

install_dependencies() {
	log_info "Installing dependencies (wireguard-tools, qrencode, nftables, openssh)..."
	install_missing_pacman_packages wireguard-tools qrencode nftables openssh
}

# shellcheck source=lib/wg_keys.sh
source "$SCRIPT_DIR/lib/wg_keys.sh"
# shellcheck source=lib/wg_firewall.sh
source "$SCRIPT_DIR/lib/wg_firewall.sh"
# shellcheck source=lib/wg_sshd.sh
source "$SCRIPT_DIR/lib/wg_sshd.sh"


main() {
	local cmd="${1:-help}"

	# Forward the FULL original argv to require_root before shifting anything
	# off -- exec sudo "$0" "$@" inside require_root must re-launch with the
	# subcommand still present, or sudo would silently run with no args.
	case "$cmd" in
	setup | add-peer | revoke | allow-web | allow-dns)
		require_root "$@"
		;;
	esac

	shift || true
	case "$cmd" in
	setup)
		install_dependencies
		generate_server_keys
		write_wg0_conf
		enable_wg_service
		write_nftables_ruleset
		verify_nftables_then_apply
		harden_sshd
		setup_duckdns
		print_router_instructions
		print_android_instructions
		log_ok "Setup complete. Run 'add-peer <name>' to provision your phone."
		;;
	add-peer)
		add_phone_peer "${1:-}"
		print_android_instructions
		;;
	allow-web)
		allow_web
		;;
	allow-dns)
		allow_dns
		;;
	status)
		status_cmd
		;;
	revoke)
		revoke_peer "${1:-}"
		;;
	help | -h | --help)
		usage
		;;
	*)
		log_error "Unknown command: $cmd"
		usage
		exit 1
		;;
	esac
}

main "$@"
