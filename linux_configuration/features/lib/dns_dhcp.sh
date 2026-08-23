#!/bin/bash
# Static IP, DHCP server config and the status report.
#
# Sourced by setup_dns_blocker.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode.

configure_static_ip() {
	has_cmd nmcli || die "nmcli (NetworkManager) not found; cannot pin a static IP automatically."
	local con
	con="$(nm_connection)"
	[[ -n $con ]] || die "No active NetworkManager connection on ${LAN_IFACE}."
	log_info "Pinning ${LAN_IFACE} to static ${LAN_IP}/24 (gw ${GATEWAY}) on '${con}'..."
	nmcli con mod "$con" \
		ipv4.method manual \
		ipv4.addresses "${LAN_IP}/24" \
		ipv4.gateway "$GATEWAY" \
		ipv4.dns "$GATEWAY"
	nmcli con up "$con" >/dev/null
	# Safety self-check: if the static config broke connectivity, auto-revert to
	# DHCP-client mode immediately so the machine never ends up stranded.
	if ping -c1 -W3 "$GATEWAY" >/dev/null 2>&1; then
		log_ok "Static IP applied; gateway reachable. ${LAN_IFACE} no longer needs external DHCP."
	else
		log_error "Gateway unreachable after static IP change -- auto-reverting to DHCP."
		revert_nic_to_dhcp "$con"
		die "Static IP self-check failed; reverted to DHCP. DHCP mode aborted (no changes kept)."
	fi
}

write_dhcp_conf() {
	local mac net_prefix
	mac="$(cat "/sys/class/net/${LAN_IFACE}/address")"
	net_prefix="${LAN_IP%.*}"
	log_info "Writing ${DHCP_CONF} (range ${net_prefix}.${DHCP_START_HOST}-${net_prefix}.${DHCP_END_HOST}, DNS ${LAN_IP})."
	cat >"$DHCP_CONF" <<EOF
# Managed by setup_dns_blocker.sh -- this PC is the LAN DHCP server.
# Only serve leases once the router's own DHCP is disabled (two servers clash).
dhcp-authoritative
dhcp-range=${net_prefix}.${DHCP_START_HOST},${net_prefix}.${DHCP_END_HOST},${DHCP_LEASE}
dhcp-option=option:router,${GATEWAY}
dhcp-option=option:dns-server,${LAN_IP}
# Reserve this PC's static address against its own MAC.
dhcp-host=${mac},${LAN_IP}
# Log every DHCP transaction (low volume; satisfies "log failures").
log-dhcp
EOF
}

cmd_dhcp() {
	detect_lan
	is_service_active dnsmasq ||
		die "Run 'setup' first -- dnsmasq must be configured before enabling DHCP mode."
	echo
	log_warn "DHCP takeover: this PC (${LAN_IP}) will become the LAN's DHCP server."
	log_warn "Disable the router's DHCP FIRST (untick 'wlacz serwer DHCP' -> Zapisz),"
	log_warn "otherwise two DHCP servers will fight on the LAN."
	if ! ask_yes_no "Have you already disabled the router's DHCP server?"; then
		log_warn "Not activating -- two DHCP servers on one LAN conflict."
		log_warn "Disable the router's DHCP ('wlacz serwer DHCP' -> Zapisz), then re-run: sudo ${SELF} dhcp"
		return 0
	fi
	configure_static_ip
	write_dhcp_conf
	dnsmasq --test >/dev/null 2>&1 || die "dnsmasq config invalid after adding DHCP -- not restarting."
	systemctl restart dnsmasq
	log_ok "This PC is now the LAN DHCP server; new leases advertise ${LAN_IP} as DNS."
	log_info "Reconnect a device's WiFi to pick up the new lease, then browse to a blocked site to confirm."
	cat <<EOF

  ---- IF ANYTHING GOES WRONG (one command, cannot lock you out) ------------
    sudo ${SELF} dhcp-off
       -> stops serving DHCP, KEEPS this PC online on ${LAN_IP}.
    Then re-tick the router's DHCP ('wlacz serwer DHCP' -> Zapisz) so other
    devices get addresses again. This PC stays reachable throughout.
  --------------------------------------------------------------------------
EOF
}

