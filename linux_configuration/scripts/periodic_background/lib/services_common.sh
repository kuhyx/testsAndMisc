#!/usr/bin/env bash
# lib/services_common.sh — output helpers, root re-exec, deployment-drift
# verification and the shared report-then-fix path used by every check.
#
# Sourced by check_and_enable_services.sh before any check lib. Reads the
# colour globals, DRY_RUN, STATUS_ONLY, ISSUES_FOUND, FIXES_APPLIED and
# SERVICE_STATUS from the caller; appends to MISSING_SCRIPTS.

######################################################################
# Helpers
######################################################################
# Absolute paths the checks below probe are prefixed with $SYSROOT, which is
# empty in production and a fixture tree under test. It is deliberately NOT
# defaulted here: several repairs in this family write outside `run` (chattr,
# find -delete, an append to resolved.conf), so a test that forgot to set it
# would edit the real /etc. Unset is a hard error; empty is the real filesystem.
SYSROOT="${SERVICES_ROOT?SERVICES_ROOT must be set (empty = the real filesystem)}"

msg() { printf "${GREEN}[✓]${NC} %s\n" "$*"; }

note() { printf "${BLUE}[i]${NC} %s\n" "$*"; }

warn() { printf "${YELLOW}[!]${NC} %s\n" "$*"; }

err() { printf "${RED}[✗]${NC} %s\n" "$*"; }

header() { printf "\n${CYAN}=== %s ===${NC}\n" "$*"; }

err_missing_script() {
	err "$*"
	logger -t check-and-enable-services -p user.err "MISSING REPAIR SCRIPT: $*"
	MISSING_SCRIPTS+=("$*")
}

# Query a USER systemd unit from root.
# `sudo -u <user> systemctl --user ...` does NOT work here: sudo gives it no
# XDG_RUNTIME_DIR / DBUS_SESSION_BUS_ADDRESS, so it cannot reach the user bus and
# fails with "Failed to connect to user scope bus via local transport". Every
# check using it therefore reported EVERY user service as "not enabled" — a false
# error for services that were enabled and running (workout-locker was reported
# broken for months while working fine). systemd's own error suggests the fix:
# --machine=<user>@.host connects to another user's bus correctly.
user_systemctl() { # <user> <systemctl args...>
	local u="$1"
	shift
	systemctl --user --machine="${u}@.host" "$@"
}

# Are the pacman hooks that unlock/relock the guarded hosts files installed?
# The hosts guard migrated to guard-lib's GENERIC unlock-all/relock-all hooks
# (which cover every registered file-guard: hosts, nsswitch, resolved, ...), and
# the old per-file 10-unlock-etc-hosts.hook / 90-relock-etc-hosts.hook names have
# not existed since. This check was never updated, so it reported a phantom
# "Pacman hooks not installed" warning forever. pacman_wrapper.sh treats the
# guard-lib pair as authoritative (see pacman_hooks_manage_guard_lib) — match it,
# while still accepting the legacy pair if an older install is present.
hosts_pacman_hooks_installed() {
	[[ -f "${SYSROOT}/etc/pacman.d/hooks/10-guard-lib-unlock-all.hook" ]] &&
		[[ -f "${SYSROOT}/etc/pacman.d/hooks/90-guard-lib-relock-all.hook" ]]
}

# True if guard-lib's file-guard instance <name> is installed AND healthy:
# the path unit is active and the target carries the immutable attribute.
# `guardctl file-guard status` exits 1 for an unregistered instance (missing
# /etc/guard-lib/targets/<name>.conf), so a missing instance and an unhealthy
# one both fail this check without needing separate handling.
guard_lib_instance_healthy() { # <name>
	local name="$1" out
	out=$(guardctl file-guard status "$name" 2>/dev/null) || return 1
	grep -q '^path unit: active$' <<<"$out" || return 1
	grep -q '^target attrs: .*i' <<<"$out" || return 1
}

