#!/bin/bash
# Preconditions/setup for diagnose_pacman_hook_stall.sh.
# Sourced, not executed; inherits the caller's strict mode and globals.

require_root() {
	if [[ $EUID -ne 0 ]]; then
		exec sudo -E bash "$0" "$@"
	fi
}

validate_requirements() {
	local tool
	for tool in "$PACMAN_BIN" ps awk sed journalctl; do
		command -v "$tool" >/dev/null 2>&1 || [[ -x "$tool" ]] || {
			echo "Error: required tool '$tool' not found" >&2
			exit 1
		}
	done

	[[ -r "$PACMAN_LOG" ]] || {
		echo "Error: cannot read $PACMAN_LOG" >&2
		exit 1
	}

	# Refuse to run alongside another *transaction*: a collision would look
	# exactly like the stall we are hunting. db.lck is the authoritative signal
	# - pacman holds it for the whole transaction. Deliberately NOT a pgrep for
	# "pacman": read-only queries (pacman -Qi) take no lock, are harmless, and
	# run constantly here from background services.
	if [[ -e "$PACMAN_LOCK" ]]; then
		echo "Error: $PACMAN_LOCK exists - another transaction is in" >&2
		echo "flight (or a stale lock remains). Resolve it before running." >&2
		exit 1
	fi
}

# Resolve the cached package file for the installed version of $PACKAGE.
resolve_package_file() {
	local version
	version="$("$PACMAN_BIN" -Q "$PACKAGE" 2>/dev/null | awk '{print $2}')"
	[[ -n "$version" ]] || {
		echo "Error: package '$PACKAGE' is not installed" >&2
		exit 1
	}

	local candidate
	for candidate in "$CACHE_DIR/$PACKAGE-$version"-*.pkg.tar.zst; do
		[[ -e "$candidate" ]] || continue
		printf '%s\n' "$candidate"
		return 0
	done

	echo "Error: no cached package for $PACKAGE-$version in $CACHE_DIR" >&2
	echo "Hint: run '$PACMAN_BIN -Sw $PACKAGE' first" >&2
	exit 1
}