# Roll back DHCP mode: stop serving leases. KEEPS this PC on its static IP so
# running rollback can never strand the machine (the router reserves ${LAN_IP}
# anyway). Re-enable the router's DHCP afterwards for the other devices.
cmd_dhcp_off() {
	detect_lan
	if [[ -f $DHCP_CONF ]]; then
		rm -f "$DHCP_CONF"
		log_ok "Removed ${DHCP_CONF} (PC no longer serves DHCP)."
	else
		log_info "No DHCP config present; nothing to remove."
	fi
	is_service_active dnsmasq && systemctl restart dnsmasq
	log_ok "DHCP serving stopped. This PC keeps its static IP (${LAN_IP}); still online."
	log_warn "Now re-enable the router's DHCP ('wlacz serwer DHCP' -> Zapisz) so other devices get addresses."
	log_info "Optional: to also put THIS PC back on router DHCP (after re-enabling it above), run:"
	log_info "    nmcli con mod '$(nm_connection)' ipv4.method auto ipv4.addresses '' ipv4.gateway '' ipv4.dns '' && nmcli con up '$(nm_connection)'"
}

# ---- Status ----------------------------------------------------------------
status_line() {
	# $1 ok/bad flag ("0" ok), $2 message
	if [[ $1 == "0" ]]; then log_ok "$2"; else log_warn "$2"; fi
}

cmd_status() {
	detect_lan
	echo "=== LAN DNS blocker status ==="

	if is_service_active dnsmasq; then
		status_line 0 "dnsmasq: active"
	else
		status_line 1 "dnsmasq: NOT active"
	fi
	if is_service_enabled dnsmasq; then
		status_line 0 "dnsmasq: enabled at boot"
	else
		status_line 1 "dnsmasq: NOT enabled"
	fi
	if [[ -f $DNSMASQ_DROPIN ]]; then
		status_line 0 "Restart=always drop-in present"
	else
		status_line 1 "Restart drop-in missing"
	fi
	if [[ -f $FEED ]]; then
		status_line 0 "blocklist feed: $(wc -l <"$FEED") lines, updated $(date -r "$FEED" '+%Y-%m-%d %H:%M')"
	else
		status_line 1 "blocklist feed missing: ${FEED}"
	fi

	if ss -tulnp 2>/dev/null | grep -qE "${LAN_IP}:53|:53 "; then
		status_line 0 "listening on ${LAN_IP}:53"
	else
		status_line 1 "not listening on ${LAN_IP}:53"
	fi

	local fw_input
	fw_input="$(nft list chain inet filter input 2>/dev/null || true)"
	if [[ $fw_input == *"policy drop"* ]]; then
		if [[ $fw_input == *"dport 53"* ]]; then
			status_line 0 "firewall: DNS/DHCP open for LAN"
		else
			status_line 1 "firewall loaded but DNS/DHCP NOT open -- run: sudo ${WG_SCRIPT} allow-dns"
		fi
	elif [[ $EUID -ne 0 ]]; then
		log_info "firewall: run 'sudo $0 status' to inspect nftables (needs root)"
	else
		status_line 0 "firewall: no default-drop ruleset loaded (DNS/DHCP not filtered)"
	fi

	if systemctl is-active dns-blocklist-refresh.timer &>/dev/null; then
		status_line 0 "refresh timer: active (next $(systemctl show -p NextElapseUSecRealtime --value dns-blocklist-refresh.timer 2>/dev/null))"
	else
		status_line 1 "refresh timer: NOT active"
	fi
	if [[ -f $DHCP_CONF ]]; then
		if ss -ulnp 2>/dev/null | grep -q ':67 '; then
			status_line 0 "DHCP mode: ON (serving leases; PC is the LAN DHCP server)"
		else
			status_line 1 "DHCP mode: config present but not serving -- restart dnsmasq"
		fi
	else
		status_line 0 "DHCP mode: off (using router DHCP / manual per-device DNS)"
	fi

	echo
	echo "=== Live resolution test (via ${LAN_IP}) ==="
	if has_cmd dig; then
		local blocked passthru
		blocked="$(dig +short +time=2 +tries=1 @"${LAN_IP}" youtube.com 2>/dev/null | head -1)"
		passthru="$(dig +short +time=2 +tries=1 @"${LAN_IP}" example.com 2>/dev/null | head -1)"
		if [[ $blocked == "0.0.0.0" ]]; then
			status_line 0 "youtube.com -> ${blocked} (BLOCKED, correct)"
		else
			status_line 1 "youtube.com -> ${blocked:-<no answer>} (expected 0.0.0.0)"
		fi
		if [[ -n $passthru && $passthru != "0.0.0.0" ]]; then
			status_line 0 "example.com -> ${passthru} (passthrough, correct)"
		else
			status_line 1 "example.com -> ${passthru:-<no answer>} (expected a real IP)"
		fi
	else
		log_warn "install 'dig' (bind) to run the live resolution test."
	fi

	if [[ -s $LOG_FILE ]]; then
		echo
		echo "=== Recent dnsmasq log (${LOG_FILE}) ==="
		tail -5 "$LOG_FILE"
	fi
}
