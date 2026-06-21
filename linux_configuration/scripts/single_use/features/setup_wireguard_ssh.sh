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

die() {
	log_error "$1"
	exit 1
}

save_config() {
	cat >"$CONFIG_FILE" <<EOF
DUCKDNS_DOMAIN="${DUCKDNS_DOMAIN}"
DUCKDNS_TOKEN="${DUCKDNS_TOKEN}"
LAN_SUBNET="${LAN_SUBNET}"
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

generate_server_keys() {
	ensure_dir "$WG_DIR"
	chmod 700 "$WG_DIR"
	if [[ -f "${WG_DIR}/server_private.key" ]]; then
		log_info "Server keypair already exists -- not rotating (would break existing peer configs)."
		return 0
	fi
	umask 077
	wg genkey | tee "${WG_DIR}/server_private.key" | wg pubkey >"${WG_DIR}/server_public.key"
	log_ok "Generated server keypair."
}

write_wg0_conf() {
	if [[ -f $WG_CONF ]]; then
		log_info "${WG_CONF} already exists -- leaving peers intact, not regenerating."
		return 0
	fi
	local server_private_key
	server_private_key=$(<"${WG_DIR}/server_private.key")
	umask 077
	cat >"$WG_CONF" <<EOF
[Interface]
Address = ${WG_SERVER_IP}/24
ListenPort = ${WG_PORT}
PrivateKey = ${server_private_key}
# No PostUp/PostDown NAT: this is a host-only tunnel, not a routed VPN.
EOF
	chmod 600 "$WG_CONF"
	log_ok "Wrote ${WG_CONF}."
}

enable_wg_service() {
	enable_service "wg-quick@${WG_IFACE}"
	log_ok "wg-quick@${WG_IFACE} enabled and started."
}

write_nftables_ruleset() {
	detect_lan_subnet
	if [[ -f $NFT_CONF ]]; then
		cp "$NFT_CONF" "${NFT_CONF}.bak.$(date +%s)"
		log_warn "Backed up existing ${NFT_CONF} before overwriting."
	fi
	cat >"${NFT_CONF}.new" <<EOF
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
	chain input {
		type filter hook input priority 0; policy drop;

		iif "lo" accept
		ct state established,related accept
		ct state invalid drop

		icmp type { destination-unreachable, time-exceeded, parameter-problem, echo-request } accept
		icmpv6 type { destination-unreachable, packet-too-big, time-exceeded, parameter-problem, nd-neighbor-solicit, nd-neighbor-advert, echo-request } accept

		udp dport ${WG_PORT} accept

		iifname "${WG_IFACE}" tcp dport 22 accept
		ip saddr ${LAN_SUBNET} tcp dport 22 accept
	}
	chain forward {
		type filter hook forward priority 0; policy drop;
	}
	chain output {
		type filter hook output priority 0; policy accept;
	}
}
EOF
}

verify_nftables_then_apply() {
	nft -c -f "${NFT_CONF}.new" || die "nftables ruleset failed syntax check -- not applying."
	mv "${NFT_CONF}.new" "$NFT_CONF"
	log_warn "Applying a default-drop firewall now."
	nft -f "$NFT_CONF"
	sleep 2
	if ! is_service_active sshd; then
		nft flush ruleset
		die "sshd died after applying nftables -- rolled back. Investigate before retrying."
	fi
	log_ok "nftables applied; sshd is still active."
	log_warn "Before closing this terminal, open a SECOND ssh session now and confirm it connects."
	enable_service nftables
}

harden_sshd() {
	log_warn "Before disabling password auth, confirm key-based login works."
	log_warn "In ANOTHER terminal, run: ssh -o PreferredAuthentications=publickey $(get_actual_user)@localhost echo ok"
	if ! ask_yes_no "Did key-based login succeed?"; then
		die "Aborting -- run ssh-copy-id to set up key auth first, then re-run setup."
	fi
	cat >"$SSHD_DROPIN" <<'EOF'
# Managed by setup_wireguard_ssh.sh -- drop-in, does not touch sshd_config.
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
EOF
	sshd -t || {
		rm -f "$SSHD_DROPIN"
		die "sshd config invalid after adding drop-in -- removed it."
	}
	systemctl reload sshd
	log_ok "sshd hardened: key-only auth, no root login."
}

