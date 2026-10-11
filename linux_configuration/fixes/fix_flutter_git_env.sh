#!/bin/bash

# ============================================================================
# Stop the Flutter SDK misreading YOUR repository as itself inside git hooks.
#
# `git commit` / `git push` export GIT_DIR (and GIT_WORK_TREE,
# GIT_INDEX_FILE) to every hook they run. The flutter tool shells out to git
# to identify its own SDK, and `git -C "$FLUTTER_ROOT" rev-parse HEAD`
# (bin/internal/shared.sh) does NOT beat an inherited GIT_DIR -- `-C` only
# changes directory, while GIT_DIR overrides repository discovery outright:
#
#     $ git -C /opt/flutter rev-parse HEAD
#     058e0af2c2...                                  <- Flutter's HEAD
#     $ GIT_DIR=~/some-repo/.git git -C /opt/flutter rev-parse HEAD
#     84bd550331...                                  <- YOUR repo's HEAD
#
# So inside a hook, `flutter --version` reports your project as the SDK, pub
# resolves the SDK as "0.0.0-unknown" and every version constraint becomes
# unsatisfiable ("... is forbidden"). Worse, flutter caches that answer in
# bin/cache/flutter.version.json, so the corruption outlives the hook and
# follows the next caller into an unrelated repository -- which is why the
# same command passes when you re-run it by hand and fails again next push.
#
# Upstream already unsets these variables in bin/internal/content_aware_hash.sh
# and bin/internal/update_engine_version.sh, but not in the version path.
#
# THE FIX: a wrapper ahead of /usr/bin on PATH that strips the git-hook
# variables and hands off to the real binary. Per-call `env -u GIT_DIR ...` in
# each hook works too, but only for as long as every future hook author
# remembers; this makes the failure impossible for every caller in every repo.
#
# Deliberately NOT patching /opt/flutter/bin/internal/shared.sh: that file is
# owned by the flutter-bin package and the next update would silently restore
# the bug.
#
# Usage: fix_flutter_git_env.sh [--check | --uninstall]
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly BIN_DIR="${HOME}/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
readonly SCRIPT_DIR
WRAPPER="$(readlink -f "${SCRIPT_DIR}/../scripts/flutter-git-env-wrapper.sh")"
readonly WRAPPER
readonly LEGACY_DIR="${HOME}/.local/share/flutter-git-env"
# Every SDK entry point that shells out to git to identify itself.
readonly TOOLS=(flutter dart)

log() { echo "$SCRIPT_NAME: $*"; }

fail() {
	echo "$SCRIPT_NAME: $*" >&2
	exit 1
}

# The wrapper is tracked in the repo; ~/.local/bin only holds symlinks to it.
# A copy left by an older install (LEGACY_DIR) is generated, so it is removed.
check_wrapper() {
	[[ -x $WRAPPER ]] || fail "tracked wrapper missing: $WRAPPER"
	mkdir -p "$BIN_DIR"
	rm -rf "$LEGACY_DIR"
}

link_tools() {
	local tool link
	for tool in "${TOOLS[@]}"; do
		link="${BIN_DIR}/${tool}"
		if [[ -e $link && ! -L $link ]]; then
			fail "$link exists and is not a symlink — refusing to overwrite it"
		fi
		ln -sfn "$WRAPPER" "$link"
		log "linked $link -> $WRAPPER"
	done
}

check_path() {
	case ":$PATH:" in
	*":$BIN_DIR:"*) ;;
	*) fail "$BIN_DIR is not on PATH — the wrapper would never be used" ;;
	esac
	local resolved
	for tool in "${TOOLS[@]}"; do
		resolved="$(command -v "$tool" || true)"
		[[ $resolved == "${BIN_DIR}/${tool}" ]] ||
			fail "$tool resolves to '$resolved', not the wrapper — check PATH order"
	done
}

# The real test: does the SDK still know what it is with GIT_DIR poisoned?
verify() {
	local probe_repo probe_version
	probe_repo="$(mktemp -d)"
	git -C "$probe_repo" init -q
	git -C "$probe_repo" -c user.email=x@y -c user.name=x commit -q --allow-empty -m probe

	probe_version="$(GIT_DIR="$probe_repo/.git" flutter --version 2>&1 | head -1 || true)"
	rm -rf "$probe_repo"

	if grep -q '0\.0\.0-unknown' <<<"$probe_version"; then
		fail "still broken: flutter reports an unknown SDK under GIT_DIR"
	fi
	if ! grep -q 'flutter/flutter' <<<"$probe_version"; then
		fail "still broken: flutter reports '$probe_version' under GIT_DIR"
	fi
	log "verified: $probe_version"
}

uninstall() {
	local tool link
	for tool in "${TOOLS[@]}"; do
		link="${BIN_DIR}/${tool}"
		if [[ -L $link && "$(readlink -f "$link")" == "$WRAPPER" ]]; then
			rm -f "$link"
			log "removed $link"
		fi
	done
	rm -rf "$LEGACY_DIR"
	log "uninstalled"
}

main() {
	case "${1:-}" in
	--uninstall)
		uninstall
		return
		;;
	--check)
		[[ -x $WRAPPER ]] || fail "wrapper is not installed"
		check_path
		verify
		return
		;;
	"") ;;
	*) fail "unknown option: $1 (expected --check or --uninstall)" ;;
	esac

	command -v flutter >/dev/null 2>&1 || fail "flutter is not on PATH"
	check_wrapper
	link_tools
	check_path
	verify
	log "done — flutter/dart now ignore an inherited GIT_DIR"
}

main "$@"
