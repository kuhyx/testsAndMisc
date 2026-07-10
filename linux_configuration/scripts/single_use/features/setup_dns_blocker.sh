#!/bin/bash
# ============================================================================
# setup_dns_blocker.sh -- Pi-hole-like LAN DNS blocking, hosted on this PC.
#
# Turns this machine into a DNS server (dnsmasq) that serves the EXACT same
# blocklist as the local /etc/hosts to every device on the LAN, with no app
# installed on those devices. The blocklist feed is produced verbatim by the
# repo's generate_hosts_file.sh (same StevenBlack variant + custom entries +
# unblocks that /etc/hosts uses), so blocking is identical by construction.
#
# The PC is NOT the gateway, so it can only be a resolver that clients are
# POINTED at (via the router's DHCP-advertised DNS). See the manual steps
# printed by `setup`. Known bypasses (DoH / Private DNS / manual DNS / VPN)
# are documented there too -- a voluntary-DNS design cannot force traffic.
#
# Usage:
#   sudo ./setup_dns_blocker.sh setup     # first-time install + enable
#        ./setup_dns_blocker.sh status    # is it set up & serving?  (no root)
#   sudo ./setup_dns_blocker.sh refresh   # rebuild feed + reload (timer runs this)
#        ./setup_dns_blocker.sh help
#
# Idempotent and safe to re-run.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
# shellcheck source=../../lib/common.sh
source "$SCRIPT_DIR/../../lib/common.sh"

# ---- Configuration ---------------------------------------------------------
readonly FEED_DIR="/var/lib/dns-blocker"
readonly FEED="${FEED_DIR}/blocklist.hosts"
readonly DNSMASQ_MAIN_CONF="/etc/dnsmasq.conf"
readonly DNSMASQ_CONF="/etc/dnsmasq.d/lan-blocker.conf"
readonly CONF_DIR_LINE="conf-dir=/etc/dnsmasq.d/,*.conf"
readonly LOG_DIR="/var/log/dns-blocker"
readonly LOG_FILE="${LOG_DIR}/dnsmasq.log"
readonly DNSMASQ_DROPIN_DIR="/etc/systemd/system/dnsmasq.service.d"
readonly DNSMASQ_DROPIN="${DNSMASQ_DROPIN_DIR}/blocker.conf"
readonly REFRESH_SERVICE="/etc/systemd/system/dns-blocklist-refresh.service"
readonly REFRESH_TIMER="/etc/systemd/system/dns-blocklist-refresh.timer"
# Optional DHCP-server mode (for routers that cannot advertise a custom DNS).
readonly DHCP_CONF="/etc/dnsmasq.d/lan-dhcp.conf"
readonly DHCP_LEASE="12h"
readonly DHCP_START_HOST="10"  # .10 .. .150 mirrors a common router default range
readonly DHCP_END_HOST="150"
# Feed generator (chattr +i but still executable) and firewall owner script.
readonly GEN="${SCRIPT_DIR}/../../periodic_background/hosts/generate_hosts_file.sh"
readonly WG_SCRIPT="${SCRIPT_DIR}/setup_wireguard_ssh.sh"
readonly SELF="${SCRIPT_DIR}/setup_dns_blocker.sh"

die() {
	log_error "$1"
	exit 1
}

# ---- LAN autodetection -----------------------------------------------------
# Derive the LAN interface / IP / gateway from the default route so the config
# is not hardcoded to one NIC name.
detect_lan() {
	local route
	route="$(ip -4 route get 1.1.1.1 2>/dev/null || true)"
	LAN_IFACE="$(awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}' <<<"$route")"
	LAN_IP="$(awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}' <<<"$route")"
	GATEWAY="$(ip -4 route show default 2>/dev/null | awk '{print $3; exit}')"
	[[ -n ${LAN_IFACE:-} && -n ${LAN_IP:-} ]] ||
		die "Could not detect the LAN interface/IP from the default route."
	# Upstream for non-blocked names: the gateway if known, else a public resolver.
	UPSTREAM="${GATEWAY:-1.1.1.1}"
}