duckdns_already_updated() {
	local domain="$1" actual_user line script
	actual_user=$(get_actual_user)
	while IFS= read -r line; do
		[[ $line =~ ^[[:space:]]*(#|$) ]] && continue
		for script in $line; do
			[[ -f $script ]] || continue
			if grep -q "duckdns.org/update?domains=${domain}" "$script" 2>/dev/null; then
				return 0
			fi
		done
	done < <(crontab -u "$actual_user" -l 2>/dev/null || true)
	return 1
}

setup_duckdns() {
	if [[ -z $DUCKDNS_DOMAIN || -z $DUCKDNS_TOKEN ]]; then
		read -r -p "DuckDNS subdomain (without .duckdns.org): " DUCKDNS_DOMAIN
		read -r -p "DuckDNS token: " DUCKDNS_TOKEN
		[[ -n $DUCKDNS_DOMAIN && -n $DUCKDNS_TOKEN ]] || die "Both fields are required."
		save_config
	fi
	if duckdns_already_updated "$DUCKDNS_DOMAIN"; then
		log_info "An existing cron job already keeps ${DUCKDNS_DOMAIN}.duckdns.org updated -- not adding a duplicate."
		return 0
	fi
	ensure_dir "$DUCKDNS_DIR"
	cat >"${DUCKDNS_DIR}/duck.sh" <<EOF
#!/bin/bash
echo url="https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=" | curl -fsS -o "${DUCKDNS_DIR}/duck.log" -K -
EOF
	chmod 700 "${DUCKDNS_DIR}/duck.sh"
	bash "${DUCKDNS_DIR}/duck.sh"
	(
		crontab -l 2>/dev/null || true
	) | grep -vF "${DUCKDNS_DIR}/duck.sh" | {
		cat
		echo "*/5 * * * * ${DUCKDNS_DIR}/duck.sh >/dev/null 2>&1"
	} | crontab -
	log_ok "DuckDNS configured: ${DUCKDNS_DOMAIN}.duckdns.org (refreshed every 5 min via cron)."
}

next_free_wg_ip() {
	local used octet
	used=$(grep -oP 'AllowedIPs\s*=\s*10\.8\.0\.\K[0-9]+' "$WG_CONF" 2>/dev/null || true)
	for ((octet = 2; octet <= 254; octet++)); do
		if ! grep -qx "$octet" <<<"$used"; then
			echo "10.8.0.${octet}"
			return 0
		fi
	done
	die "No free IPs left in ${WG_SUBNET}."
}

add_phone_peer() {
	local name="${1:?usage: add-peer <name>}"
	[[ -f $WG_CONF ]] || die "Run 'setup' first -- ${WG_CONF} does not exist yet."
	[[ -n $DUCKDNS_DOMAIN ]] || die "DuckDNS domain not configured -- run 'setup' first."
	if grep -q "# peer:${name}\$" "$WG_CONF"; then
		die "A peer named '${name}' already exists in ${WG_CONF}. Use 'revoke ${name}' first to replace it."
	fi

	ensure_dir "$WG_CLIENTS_DIR"
	chmod 700 "$WG_CLIENTS_DIR"

	local tmpdir
	tmpdir=$(mktemp -d)
	trap 'rm -rf "$tmpdir"; trap - RETURN' RETURN

	umask 077
	wg genkey | tee "${tmpdir}/priv" | wg pubkey >"${tmpdir}/pub"
	local client_priv client_pub server_pub peer_ip
	client_priv=$(<"${tmpdir}/priv")
	client_pub=$(<"${tmpdir}/pub")
	server_pub=$(<"${WG_DIR}/server_public.key")
	peer_ip=$(next_free_wg_ip)

	cat >>"$WG_CONF" <<EOF

[Peer] # peer:${name}
PublicKey = ${client_pub}
AllowedIPs = ${peer_ip}/32
EOF
	if is_service_active "wg-quick@${WG_IFACE}"; then
		wg syncconf "$WG_IFACE" <(wg-quick strip "$WG_IFACE")
	fi

	local client_conf="${WG_CLIENTS_DIR}/${name}.conf"
	cat >"$client_conf" <<EOF
[Interface]
PrivateKey = ${client_priv}
Address = ${peer_ip}/32
# No DNS server here on purpose: AllowedIPs below is scoped to the WireGuard
# subnet only (host-only tunnel), so a DNS server outside that subnet would
# be unreachable through the tunnel -- Android would then have no working
# resolver at all while the tunnel is active, breaking DNS for everything.

[Peer]
PublicKey = ${server_pub}
Endpoint = ${DUCKDNS_DOMAIN}.duckdns.org:${WG_PORT}
AllowedIPs = ${WG_SUBNET}
PersistentKeepalive = 25
EOF
	chmod 600 "$client_conf"
	log_ok "Phone config written to ${client_conf}"
	log_info "Scan this QR code with the WireGuard Android app:"
	qrencode -t ansiutf8 <"$client_conf"
}

revoke_peer() {
	local name="${1:?usage: revoke <name>}"
	[[ -f $WG_CONF ]] || die "${WG_CONF} does not exist."
	grep -q "# peer:${name}\$" "$WG_CONF" || die "No peer named '${name}' found."

	local tmp
	tmp=$(mktemp)
	trap 'rm -f "$tmp"; trap - RETURN' RETURN
	awk -v marker="# peer:${name}" '
		$0 ~ ("^\\[Peer\\].*" marker "$") { skip = 1; next }
		skip && /^$/ { skip = 0; next }
		skip { next }
		{ print }
	' "$WG_CONF" >"$tmp"
	cat "$tmp" >"$WG_CONF"
	chmod 600 "$WG_CONF"

	if is_service_active "wg-quick@${WG_IFACE}"; then
		wg syncconf "$WG_IFACE" <(wg-quick strip "$WG_IFACE")
	fi
	rm -f "${WG_CLIENTS_DIR}/${name}.conf"
	log_ok "Revoked peer '${name}'."
}

print_router_instructions() {
	local lan_ip
	lan_ip=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')
	cat <<EOF

=== Manual step: forward a port on your router (cannot be automated) ===
1. Log into your router admin page (often http://192.168.1.1 or http://192.168.0.1).
2. Find "Port Forwarding" / "Virtual Server" / "NAT" settings.
3. Forward UDP port ${WG_PORT} -> ${lan_ip} (UDP only -- do NOT forward TCP/22).
4. Save (and reboot the router if it requires it).
5. Confirm your ISP gives you a real public IPv4 (not CGNAT):
     curl -s https://api.ipify.org
     getent hosts ${DUCKDNS_DOMAIN:-<your-domain>}.duckdns.org
   These two must match and must NOT be in 100.64.0.0/10 (CGNAT range).
EOF
}

print_android_instructions() {
	cat <<EOF

=== Manual step: install FOSS apps on your Android phone ===
1. Install F-Droid (https://f-droid.org/) if you don't have it.
2. From F-Droid, install "WireGuard" (official app, org.wireguard.android).
3. From F-Droid, install "Termux" (then run: pkg install openssh) or "ConnectBot".
4. Open WireGuard -> "+" -> "Scan from QR code" -> scan the code printed above.
5. Toggle the tunnel on.
6. From Termux/ConnectBot: ssh $(get_actual_user)@${WG_SERVER_IP}
EOF
}

status_cmd() {
	echo "=== WireGuard ==="
	wg show 2>/dev/null || echo "(interface not up)"
	echo
	echo "=== wg-quick@${WG_IFACE} service ==="
	systemctl status "wg-quick@${WG_IFACE}" --no-pager 2>/dev/null || echo "(not installed)"
	echo
	echo "=== nftables (input chain) ==="
	nft list ruleset 2>/dev/null | sed -n '/chain input/,/}/p' || echo "(nftables not active)"
	echo
	echo "=== sshd password auth ==="
	sshd -T 2>/dev/null | grep -i passwordauthentication || echo "(could not query sshd)"
}

usage() {
	cat <<EOF
Usage: $0 <command> [args]

Commands:
  setup            Full first-time setup (WireGuard, firewall, sshd, DuckDNS).
  add-peer <name>  Provision a new phone/laptop and print its QR code.
  status           Show WireGuard/firewall/sshd status.
  revoke <name>    Remove a peer.
  help             Show this message.
EOF
}

main() {
	local cmd="${1:-help}"

	# Forward the FULL original argv to require_root before shifting anything
	# off -- exec sudo "$0" "$@" inside require_root must re-launch with the
	# subcommand still present, or sudo would silently run with no args.
	case "$cmd" in
	setup | add-peer | revoke)
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
