#!/bin/bash
# Validation, firewall rules and the allow-DNS flag.
#
# Sourced by setup_dns_blocker.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode.

validate_and_enable() {
	log_info "Validating dnsmasq configuration..."
	dnsmasq --test 2>&1 | tail -3
	dnsmasq --test >/dev/null 2>&1 || die "dnsmasq config failed validation -- not enabling."
	log_ok "dnsmasq config valid."
	systemctl daemon-reload
	enable_service dnsmasq
	# enable --now does not restart an already-running daemon, so restart to
	# apply config changes on idempotent re-runs.
	systemctl restart dnsmasq
	systemctl enable --now dns-blocklist-refresh.timer
	systemctl enable --now dnsmasq-watchdog.timer
	log_ok "dnsmasq, the daily refresh timer, and the watchdog are enabled."
}

# Open port 53 for LAN clients -- but only touch the firewall if it is already
# the active (wireguard-managed) default-drop ruleset. If nftables is inactive,
# port 53 is already reachable and force-loading the firewall here could
# disrupt other services, so we only persist the intent and instruct the user.
# A default-drop nftables ruleset can be loaded in the kernel even while
# nftables.service reads "inactive", so detect the actual ruleset, not the unit.
firewall_is_loaded() {
	# Capture then match (no 'grep -q' pipe: it closes early -> SIGPIPE on nft ->
	# pipefail makes the whole pipeline fail, a false negative under set -o pipefail).
	local rules
	rules="$(nft list chain inet filter input 2>/dev/null || true)"
	[[ $rules == *"policy drop"* ]]
}

configure_firewall() {
	if firewall_is_loaded; then
		log_info "Default-drop firewall detected; opening DNS/DHCP for the LAN via the firewall owner."
		bash "$WG_SCRIPT" allow-dns
	else
		log_warn "No default-drop firewall loaded -- DNS/DHCP already reachable on the LAN."
		persist_allow_dns_flag
		log_warn "If you later enable the default-drop firewall, run: sudo ${WG_SCRIPT} allow-dns"
	fi
}

# Record ALLOW_DNS=true in the wireguard config so a future firewall apply keeps
# :53 open for the LAN, without activating the firewall now.
persist_allow_dns_flag() {
	local cfg="${SCRIPT_DIR}/.wireguard_ssh.conf"
	[[ -f $cfg ]] || return 0
	if grep -qE '^ALLOW_DNS=' "$cfg"; then
		sed -i 's/^ALLOW_DNS=.*/ALLOW_DNS="true"/' "$cfg"
	else
		printf 'ALLOW_DNS="true"\n' >>"$cfg"
	fi
	log_ok "Persisted ALLOW_DNS=true in ${cfg} for the next firewall apply."
}

print_manual_steps() {
	cat <<EOF

============================================================================
 Manual steps this script cannot do (they are on the router / phone)
============================================================================
 The PC (${LAN_IP}) is not the gateway, so devices only use it as DNS if they
 are pointed at it. Pick ONE delivery method:

 A) If your router lets you set the DHCP "DNS server" it advertises:
      set it to ${LAN_IP} and ONLY that (no secondary DNS -- a backup DNS
      silently disables blocking). Also reserve ${LAN_IP} for this PC.
 B) If your router CANNOT set the advertised DNS (many ISP routers can't):
      run './setup_dns_blocker.sh dhcp' to make THIS PC the LAN DHCP server
      (disable the router's DHCP first). Fully automatic for every device.
 C) Or set DNS = ${LAN_IP} by hand on each device (phone: WiFi -> Static -> DNS).

 PHONE (all methods) -- turn Private DNS OFF (Settings -> Network -> Private
      DNS -> Off). Android's default "Automatic" uses DoH and bypasses LAN DNS.
      This is a toggle, not an app, so it keeps the "no extra app" rule.

 Known limitations (voluntary DNS): a device using DoH, a VPN, or a manually
 set DNS bypasses this. It cannot be forced because the PC is not in the
 traffic path. Works for the common case (devices that honor network DNS).
============================================================================
EOF
}
