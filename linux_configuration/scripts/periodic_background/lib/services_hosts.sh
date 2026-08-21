#!/usr/bin/env bash
# lib/services_hosts.sh — the /etc/hosts blocking stack check: the hosts file
# itself, its immutable attribute, the three guard-lib file-guard instances
# (hosts/nsswitch/resolved), the pacman unlock/relock hooks, and the
# systemd-resolved settings that can silently bypass /etc/hosts.
#
# Sourced by check_and_enable_services.sh. The repair half lives in
# services_hosts_fix.sh so both files stay under the 250-line cap.

# Absolute paths the checks below probe are prefixed with $SYSROOT, which is
# empty in production and a fixture tree under test. It is deliberately NOT
# defaulted here: several repairs in this family write outside `run` (chattr,
# find -delete, an append to resolved.conf), so a test that forgot to set it
# would edit the real /etc. Unset is a hard error; empty is the real filesystem.
SYSROOT="${SERVICES_ROOT?SERVICES_ROOT must be set (empty = the real filesystem)}"

check_hosts() {
	header "Hosts File and Guards"

	local status="ok"
	local issues=()

	# Check /etc/hosts exists and has content
	if [[ -f "${SYSROOT}/etc/hosts" ]]; then
		local line_count
		line_count=$(wc -l <"${SYSROOT}/etc/hosts")
		if [[ $line_count -gt 100 ]]; then
			msg "/etc/hosts exists with $line_count lines (StevenBlack list likely installed)"
		else
			issues+=("/etc/hosts has only $line_count lines (StevenBlack list may not be installed)")
			status="warning"
		fi
	else
		issues+=("/etc/hosts does not exist")
		status="error"
	fi

	# Check if hosts file is immutable
	local attrs
	attrs=$(lsattr "${SYSROOT}/etc/hosts" 2>/dev/null | cut -d' ' -f1 || echo "")
	if [[ $attrs == *"i"* ]]; then
		msg "/etc/hosts has immutable attribute set"
	else
		issues+=("/etc/hosts is not immutable")
		status="warning"
	fi

	# Check cached hosts file
	if [[ -f "${SYSROOT}/etc/hosts.stevenblack" ]]; then
		msg "StevenBlack cache exists at ${SYSROOT}/etc/hosts.stevenblack"
	else
		issues+=("StevenBlack cache not found")
		status="warning"
	fi

	# Check the guard-lib "hosts" file-guard instance (path unit active +
	# immutable attribute on the target). Replaces the legacy hosts-guard.path
	# / hosts-bind-mount.service / enforce-hosts.sh checks now that this
	# machine's migration to guard-lib is complete — see
	# migrate_hosts_guard_to_guard_lib.sh.
	if guard_lib_instance_healthy hosts; then
		msg "guard-lib 'hosts' instance is active and enforced"
	else
		issues+=("guard-lib 'hosts' instance is missing or unhealthy")
		status="error"
	fi

	# Check pacman hooks
	if hosts_pacman_hooks_installed; then
		msg "Pacman hooks installed"
	else
		issues+=("Pacman hooks not installed")
		status="warning"
	fi

	# Check nsswitch.conf has 'files' in hosts line
	if [[ -f "${SYSROOT}/etc/nsswitch.conf" ]]; then
		local nsswitch_hosts
		nsswitch_hosts=$(grep '^hosts:' "${SYSROOT}/etc/nsswitch.conf" 2>/dev/null || echo "")
		if echo "$nsswitch_hosts" | grep -qw 'files'; then
			msg "nsswitch.conf hosts line includes 'files'"
		else
			issues+=("nsswitch.conf hosts line missing 'files' — ${SYSROOT}/etc/hosts is bypassed!")
			status="error"
		fi
	else
		issues+=("/etc/nsswitch.conf does not exist")
		status="error"
	fi

	# Check the guard-lib "nsswitch" file-guard instance
	if guard_lib_instance_healthy nsswitch; then
		msg "guard-lib 'nsswitch' instance is active and enforced"
	else
		issues+=("guard-lib 'nsswitch' instance is missing or unhealthy")
		status="error"
	fi

	# Check resolved.conf has ReadEtcHosts=yes
	if [[ -f "${SYSROOT}/etc/systemd/resolved.conf" ]]; then
		local read_etc_hosts
		read_etc_hosts=$(grep -E '^\s*ReadEtcHosts\s*=' "${SYSROOT}/etc/systemd/resolved.conf" 2>/dev/null |
			tail -1 | sed 's/.*=\s*//' | tr -d '[:space:]')
		if [[ "$read_etc_hosts" == "yes" ]]; then
			msg "resolved.conf ReadEtcHosts=yes"
		else
			issues+=("resolved.conf ReadEtcHosts='$read_etc_hosts' — ${SYSROOT}/etc/hosts is bypassed by systemd-resolved!")
			status="error"
		fi

		# Check DNSOverTLS is not enabled
		local dns_over_tls
		dns_over_tls=$(grep -E '^\s*DNSOverTLS\s*=' "${SYSROOT}/etc/systemd/resolved.conf" 2>/dev/null |
			tail -1 | sed 's/.*=\s*//' | tr -d '[:space:]') || true
		if [[ -z "$dns_over_tls" || "$dns_over_tls" == "no" ]]; then
			msg "resolved.conf DNSOverTLS is disabled"
		else
			issues+=("resolved.conf DNSOverTLS='$dns_over_tls' — can bypass ${SYSROOT}/etc/hosts!")
			status="error"
		fi

		# Check for drop-in overrides
		if [[ -d "${SYSROOT}/etc/systemd/resolved.conf.d" ]]; then
			local dropin_count
			dropin_count=$(find "${SYSROOT}/etc/systemd/resolved.conf.d" -name '*.conf' -type f 2>/dev/null | wc -l)
			if [[ "$dropin_count" -gt 0 ]]; then
				issues+=("Found $dropin_count resolved.conf drop-in override(s) — potential bypass!")
				status="error"
			fi
		fi

		# Check immutable attribute
		if command -v lsattr &>/dev/null; then
			if lsattr "${SYSROOT}/etc/systemd/resolved.conf" 2>/dev/null | grep -q '.*i.*e.*'; then
				msg "resolved.conf has immutable attribute"
			else
				issues+=("resolved.conf missing immutable attribute")
				[[ "$status" == "ok" ]] && status="warning"
			fi
		fi
	else
		issues+=("/etc/systemd/resolved.conf does not exist")
		[[ "$status" == "ok" ]] && status="warning"
	fi

	# Check the guard-lib "resolved" file-guard instance
	if guard_lib_instance_healthy resolved; then
		msg "guard-lib 'resolved' instance is active and enforced"
	else
		issues+=("guard-lib 'resolved' instance is missing or unhealthy")
		status="error"
	fi

	# Report issues
	if [[ $status != "ok" ]]; then
		for issue in "${issues[@]}"; do
			if [[ $status == "error" ]]; then
				err "$issue"
			else
				warn "$issue"
			fi
		done
		((ISSUES_FOUND++)) || true

		if [[ $STATUS_ONLY -eq 0 ]]; then
			# The repair half lives in services_hosts_fix.sh; it returns 0 only
			# when the post-repair re-verify passes, so a promotion to "ok" here
			# always reflects a re-checked machine rather than a fix attempt.
			if hosts_repair_all; then
				status="ok"
			fi
		fi
	fi

	set_service_status "hosts" "$status"
}
