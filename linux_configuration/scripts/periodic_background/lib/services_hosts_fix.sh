#!/usr/bin/env bash
# lib/services_hosts_fix.sh — the repair half of check_hosts.
#
# Split out of services_hosts.sh so both stay under the 250-line cap. The
# detection half decides WHETHER to repair; everything here assumes that
# decision is already made and only does the repairing.
#
# All three helpers go through `run`, so --dry-run prints instead of acting.
# They increment FIXES_APPLIED and may call err_missing_script, exactly as they
# did inline. hosts_repair_all returns 0 when the post-fix re-verify passes, so
# the caller can promote its status to "ok" without reading a global.

# Put 'files' back on the nsswitch.conf hosts line. Without it every /etc/hosts
# entry is bypassed outright, which makes this the highest-severity repair here
# — the blocking stack is silently inert until it is fixed.
hosts_fix_nsswitch() {
	[[ -f /etc/nsswitch.conf ]] || return 0
	local line
	line=$(grep '^hosts:' /etc/nsswitch.conf 2>/dev/null || echo "")
	[[ -n $line ]] || return 0
	if echo "$line" | grep -qw 'files'; then
		return 0
	fi
	note "Fixing nsswitch.conf — adding 'files' to hosts line..."
	# 'files' must precede whichever resolver is present, or the resolver
	# answers first and /etc/hosts never gets consulted.
	if echo "$line" | grep -qw 'resolve'; then
		run sed -i 's/^hosts:\(.*\)resolve/hosts: files\1resolve/' /etc/nsswitch.conf
	elif echo "$line" | grep -qw 'dns'; then
		run sed -i 's/^hosts:\(.*\)dns/hosts:\1files dns/' /etc/nsswitch.conf
	else
		run sed -i 's/^hosts:/hosts: files/' /etc/nsswitch.conf
	fi
	((FIXES_APPLIED++)) || true
	msg "nsswitch.conf fixed: $(grep '^hosts:' /etc/nsswitch.conf)"
}

# Repair the three systemd-resolved settings that can bypass /etc/hosts:
# ReadEtcHosts=no, DNSOverTLS enabled, and drop-in overrides of either. The
# file carries the immutable attribute, so each edit is bracketed by chattr.
hosts_fix_resolved() {
	[[ -f /etc/systemd/resolved.conf ]] || return 0
	local read_etc_hosts
	read_etc_hosts=$(grep -E '^\s*ReadEtcHosts\s*=' /etc/systemd/resolved.conf 2>/dev/null |
		tail -1 | sed 's/.*=\s*//' | tr -d '[:space:]')
	if [[ "$read_etc_hosts" != "yes" ]]; then
		note "Fixing resolved.conf — setting ReadEtcHosts=yes..."
		chattr -i /etc/systemd/resolved.conf 2>/dev/null || true
		if grep -qE '^\s*ReadEtcHosts\s*=' /etc/systemd/resolved.conf; then
			run sed -i -E 's/^\s*ReadEtcHosts\s*=.*/ReadEtcHosts=yes/' /etc/systemd/resolved.conf
		elif grep -q '^\[Resolve\]' /etc/systemd/resolved.conf; then
			run sed -i '/^\[Resolve\]/a ReadEtcHosts=yes' /etc/systemd/resolved.conf
		else
			printf '\n[Resolve]\nReadEtcHosts=yes\n' >>/etc/systemd/resolved.conf
		fi
		chattr +i /etc/systemd/resolved.conf 2>/dev/null || true
		run systemctl restart systemd-resolved
		((FIXES_APPLIED++)) || true
		msg "resolved.conf ReadEtcHosts fixed"
	fi

	local dns_over_tls
	dns_over_tls=$(grep -E '^\s*DNSOverTLS\s*=' /etc/systemd/resolved.conf 2>/dev/null |
		tail -1 | sed 's/.*=\s*//' | tr -d '[:space:]') || true
	if [[ -n "$dns_over_tls" && "$dns_over_tls" != "no" ]]; then
		note "Fixing resolved.conf — disabling DNSOverTLS..."
		chattr -i /etc/systemd/resolved.conf 2>/dev/null || true
		run sed -i -E 's/^\s*DNSOverTLS\s*=.*/#DNSOverTLS=no/' /etc/systemd/resolved.conf
		chattr +i /etc/systemd/resolved.conf 2>/dev/null || true
		run systemctl restart systemd-resolved
		((FIXES_APPLIED++)) || true
		msg "resolved.conf DNSOverTLS disabled"
	fi

	# A drop-in can re-enable either setting without touching resolved.conf, so
	# the two repairs above are not durable while any drop-in survives.
	if [[ -d /etc/systemd/resolved.conf.d ]]; then
		local dropin_count
		dropin_count=$(find /etc/systemd/resolved.conf.d -name '*.conf' -type f 2>/dev/null | wc -l)
		if [[ "$dropin_count" -gt 0 ]]; then
			note "Removing $dropin_count resolved.conf drop-in override(s)..."
			chattr -i /etc/systemd/resolved.conf.d 2>/dev/null || true
			find /etc/systemd/resolved.conf.d -name '*.conf' -type f -delete
			chattr +i /etc/systemd/resolved.conf.d 2>/dev/null || true
			run systemctl restart systemd-resolved
			((FIXES_APPLIED++)) || true
		fi
	fi
}

# Reinstall the hosts file and re-run the guard-lib migration when needed, then
# re-verify. Returns 0 only if all four guard-lib facts hold afterwards, which
# is what lets the caller promote its status to "ok".
#
# Under --dry-run nothing was actually changed, so re-verifying would report on
# the unrepaired machine; return 1 there instead of claiming a fix landed.
hosts_repair_all() {
	# Order matters and matches the pre-split script: resolver config first, so
	# that a hosts file installed below is actually consulted once it lands.
	hosts_fix_nsswitch
	hosts_fix_resolved

	if [[ ! -f /etc/hosts ]] || [[ $(wc -l </etc/hosts) -lt 100 ]]; then
		note "Installing hosts file..."
		if [[ -f $HOSTS_INSTALL_SCRIPT ]]; then
			run bash "$HOSTS_INSTALL_SCRIPT"
			((FIXES_APPLIED++)) || true
		else
			err_missing_script "Hosts install script not found: $HOSTS_INSTALL_SCRIPT"
		fi
	fi

	# The migration script documents itself as idempotent, so re-running it
	# against an already-migrated healthy machine is a no-op.
	if ! guard_lib_instance_healthy hosts ||
		! guard_lib_instance_healthy nsswitch ||
		! guard_lib_instance_healthy resolved ||
		! hosts_pacman_hooks_installed; then
		note "Repairing guard-lib hosts/nsswitch/resolved instances..."
		if [[ -f $GUARD_LIB_MIGRATE_SCRIPT ]]; then
			run bash "$GUARD_LIB_MIGRATE_SCRIPT"
			((FIXES_APPLIED++)) || true
		else
			err_missing_script "Guard-lib migration script not found: $GUARD_LIB_MIGRATE_SCRIPT"
		fi
	fi

	[[ $DRY_RUN -eq 0 ]] || return 1
	guard_lib_instance_healthy hosts &&
		guard_lib_instance_healthy nsswitch &&
		guard_lib_instance_healthy resolved &&
		hosts_pacman_hooks_installed
}
