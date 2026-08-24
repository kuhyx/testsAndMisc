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

# Absolute path to the human user's home directory -- the extracted repos are
# cloned there, never into /root.
#
# Three cases, and all three happen in practice:
#   1. run directly by the user      -> $USER
#   2. run via sudo                  -> SUDO_USER ($HOME is /root here)
#   3. run by systemd as root        -> NEITHER is set and `id -un` is "root".
#      Falling back to root's home yields /root/<repo>, which never exists.
#      dns-blocklist-refresh.service hit exactly this and died with
#      "Feed generator not found: /root/hosts-blocker/...".
#
# For case 3 fall back to REPO_OWNER_USER, which defaults to the owner of this
# very file -- the checkout the caller is running from is itself the best
# evidence of whose home the sibling repos are in.
extracted_repo_home() {
	local real_user real_home
	real_user="${SUDO_USER:-${USER:-$(id -un)}}"
	if [[ $real_user == "root" ]]; then
		real_user="${REPO_OWNER_USER:-$(stat -c %U "${BASH_SOURCE[0]}" 2>/dev/null)}"
		[[ -n $real_user && $real_user != "root" ]] || real_user="root"
	fi
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

# extracted_repo_clone <repo-name>
# Clones a missing extracted repo into its expected location and prints that
# path. Used by install paths that must work on a bare machine, where "clone it
# yourself" is not actionable -- there is nothing to clone it with yet.
#
# The clone runs as the HUMAN user, never as root. Installers re-exec themselves
# via sudo, and a root-owned ~/screen-locker silently breaks every later git
# operation the user makes in it. A sandbox never catches this (the guest runs
# as root throughout), so the ownership is forced here rather than assumed.
#
# A failure here is loud and fatal to the caller: a repo that cannot be fetched
# must never degrade into a silently skipped module.
extracted_repo_clone() {
	local name="$1" dir url real_user
	dir="$(extracted_repo_dir "$name")"
	url="https://github.com/kuhyx/$name.git"
	real_user="${SUDO_USER:-${USER:-$(id -un)}}"

	printf 'Cloning missing repo "%s" -> %s\n' "$name" "$dir" >&2
	if [[ $EUID -eq 0 && $real_user != "root" ]]; then
		sudo -u "$real_user" git clone --quiet "$url" "$dir" >&2 || return 1
	else
		git clone --quiet "$url" "$dir" >&2 || return 1
	fi
	printf '%s' "$dir"
}

# require_extracted_repo <repo-name> [what-needs-it]
# Prints the directory on success. Clones the repo if it is missing; only if
# that clone fails does it explain how to get it and return 1 -- callers decide
# whether that is fatal, but none of them may treat it as "nothing to do".
require_extracted_repo() {
	local name="$1" what="${2:-this script}" dir
	dir="$(extracted_repo_dir "$name")"
	if [[ ! -d $dir ]]; then
		# Try to fetch it before giving up: on a fresh machine the repo is
		# simply not there yet, and that is recoverable without the user.
		if extracted_repo_clone "$name" >/dev/null 2>&1 && [[ -d $dir ]]; then
			printf '%s' "$dir"
			return 0
		fi
	fi
	if [[ ! -d $dir ]]; then
		printf '\n' >&2
		printf 'ERROR: %s needs the extracted "%s" repo. It is not checked out,\n' \
			"$what" "$name" >&2
		printf '       and cloning it automatically FAILED (no network? bad URL?).\n' >&2
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
