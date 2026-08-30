#!/bin/bash
# nftables ruleset, its verification and sshd hardening.
#
# Sourced by setup_wireguard_ssh.sh; split out to keep wg_keys.sh under the
# 250-line cap. Sourced rather than run, so it inherits the caller's
# strict mode and the variables defined above the source line.

# Rendering is separate from writing so that 'verify' can regenerate the
# ruleset into a scratch file and diff it against what is actually on disk,
# without backing anything up or touching the live configuration.
render_nftables_ruleset() {
	local target="$1"
	detect_lan_subnet
	local web_rule=""
	if [[ $ALLOW_WEB == "true" ]]; then
		web_rule=$'\n\t\ttcp dport { 80, 443 } accept'
	fi
	# DNS blocker (setup_dns_blocker.sh): serve DNS (53) -- and DHCP (67) when
	# this PC is the LAN DHCP server -- to LAN clients only. Restricted to the
	# LAN subnet so nothing is ever exposed to the internet.
	local dns_rule="" dhcp_rule=""
	if [[ $ALLOW_DNS == "true" ]]; then
		dns_rule=$'\n\t\tip saddr '"${LAN_SUBNET}"$' udp dport 53 accept'
		dns_rule+=$'\n\t\tip saddr '"${LAN_SUBNET}"$' tcp dport 53 accept'
		# DHCP clients have no IP yet (saddr 0.0.0.0 -> 255.255.255.255) and the
		# broadcast is classified INVALID by conntrack -- so this rule MUST sit
		# BEFORE 'ct state invalid drop' and match the client source port, not a
		# saddr. Link-local only: :67 broadcasts never route in from the internet.
		dhcp_rule=$'\n\t\tudp sport 68 udp dport 67 accept'
	fi
	cat >"$target" <<EOF
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
	chain input {
		type filter hook input priority 0; policy drop;

		iif "lo" accept
		ct state established,related accept${dhcp_rule}
		ct state invalid drop

		icmp type { destination-unreachable, time-exceeded, parameter-problem, echo-request } accept
		icmpv6 type { destination-unreachable, packet-too-big, time-exceeded, parameter-problem, nd-neighbor-solicit, nd-neighbor-advert, echo-request } accept

		udp dport ${WG_PORT} accept

		iifname "${WG_IFACE}" tcp dport 22 accept
		ip saddr ${LAN_SUBNET} tcp dport 22 accept${web_rule}${dns_rule}
	}
	chain forward {
		type filter hook forward priority 0; policy drop;

		# Docker keeps its own FORWARD rules (DOCKER-USER, DOCKER-FORWARD,
		# the isolation chains) in the ip/filter table. This chain runs at
		# the same hook, so a bare 'policy drop' here VETOES them and every
		# bridged container loses all outbound networking -- while the host
		# itself stays perfectly online, so nothing looks broken. That is
		# what killed signal-cli's connection to Signal on 2026-08-29: the
		# bot stayed up, healthy and deaf for three hours.
		ct state established,related accept
		iifname "docker0" accept
		oifname "docker0" accept
		iifname "br-*" accept
		oifname "br-*" accept
	}
	chain output {
		type filter hook output priority 0; policy accept;
	}
}
EOF
}

write_nftables_ruleset() {
	if [[ -f $NFT_CONF ]]; then
		cp "$NFT_CONF" "${NFT_CONF}.bak.$(date +%s)"
		log_warn "Backed up existing ${NFT_CONF} before overwriting."
	fi
	render_nftables_ruleset "${NFT_CONF}.new"
}

# The one invariant that has now broken twice: the forward chain must let
# Docker's own chains decide. Both times the repo carried the rule and
# /etc/nftables.conf did not, so a reboot reloaded the stale file and cut
# every bridged container off the internet while the host stayed online.
# Nothing compared the two, so nothing noticed.
readonly DOCKER_FORWARD_RULE='iifname "docker0" accept'

verify_nft() {
	local rendered status=0
	rendered="$(mktemp)"
	render_nftables_ruleset "$rendered"

	if diff -q "$rendered" "$NFT_CONF" >/dev/null 2>&1; then
		log_ok "${NFT_CONF} matches what this script generates."
	else
		log_error "${NFT_CONF} has DRIFTED from this script. A reboot would apply the stale file."
		diff -u "$NFT_CONF" "$rendered" | head -40 || true
		status=1
	fi
	rm -f "$rendered"

	if nft list chain inet filter forward 2>/dev/null | grep -qF "$DOCKER_FORWARD_RULE"; then
		log_ok "live forward chain lets Docker through."
	else
		log_error "live forward chain does NOT accept docker0 -- bridged containers have no network."
		status=1
	fi

	if ((status != 0)); then
		log_error "Re-apply with: sudo $0 allow-web"
	fi
	return "$status"
}

# 'flush ruleset' above deletes Docker's own tables along with everything
# else, and dockerd only rebuilds them on its next network event -- so
# without this, containers keep running with no NAT and no forwarding until
# somebody happens to restart one. Restarting dockerd rebuilds them at once;
# containers with a restart policy come back by themselves.
restore_docker_rules() {
	if ! is_service_active docker; then
		return 0
	fi
	log_warn "Restarting docker so it can rebuild the nft rules the flush removed."
	systemctl restart docker
	log_ok "docker restarted; its firewall rules are back."
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
	restore_docker_rules
	log_warn "Before closing this terminal, open a SECOND ssh session now and confirm it connects."
	enable_service nftables
}
