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
	if ! command -v docker >/dev/null 2>&1; then
		echo "deploy_build: docker not found — mount NOT verified." >&2
		return 0
	fi
	running="$(docker ps --format '{{.Names}}' 2>/dev/null || true)"
	if ! grep -qx "$CONTAINER" <<<"$running"; then
		echo "deploy_build: ${CONTAINER} not running — mount NOT verified." >&2
		return 0
	fi

	host_inode="$(stat -c %i "$LIVE")"
	# `docker exec` reports OCI runtime errors on STDOUT, so 2>/dev/null does not
	# suppress them and a failure arrives as a long string rather than as empty
	# output. Require an actual inode number instead of merely non-empty.
	container_inode="$(docker exec "$CONTAINER" stat -c %i /srv 2>/dev/null || true)"
	if [[ ! $container_inode =~ ^[0-9]+$ ]]; then
		echo "deploy_build: could not read /srv inode from ${CONTAINER} — mount NOT verified." >&2
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
	# Both entry points run this same script — setup_kcd2_dice_solver.sh calls it
	# directly, and the post-commit hook starts a unit that runs it — so one lock
	# closes the race between them. Without it, a second run's `vite --emptyOutDir`
	# truncates dist.staging while the first run's rsync is still reading it:
	# rsync exits 24, `set -e` stops the script before assert_mount_live, and dist/
	# is left holding a fresh index.html that references assets which never
	# arrived. Nothing downstream notices — `try_files` serves index.html for the
	# missing chunks, so the browser is handed HTML where it expects JavaScript and
	# no 404 reaches any log.
	#
	# Wait rather than fail: a rebuild that arrives during a setup run still needs
	# to happen, and the unit has no start timeout.
	exec 9>"${SCRIPT_DIR}/.deploy.lock"
	flock -w 600 9 || die "another deploy_build is still running after 10 minutes."

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
