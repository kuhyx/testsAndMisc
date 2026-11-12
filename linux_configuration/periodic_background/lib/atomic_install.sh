#!/bin/bash
# Atomic install of live /usr/local/bin scripts for the periodic system setup.
#
# Sourced by setup_periodic_system.sh and periodic_browser.sh.
#
# Why not `sed ... > /usr/local/bin/x.sh`: that truncates the file in place.
# bash reads a script lazily, so a service already running it (the hosts
# monitor loops forever) can execute a half-new file. Rendering beside the
# target and renaming over it gives the target a NEW inode; a running instance
# keeps reading the old one until it exits or is restarted.
# Fail-closed: a template that is missing or fails `bash -n` leaves the live
# file untouched and returns non-zero.

# install_rendered_script <template> <dest> [sed args...]
# Renders <template> through sed with the given args into a temp file in
# dirname(<dest>) (same filesystem, so mv is a rename), syntax-checks it, sets
# mode 0755 and root ownership when run as root, then renames it over <dest>.
install_rendered_script() {
	local template="$1" dest="$2"
	shift 2
	local tmp
	[[ -f $template ]] || {
		echo "Error: template not found: $template" >&2
		return 1
	}
	tmp="$(mktemp "${dest}.XXXXXX")" || return 1
	# `-e ''` keeps sed valid when the caller passes no expressions.
	if sed -e '' "$@" "$template" >"$tmp" &&
		bash -n "$tmp" &&
		chmod 0755 "$tmp" &&
		{ [[ $EUID -ne 0 ]] || chown root:root "$tmp"; } &&
		mv -f "$tmp" "$dest"; then
		return 0
	fi
	rm -f "$tmp"
	echo "Error: not installing $dest (render or syntax check failed)" >&2
	return 1
}

# restart_if_active <unit>
# Restarts a unit onto a freshly installed script, but only if it is running:
# the installer must not start a service the user stopped on purpose.
restart_if_active() {
	local unit="$1"
	if systemctl is-active "$unit" >/dev/null 2>&1; then
		systemctl restart "$unit"
		echo "✓ Restarted $unit onto the new script"
	fi
	return 0
}
