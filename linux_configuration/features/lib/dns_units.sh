#!/bin/bash
# dnsmasq config, drop-in, refresh timer and watchdog units.
#
# Sourced by setup_dns_blocker.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode.

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

# The whole LAN's DHCP/DNS depends on this one process. Restart=always in the
# drop-in only catches an actual crash; an incident on 2026-07-23 found
# dnsmasq dead with ZERO error logged (no crash, no "Stopping"/"Stopped" line
# either -- consistent with something issuing a plain stop, not a failure) and
# it stayed down for hours, silently, until noticed by a phone unable to join
# WiFi. Mirrors the existing shutdown-timer-monitor-watchdog pattern used
# elsewhere in this repo: same 5-minute cadence, same is-active-or-start shape,
# plus a logger call so a future incident leaves a trace instead of none.
install_watchdog() {
	cat >"$WATCHDOG_SERVICE" <<'EOF'
[Unit]
Description=Watchdog for dnsmasq (LAN DHCP/DNS)
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'systemctl is-active --quiet dnsmasq || { logger -t dnsmasq-watchdog "dnsmasq was down -- restarting"; systemctl restart dnsmasq; }'
EOF
	cat >"$WATCHDOG_TIMER" <<'EOF'
[Unit]
Description=Watchdog Timer for dnsmasq

[Timer]
OnBootSec=60
OnUnitActiveSec=300
Persistent=true

[Install]
WantedBy=timers.target
EOF
}
