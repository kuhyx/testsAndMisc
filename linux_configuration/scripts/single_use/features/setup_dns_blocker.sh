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
readonly WATCHDOG_SERVICE="/etc/systemd/system/dnsmasq-watchdog.service"
readonly WATCHDOG_TIMER="/etc/systemd/system/dnsmasq-watchdog.timer"
# Optional DHCP-server mode (for routers that cannot advertise a custom DNS).
readonly DHCP_CONF="/etc/dnsmasq.d/lan-dhcp.conf"
readonly DHCP_LEASE="12h"
readonly DHCP_START_HOST="10" # .10 .. .150 mirrors a common router default range
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

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
# shellcheck source=lib/dns_units.sh
source "$SCRIPT_DIR/lib/dns_units.sh"
# shellcheck source=lib/dns_firewall.sh
source "$SCRIPT_DIR/lib/dns_firewall.sh"
# shellcheck source=lib/dns_dhcp.sh
source "$SCRIPT_DIR/lib/dns_dhcp.sh"


cmd_setup() {
	detect_lan
	install_dnsmasq
	prepare_dirs
	build_feed
	write_dnsmasq_conf
	install_restart_dropin
	install_refresh_timer
	install_watchdog
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
