#!/bin/bash

# ============================================================================
# Deploy testsAndMisc: fast-forward the live checkout (~/src/testsAndMisc) to
# origin/main. Everything this repo runs on the machine (i3 config, systemd
# units, symlinked scripts, git hooks) executes straight from that checkout,
# so updating it is the deploy.
#
#   scripts/deploy.sh
#
# Idempotent. Uncommitted work in the live checkout is kept: git refuses the
# fast-forward (and this exits non-zero) only when an incoming commit touches
# a file with local edits. Copies installed under /usr/local or /etc by the
# sudo installers are not refreshed here; rerun that installer by hand.
#
# Exits non-zero unless the health check passes: the checkout is on main, its
# HEAD equals origin/main, and core.hooksPath points at the tracked hooks.
# Env: TESTSANDMISC_DIR (default ~/src/testsAndMisc).
# ============================================================================

set -euo pipefail

readonly REPO="${TESTSANDMISC_DIR:-${HOME}/src/testsAndMisc}"
readonly HOOKS_PATH=linux_configuration/.githooks

die() {
	echo "deploy: $1" >&2
	exit 1
}

update_checkout() {
	[[ -d "${REPO}/.git" ]] || die "${REPO} is not a git checkout"
	local branch
	branch="$(git -C "$REPO" rev-parse --abbrev-ref HEAD)"
	[[ "$branch" == main ]] || die "${REPO} is on '${branch}', not main"
	git -C "$REPO" pull --ff-only --quiet origin main ||
		die "git pull --ff-only failed in ${REPO} (diverged, or local edits collide)"
}

health_check() {
	local head remote hooks
	head="$(git -C "$REPO" rev-parse HEAD)"
	remote="$(git -C "$REPO" rev-parse origin/main)"
	[[ "$head" == "$remote" ]] || die "HEAD ${head:0:8} != origin/main ${remote:0:8}"
	hooks="$(git -C "$REPO" config --get core.hooksPath || true)"
	[[ "$hooks" == "$HOOKS_PATH" && -d "${REPO}/${HOOKS_PATH}" ]] ||
		die "core.hooksPath is '${hooks}', want ${HOOKS_PATH} (run meta/scripts/install_hooks.sh)"
	echo "deploy: ${REPO} at ${head:0:8} = origin/main, hooks wired"
}

main() {
	update_checkout
	health_check
}

main "$@"
