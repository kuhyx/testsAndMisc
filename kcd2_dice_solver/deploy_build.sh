#!/bin/bash
#
# deploy_build.sh — build the static bundle that dice.kuhy.duckdns.org serves.
#
# The single build path, used by both setup_kcd2_dice_solver.sh and the
# post-commit auto-rebuild, so the live site can never be produced two
# different ways.
#
# Why it does not just run `vite build`:
#
#   The serving container bind-mounts dist/ at /srv. A bind mount follows the
#   INODE, so anything that replaces the directory (rm -rf dist && mv new dist)
#   silently detaches the mount until the container is restarted — the site then
#   serves the old files forever with no error anywhere. And a plain `vite build`
#   empties dist/ before writing, so the site 404s for the length of the build.
#
#   Building into dist.staging/ and rsyncing into dist/ avoids both, but only
#   with --delete-after --delay-updates: plain --delete removes stale files
#   BEFORE writing the new ones, so a client that fetched index.html moments
#   earlier can 404 on the very asset it is asking for.
#
#   Preserving the inode is necessary but not sufficient, so the publish is
#   followed by a check that the container is still mounted on this directory —
#   see assert_mount_live for why that cannot be done by watching the inode here.
#
# Usage:
#   deploy_build.sh          Build and publish into dist/.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
readonly STAGING="${SCRIPT_DIR}/dist.staging"
readonly LIVE="${SCRIPT_DIR}/dist"
# Must match setup_kcd2_dice_solver.sh's DICE_CONTAINER.
readonly CONTAINER="kcd2-dice"

die() {
	echo "deploy_build: $1" >&2
	exit 1
}

# nvm-installed toolchains are not on PATH for systemd/git-hook invocations.
ensure_toolchain() {
	if [[ -s ${NVM_DIR:-$HOME/.nvm}/nvm.sh ]]; then
		# shellcheck disable=SC1091  # sourced at runtime, path varies by machine
		source "${NVM_DIR:-$HOME/.nvm}/nvm.sh"
	fi
	command -v node >/dev/null || die "node not found."
	command -v pnpm >/dev/null || die "pnpm not found."
	command -v rsync >/dev/null || die "rsync not found."
}

# Confirm the serving container is still mounted on THIS directory.
#
# Watching dist/'s own inode across the rsync cannot detect a detached mount and
# never could: rsync into an existing directory never changes it, and if dist/
# had already been removed (it is gitignored, so `git clean -xdff` removes it)
# the mkdir above recreates it at a fresh inode before anything is measured.
# Either way the check passes while the container serves the pre-deletion
# snapshot forever, with no error anywhere. The only thing that actually
# answers the question is what the CONTAINER sees.
assert_mount_live() {
	local running host_inode container_inode
	command -v docker >/dev/null 2>&1 || return 0
	running="$(docker ps --format '{{.Names}}' 2>/dev/null || true)"
	grep -qx "$CONTAINER" <<<"$running" || return 0

	host_inode="$(stat -c %i "$LIVE")"
	container_inode="$(docker exec "$CONTAINER" stat -c %i /srv 2>/dev/null || true)"
	if [[ -z $container_inode ]]; then
		echo "deploy_build: could not read /srv inode from ${CONTAINER}; skipping mount check." >&2
		return 0
	fi
	if [[ $host_inode != "$container_inode" ]]; then
		echo "deploy_build: dist/ was replaced — ${CONTAINER} is serving a detached copy." >&2
		echo "deploy_build: restarting ${CONTAINER} to re-attach the bind mount…" >&2
		docker restart "$CONTAINER" >/dev/null
		container_inode="$(docker exec "$CONTAINER" stat -c %i /srv 2>/dev/null || true)"
		[[ $host_inode == "$container_inode" ]] ||
			die "${CONTAINER} still not mounted on ${LIVE} after a restart."
		echo "deploy_build: ${CONTAINER} re-attached." >&2
	fi
}

main() {
	ensure_toolchain
	cd "$SCRIPT_DIR"

	echo "Installing dependencies…"
	pnpm install --frozen-lockfile

	echo "Building into dist.staging…"
	pnpm exec tsc -b
	pnpm exec vite build --outDir dist.staging --emptyOutDir

	# Fail before touching the live directory, never after.
	[[ -f "${STAGING}/index.html" ]] || die "build produced no index.html."

	mkdir -p "$LIVE"
	rsync -a --delete-after --delay-updates "${STAGING}/" "${LIVE}/"
	assert_mount_live

	echo "Published $(find "$LIVE" -type f | wc -l) files to ${LIVE} (inode $(stat -c %i "$LIVE"))."
}

main "$@"
