#!/bin/bash
# Resolve the on-disk location of repos that were EXTRACTED out of this
# monorepo, so callers that still orchestrate them can find them.
#
# Why this exists: when screen_locker was extracted, check_and_enable_services
# kept pointing at python_pkg/screen_locker/, which had stopped existing. The
# result was a red "error" for a service that was installed and enabled the
# whole time, while its "fix" silently did nothing. A missing extracted repo
# must be LOUD, never a silent skip.
#
# $HOME is wrong here: several callers re-exec themselves via sudo, where
# $HOME is /root. Resolve the invoking user's home instead, the same way
# check_and_enable_services.sh already does for screen-locker.

# Absolute path to the invoking (non-root) user's home directory.
extracted_repo_home() {
	local real_user real_home
	real_user="${SUDO_USER:-${USER:-$(id -un)}}"
	real_home="$(getent passwd "$real_user" 2>/dev/null | cut -d: -f6)"
	[[ -n $real_home ]] || real_home="/home/$real_user"
	printf '%s' "$real_home"
}

# extracted_repo_dir <repo-name>
# Prints the expected checkout path. An override env var (e.g.
# HOSTS_BLOCKER_DIR for hosts-blocker) wins, so a non-standard checkout does
# not require editing these scripts.
extracted_repo_dir() {
	local name="$1" var override
	var="$(printf '%s' "$name" | tr '[:lower:]-' '[:upper:]_')_DIR"
	override="${!var:-}"
	if [[ -n $override ]]; then
		printf '%s' "$override"
		return 0
	fi
	printf '%s/%s' "$(extracted_repo_home)" "$name"
}

# require_extracted_repo <repo-name> [what-needs-it]
# Prints the directory on success. On failure, explains how to get it and
# returns 1 -- callers decide whether that is fatal, but none of them may
# treat it as "nothing to do".
require_extracted_repo() {
	local name="$1" what="${2:-this script}" dir
	dir="$(extracted_repo_dir "$name")"
	if [[ ! -d $dir ]]; then
		printf '\n' >&2
		printf 'ERROR: %s needs the extracted "%s" repo, which is not checked out.\n' \
			"$what" "$name" >&2
		printf '  expected at: %s\n' "$dir" >&2
		printf '  clone it:    git clone https://github.com/kuhyx/%s %s\n' \
			"$name" "$dir" >&2
		printf '  or set:      %s_DIR=/path/to/%s\n' \
			"$(printf '%s' "$name" | tr '[:lower:]-' '[:upper:]_')" "$name" >&2
		printf '\n' >&2
		return 1
	fi
	printf '%s' "$dir"
}
