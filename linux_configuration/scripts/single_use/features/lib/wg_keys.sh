#!/bin/bash
# Key generation and the WireGuard service.
#
# Sourced by setup_wireguard_ssh.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

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
