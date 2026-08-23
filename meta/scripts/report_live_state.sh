#!/usr/bin/env bash

# ============================================================================
# Report every place on this machine that points into this repo.
#
# The restructure moves whole subtrees out of testsAndMisc. Anything that
# names a path inside the repo - a systemd unit, an /etc config, a symlink on
# PATH - keeps pointing at the old location and breaks silently once the
# target moves. This script is the checklist: run it before a move to record
# what must be repointed, and after a move to prove nothing was missed.
#
#   report_live_state.sh              # human-readable report
#   report_live_state.sh --check      # exit 1 if anything still points here
#
# --check is the post-move gate. A clean run means no live reference remains.
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly REPO="${REPO:-$HOME/testsAndMisc}"

CHECK_ONLY=0

usage() {
	echo "Usage: $SCRIPT_NAME [--check]"
	echo "Options:"
	echo "  --check       Exit 1 if any live reference into the repo remains"
	echo "  -h, --help    Show this help"
	exit 0
}

# Units whose ExecStart/WorkingDirectory/Environment names a repo path.
# Root units need no privilege to read; user units live under $HOME.
report_systemd() {
	echo "## systemd units"
	local found=0 unit
	while IFS= read -r unit; do
		[[ -n "$unit" ]] || continue
		found=1
		printf '  %s\n' "$unit"
		grep -n "$REPO\|%h/testsAndMisc" "$unit" | sed 's/^/      /'
	done < <(grep -rl "$REPO\|%h/testsAndMisc" \
		/etc/systemd/system "$HOME/.config/systemd/user" 2>/dev/null | sort)
	((found)) || echo "  (none)"
	return "$found"
}

# Non-unit config under /etc that hardcodes a repo path (guard-lib targets,
# sudoers drop-ins, pacman hooks).
report_etc() {
	echo "## /etc references"
	local found=0 path
	while IFS= read -r path; do
		[[ -n "$path" ]] || continue
		case "$path" in */systemd/*) continue ;; esac
		found=1
		printf '  %s\n' "$path"
		grep -n "$REPO" "$path" 2>/dev/null | sed 's/^/      /'
	done < <(grep -rl "$REPO" /etc 2>/dev/null | sort)
	((found)) || echo "  (none)"
	return "$found"
}

# Scripts INSTALLED outside the repo that name a path inside it. These are the
# easiest references to miss: the copy under /usr/local/bin is what actually
# runs, so grepping the repo for its own paths never finds them, and a stale
# one fails at whatever hour its timer next fires.
report_installed() {
	echo "## installed scripts referencing the repo"
	local found=0 path
	while IFS= read -r path; do
		[[ -n "$path" ]] || continue
		found=1
		printf '  %s\n' "$path"
		grep -n "$REPO" "$path" 2>/dev/null | sed 's/^/      /'
	done < <(grep -rl "$REPO" /usr/local/bin /usr/local/lib 2>/dev/null | sort)
	((found)) || echo "  (none)"
	return "$found"
}

# Symlinks anywhere in $HOME resolving into the repo: i3blocks, ~/.local/bin,
# oh-my-zsh custom. Depth 4 covers every known location without walking the
# whole home directory.
report_symlinks() {
	echo "## symlinks into the repo"
	local found=0 link target
	while IFS= read -r link; do
		[[ -n "$link" ]] || continue
		found=1
		target="$(readlink "$link")"
		printf '  %s -> %s\n' "$link" "$target"
	done < <(find "$HOME" -maxdepth 4 -type l -lname "*testsAndMisc*" \
		-not -path "$REPO/*" 2>/dev/null | sort)
	((found)) || echo "  (none)"
	return "$found"
}

main() {
	local any=0
	report_systemd || any=1
	echo
	report_etc || any=1
	echo
	report_installed || any=1
	echo
	report_symlinks || any=1

	if ((CHECK_ONLY)); then
		if ((any)); then
			echo
			echo "$SCRIPT_NAME: live references into $REPO remain (see above)" >&2
			return 1
		fi
		echo
		echo "$SCRIPT_NAME: no live reference points into $REPO"
	fi
	return 0
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	--check)
		CHECK_ONLY=1
		shift
		;;
	-h | --help)
		usage
		;;
	*)
		echo "Unknown option: $1" >&2
		exit 1
		;;
	esac
done

main
