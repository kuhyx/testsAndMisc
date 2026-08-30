#!/bin/bash
# The units that run 'verify' by themselves.
#
# Sourced by setup_wireguard_ssh.sh; split out to keep wg_firewall.sh under
# the 250-line cap. Sourced rather than run, so it inherits the caller's
# strict mode and the variables defined above the source line.
#
# 'verify' gates on two invariants and exits non-zero, but nothing invoked
# it. It reported drift only when a human thought to ask -- and the outage it
# exists for is precisely the one nobody thinks to ask about. Twice now the
# repo has carried the docker0 forward rule while /etc/nftables.conf did not,
# and both times a reboot loaded the stale file and cut every bridged
# container off the internet while the host itself stayed online, so nothing
# looked broken.
#
# So it runs at boot, just after the ruleset is loaded, and a failure lands in
# `systemctl --failed`, where it is visible without being looked for. It must
# FAIL, never warn: a warning in the journal is the same as no check at all.

readonly VERIFY_SERVICE="nftables-drift.service"
readonly VERIFY_TIMER="nftables-drift.timer"
readonly SYSTEMD_UNIT_DIR="/etc/systemd/system"

# Rendering is separate from installing so the tests can assert the generated
# content without a daemon-reload, the same split render/write_nftables uses.
#
# The ExecStart deliberately points into the repo checkout rather than a copy
# under /usr/local/bin. The check is "does /etc match what THIS repo
# generates", so a copy would be one more thing that can go stale -- and a
# stale copy of a drift detector agrees with the drift.
render_verify_units() {
	local unit_dir="$1" entry="$2"
	cat >"${unit_dir}/${VERIFY_SERVICE}" <<UNIT
[Unit]
Description=Verify /etc/nftables.conf still matches the repo, and Docker still gets through
Documentation=file://${entry}
# nftables.service is what loads the file being checked, so checking before it
# has run would compare against whatever the previous boot left behind.
# docker.service is ordered for the same reason in reverse: it rebuilds the ip
# filter rules a flush removed, and this must not race that rebuild.
After=nftables.service docker.service network-online.target
Wants=network-online.target
# Not Requires=: if nftables.service is dead the ruleset is NOT loaded, which
# is the most serious version of the fault this unit detects. It must run and
# fail, not be skipped as unsatisfiable.

[Service]
Type=oneshot
# verify only reads: it renders the ruleset into a mktemp file and diffs it,
# and asks nft to list the live forward chain. Anything it tries to write is
# a bug, so make the attempt fail loudly instead of succeeding quietly -- the
# saved LAN_SUBNET lives in the repo under \$HOME, and a root-owned rewrite of
# it would lock the non-root subcommands out of their own config.
ExecStart=${entry} verify
RemainAfterExit=yes
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
UNIT

	cat >"${unit_dir}/${VERIFY_TIMER}" <<UNIT
[Unit]
Description=Re-check the nftables ruleset for drift daily
Documentation=file://${entry}

[Timer]
# The boot run is the gate; this only catches a rule hand-applied to a machine
# that then stays up for weeks. Persistent so a PC that was off at the
# scheduled time still checks once it comes back.
OnCalendar=daily
Persistent=true
Unit=${VERIFY_SERVICE}

[Install]
WantedBy=timers.target
UNIT
}

install_verify_units() {
	local entry="${SCRIPT_DIR}/setup_wireguard_ssh.sh"
	if [[ ! -x $entry ]]; then
		die "cannot find an executable ${entry} for the verify unit to run."
	fi
	render_verify_units "$SYSTEMD_UNIT_DIR" "$entry"
	systemctl daemon-reload
	# The service is enabled but NOT started here: it is a boot-time check,
	# and `enable --now` would run it before the caller has finished writing
	# the ruleset it is meant to check.
	systemctl enable "$VERIFY_SERVICE" >/dev/null
	enable_service "$VERIFY_TIMER"
	log_ok "${VERIFY_SERVICE} will re-check the ruleset at every boot."
	log_info "A failure shows up in: systemctl --failed"
}
