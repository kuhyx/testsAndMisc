#!/bin/bash
# Run a command under this machine's heavy-job lock, if it has one.
#
# Front-end for .pre-commit-config.yaml so the config stays portable: the lock
# lives at a machine-specific absolute path (installed by
# install_pacman_wrapper.sh), and hardcoding that into a tracked config would
# break the hook on any clone that has not installed it. Missing lock => run the
# command unserialised, exactly as before.
#
# Usage: run_with_heavy_lock.sh <lock-name> <command> [args...]

set -uo pipefail

readonly HEAVY_JOB_LOCK_LIB="/usr/local/bin/heavy_job_lock.sh"

if [[ $# -lt 2 ]]; then
	echo "usage: $(basename "$0") <lock-name> <command> [args...]" >&2
	exit 2
fi

lock_name="$1"
shift

if [[ -r $HEAVY_JOB_LOCK_LIB ]]; then
	# shellcheck source=/dev/null
	source "$HEAVY_JOB_LOCK_LIB"
	with_heavy_lock "$lock_name" -- "$@"
	exit $?
fi

exec "$@"