# ---- Setup steps -----------------------------------------------------------
install_dnsmasq() {
	# dnsmasq is the resolver; bind provides 'dig' for the status live test.
	local pkgs=()
	has_cmd dnsmasq || pkgs+=(dnsmasq)
	has_cmd dig || pkgs+=(bind)
	if ((${#pkgs[@]})); then
		log_info "Installing: ${pkgs[*]}"
		install_missing_pacman_packages "${pkgs[@]}"
	else
		log_ok "dnsmasq and dig already installed."
	fi
	# dnsmasq only reads /etc/dnsmasq.d/* if the main conf enables conf-dir.
	if grep -qE '^\s*conf-dir=' "$DNSMASQ_MAIN_CONF" 2>/dev/null; then
		log_ok "conf-dir already enabled in ${DNSMASQ_MAIN_CONF}."
	else
		log_info "Enabling conf-dir in ${DNSMASQ_MAIN_CONF}."
		printf '\n# Added by setup_dns_blocker.sh -- load /etc/dnsmasq.d/*.conf\n%s\n' \
			"$CONF_DIR_LINE" >>"$DNSMASQ_MAIN_CONF"
	fi
}

prepare_dirs() {
	ensure_dir "$FEED_DIR"
	ensure_dir "$LOG_DIR"
	# dnsmasq drops to the 'dnsmasq' user; it must be able to write its log.
	touch "$LOG_FILE"
	if id dnsmasq &>/dev/null; then
		chown dnsmasq:dnsmasq "$LOG_DIR" "$LOG_FILE"
	fi
}

build_feed() {
	[[ -x $GEN ]] || die "Feed generator not found or not executable: ${GEN}"
	log_info "Building blocklist feed from generate_hosts_file.sh (this is the same list as /etc/hosts)..."
	"$GEN" "$FEED" || die "Feed generation failed."
	local count
	count="$(wc -l <"$FEED")"
	((count > 1000)) || die "Feed looks too small (${count} lines) -- refusing to serve a broken blocklist."
	log_ok "Feed built: ${count} lines at ${FEED}."
}

write_dnsmasq_conf() {
	ensure_dir "$(dirname "$DNSMASQ_CONF")" # /etc/dnsmasq.d may not exist yet
	log_info "Writing ${DNSMASQ_CONF} (listen on ${LAN_IFACE}/${LAN_IP}, upstream ${UPSTREAM})."
	cat >"$DNSMASQ_CONF" <<EOF
# Managed by setup_dns_blocker.sh -- LAN DNS blocker.
# Serves the identical blocklist as /etc/hosts to LAN clients via addn-hosts.
# Do not edit by hand; re-run 'setup_dns_blocker.sh setup' instead.

# Listen only on the LAN interface (leaves 127.0.0.53 free for the
# systemd-resolved stub that the /etc/hosts installer enables).
interface=${LAN_IFACE}
bind-interfaces

# Do NOT read /etc/hosts (huge + immutable); the blocklist comes from the feed.
no-hosts
addn-hosts=${FEED}

# Forward everything not in the blocklist to the upstream resolver ONLY.
# no-resolv: ignore /etc/resolv.conf so we never chain through the
# systemd-resolved stub (127.0.0.53) that the /etc/hosts installer enables.
no-resolv
server=${UPSTREAM}
domain-needed
bogus-priv

cache-size=10000

# Log dnsmasq's own messages (startup, upstream failures) -- "log failures".
log-facility=${LOG_FILE}
# log-queries   # opt-in: full per-query log (verbose + privacy). Off by default.
EOF
}

install_restart_dropin() {
	ensure_dir "$DNSMASQ_DROPIN_DIR"
	cat >"$DNSMASQ_DROPIN" <<'EOF'
# Managed by setup_dns_blocker.sh -- keep the resolver up and wait for the
# network so bind-interfaces can bind the LAN address at boot.
[Unit]
After=network-online.target
Wants=network-online.target

[Service]
Restart=always
RestartSec=5
EOF
}

install_refresh_timer() {
	cat >"$REFRESH_SERVICE" <<EOF
[Unit]
Description=Rebuild the LAN DNS blocklist and reload dnsmasq
After=network-online.target

[Service]
Type=oneshot
ExecStart=${SELF} refresh
EOF
	cat >"$REFRESH_TIMER" <<'EOF'
[Unit]
Description=Daily rebuild of the LAN DNS blocklist

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=15m

[Install]
WantedBy=timers.target
EOF
}

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
	log_ok "dnsmasq and the daily refresh timer are enabled."
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

cmd_setup() {
	detect_lan
	install_dnsmasq
	prepare_dirs
	build_feed
	write_dnsmasq_conf
	install_restart_dropin
	install_refresh_timer
	validate_and_enable
	configure_firewall
	print_manual_steps
	log_ok "DNS blocker setup complete. Run './setup_dns_blocker.sh status' to verify."
}

cmd_refresh() {
	[[ -x $GEN ]] || die "Feed generator not found: ${GEN}"
	log_info "Refreshing blocklist feed..."
	"$GEN" "$FEED" || die "Feed generation failed."
	if is_service_active dnsmasq; then
		systemctl kill -s HUP dnsmasq
		log_ok "Feed refreshed and dnsmasq reloaded ($(wc -l <"$FEED") lines)."
	else
		log_warn "Feed refreshed but dnsmasq is not running -- start it with: systemctl start dnsmasq"
	fi
}

# ---- DHCP-server mode ------------------------------------------------------
# For routers that cannot advertise a custom DNS server: the PC takes over LAN
# DHCP and hands out itself as the DNS server, so every device is blocked with
# no per-device config. Requires a static IP on the PC (else it cannot get an
# address once the router's DHCP is off).
nm_connection() {
	nmcli -t -f NAME,DEVICE con show --active |
		awk -F: -v d="$LAN_IFACE" '$2==d{print $1; exit}'
}

revert_nic_to_dhcp() {
	local con="$1"
	nmcli con mod "$con" ipv4.method auto ipv4.addresses "" ipv4.gateway "" ipv4.dns ""
	nmcli con up "$con" >/dev/null 2>&1 || true
}

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

	is_service_active dnsmasq && status_line 0 "dnsmasq: active" || status_line 1 "dnsmasq: NOT active"
	is_service_enabled dnsmasq && status_line 0 "dnsmasq: enabled at boot" || status_line 1 "dnsmasq: NOT enabled"
	[[ -f $DNSMASQ_DROPIN ]] && status_line 0 "Restart=always drop-in present" || status_line 1 "Restart drop-in missing"

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

	systemctl is-active dns-blocklist-refresh.timer &>/dev/null &&
		status_line 0 "refresh timer: active (next $(systemctl show -p NextElapseUSecRealtime --value dns-blocklist-refresh.timer 2>/dev/null))" ||
		status_line 1 "refresh timer: NOT active"

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
		[[ $blocked == "0.0.0.0" ]] &&
			status_line 0 "youtube.com -> ${blocked} (BLOCKED, correct)" ||
			status_line 1 "youtube.com -> ${blocked:-<no answer>} (expected 0.0.0.0)"
		[[ -n $passthru && $passthru != "0.0.0.0" ]] &&
			status_line 0 "example.com -> ${passthru} (passthrough, correct)" ||
			status_line 1 "example.com -> ${passthru:-<no answer>} (expected a real IP)"
	else
		log_warn "install 'dig' (bind) to run the live resolution test."
	fi

	if [[ -s $LOG_FILE ]]; then
		echo
		echo "=== Recent dnsmasq log (${LOG_FILE}) ==="
		tail -5 "$LOG_FILE"
	fi
}

usage() {
	cat <<EOF
Usage: $0 <command>

Commands:
  setup     First-time install: dnsmasq + blocklist feed + refresh timer + firewall (root).
  status    Show whether the blocker is set up and serving, with a live dig test.
  refresh   Rebuild the blocklist feed and reload dnsmasq (root; run by the timer).
  dhcp      Make this PC the LAN DHCP server so every device uses it as DNS (root).
            Use when the router cannot advertise a custom DNS. Disable router DHCP first.
  dhcp-off  Revert DHCP mode: stop serving leases, return the NIC to DHCP-client (root).
  help      Show this message.
EOF
}

main() {
	local cmd="${1:-help}"
	case "$cmd" in
	setup | refresh | dhcp | dhcp-off)
		require_root "$@"
		;;
	esac

	case "$cmd" in
	setup) cmd_setup ;;
	refresh) cmd_refresh ;;
	dhcp) cmd_dhcp ;;
	dhcp-off) cmd_dhcp_off ;;
	status) cmd_status ;;
	help | -h | --help) usage ;;
	*)
		log_error "Unknown command: $cmd"
		usage
		exit 1
		;;
	esac
}

# Guard lets tests source this file to exercise individual functions.
if [[ "${SETUP_DNS_BLOCKER_SKIP_MAIN:-}" != "1" ]]; then
	main "$@"
fi