# Replay a drift manifest written at install time. The manifest holds plain
# sha256sum lines covering BOTH the repo sources an installer copied from and
# the installed copies it produced, so one `sha256sum -c` answers both "has the
# repo moved on?" and "did someone edit the deployed file?".
#
# This exists because an existence check is not a deployment check. On
# 2026-08-03 /usr/local/bin/pacman_wrapper was 19916 B against a 27510 B source
# — missing the policy integrity manifest, the pacman_lock_lib stale-lock fix
# and the guard-lib fallbacks — while every check here reported "ok" hourly,
# because the file was present and /usr/bin/pacman was a symlink. Both of those
# facts stayed true the entire time the wrapper was a week out of date.
#
# Return: 0 verified, 1 drift detected, 2 no manifest (install predates this).
# Callers must treat 2 as actionable rather than a pass: "cannot verify" is
# precisely the state that hid the stale wrapper.
deployment_drift() { # <manifest-path>
	local manifest="$1"
	[[ -f $manifest ]] || return 2
	sha256sum -c --status "$manifest" 2>/dev/null || return 1
	return 0
}

run() {
	if [[ $DRY_RUN -eq 1 ]]; then
		echo -e "${YELLOW}DRY-RUN:${NC} $*"
		return 0
	else
		"$@"
	fi
}

require_root() {
	if [[ $EUID -ne 0 ]]; then
		echo "This script requires root privileges."
		echo "Re-executing with sudo..."
		exec sudo -E bash "$0" "$@"
	fi
}

######################################################################
# Report issues and optionally run fix script
# Usage: report_and_fix issues_array status_var status_key fix_note setup_script verify_service [args...]
######################################################################
report_and_fix() {
	local -n _issues=$1
	local -n _status=$2
	local status_key="$3"
	local fix_note="$4"
	local setup_script="$5"
	local verify_service="${6:-}"
	shift 6
	local script_args=("$@")

	if [[ $_status != "ok" ]]; then
		for issue in "${_issues[@]}"; do
			if [[ $_status == "error" ]]; then
				err "$issue"
			else
				warn "$issue"
			fi
		done
		((ISSUES_FOUND++)) || true

		if [[ $STATUS_ONLY -eq 0 && $_status == "error" ]]; then
			note "$fix_note"
			if [[ -f $setup_script ]]; then
				run bash "$setup_script" "${script_args[@]}"
				((FIXES_APPLIED++)) || true
				# Re-verify after fix
				if [[ $DRY_RUN -eq 0 && -n $verify_service ]] && systemctl is-enabled "$verify_service" &>/dev/null; then
					_status="ok"
				fi
			else
				err_missing_script "Setup script not found: $setup_script"
			fi
		fi
	fi

	set_service_status "$status_key" "$_status"
}

# Record one service's verdict.
#
# The check libs write SERVICE_STATUS while only services_report.sh reads it.
# Split across files that is a write-only global, which shellcheck reports as
# SC2034 in every writing lib — correctly, since the hook runs it with no `-x`
# and cannot see the reader. Routing every write through this setter, which
# lives in the same file as a reader, turns the cross-file global into a
# function call and removes the finding without suppressing it.
#
# Writing an already-recorded key is a caller bug: each check owns exactly one
# key and runs once, so a second write means two checks are fighting over one
# summary row. Fail loudly rather than let the later one win silently.
set_service_status() { # <key> <status>
	local key="$1"
	local value="$2"
	if [[ -n ${SERVICE_STATUS[$key]:-} ]]; then
		err "internal error: status for '${key}' already recorded as '$(get_service_status "$key")'"
		return 1
	fi
	SERVICE_STATUS["$key"]="$value"
}

# Read one service's recorded verdict, defaulting to "unknown".
get_service_status() { # <key>
	printf '%s\n' "${SERVICE_STATUS[$1]:-unknown}"
}
