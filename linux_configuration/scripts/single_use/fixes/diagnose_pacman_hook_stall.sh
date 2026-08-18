#!/bin/bash

# ============================================================================
# diagnose_pacman_hook_stall.sh
#
# Reproduces and instruments the intermittent pacman freeze that happens at the
# FIRST PreTransaction hook of a transaction:
#
#     :: Running pre-transaction hooks...
#     (1/2) guard-lib: unlocking protected files before pacman transaction
#     <hangs for minutes>
#
# /var/log/pacman.log shows the hook's "running '...hook'..." line and then
# nothing at all - the next entry is the user's retry. Five such transactions
# were abandoned between 2026-07-29 and 2026-08-03. The hook script itself is
# provably a no-op on this machine (/etc/guard-lib/targets is empty, so its
# loop body never executes), which means the stall is pacman forking/exec'ing
# the hook, not the hook doing work.
#
# This script drives real transactions in a loop and, when one stalls, captures
# the kernel-side evidence needed to tell "blocked in a syscall" from "the box
# could not spawn a process": /proc/<pid>/stack, wchan, syscall, the process
# tree, and memory/PSI counters.
#
# The repro target is a 0-file meta-package (base-devel), reinstalled from the
# local cache: a real transaction that fires every hook but writes no files and
# needs no network.
# ============================================================================

set -euo pipefail

# shellcheck source=lib/pacman_hook_stall_summary.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/pacman_hook_stall_summary.sh"

# shellcheck source=lib/pacman_hook_stall_usage.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/pacman_hook_stall_usage.sh"

# shellcheck source=lib/pacman_hook_stall_watch.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/pacman_hook_stall_watch.sh"

# shellcheck source=lib/pacman_hook_stall_capture.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/pacman_hook_stall_capture.sh"

# shellcheck source=lib/pacman_hook_stall_load.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/pacman_hook_stall_load.sh"

# shellcheck source=lib/pacman_hook_stall_setup.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/pacman_hook_stall_setup.sh"

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
# All four below are env-overridable (not hardcoded readonly) so the test
# harness can point them at fakes instead of the real machine; production
# gets the same defaults as before since nothing else sets these.
: "${PACMAN_BIN:=/usr/bin/pacman.orig}"
readonly PACMAN_BIN
: "${PACMAN_LOG:=/var/log/pacman.log}"
readonly PACMAN_LOG
: "${CACHE_DIR:=/var/cache/pacman/pkg}"
readonly CACHE_DIR
: "${PACMAN_LOCK:=/var/lib/pacman/db.lck}"
readonly PACMAN_LOCK

# Defaults
RUNS=40
PACKAGE="base-devel"
STALL_TIMEOUT=20 # seconds with no new pacman.log line => declare a stall
HARD_TIMEOUT=120 # seconds before we give up and kill the stalled transaction
OUT_DIR="/var/log/pacman-hook-stall"
WITH_LOAD=0
WATCH_MODE=0
# Env-overridable like PACMAN_BIN etc above, so a test can force a tiny allocation.
: "${LOAD_FLOOR_MB:=800}"     # never push MemAvailable below this
: "${LOAD_MIN_FREE_MB:=1500}" # refuse to start --with-load below this much available

HOG_FILE=""
LOAD_PID=""
PACMAN_PID=""
STALLS=0
RUN_INDEX=0
LAST_ELAPSED=0

cleanup() {
	local rc=$?
	stop_load
	if [[ -n "$PACMAN_PID" ]] && kill -0 "$PACMAN_PID" 2>/dev/null; then
		echo "Cleaning up: killing in-flight pacman ($PACMAN_PID)" >&2
		kill_tree "$PACMAN_PID"
	fi
	exit "$rc"
}

trap cleanup EXIT INT TERM

# ----------------------------------------------------------------------------
# Preconditions
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Load generator (tmpfs allocation = real anonymous-ish memory, no extra deps)
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Diagnostics capture
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# The repro loop
# ----------------------------------------------------------------------------

log_size() { stat -c %s "$PACMAN_LOG" 2>/dev/null || echo 0; }

# Run one transaction, watching pacman.log for silence. Sets LAST_ELAPSED and,
# when it hangs, bumps STALLS via capture_stall. Deliberately NOT called in a
# command substitution: both counters and PACMAN_PID (which the EXIT trap needs)
# must live in this shell, not a subshell.
run_one() {
	local pkg_file="$1"
	local run="$2"

	local started
	printf -v started '%(%s)T' -1

	"$PACMAN_BIN" -U --noconfirm "$pkg_file" >/dev/null 2>&1 &
	PACMAN_PID=$!

	local last_size last_change now captured=0
	last_size="$(log_size)"
	printf -v last_change '%(%s)T' -1

	while kill -0 "$PACMAN_PID" 2>/dev/null; do
		sleep 1
		local size
		size="$(log_size)"
		printf -v now '%(%s)T' -1

		if [[ $size != "$last_size" ]]; then
			last_size="$size"
			last_change="$now"
		elif ((captured == 0 && now - last_change >= STALL_TIMEOUT)); then
			capture_stall "$PACMAN_PID" "$run"
			captured=1
		fi

		if ((now - started >= HARD_TIMEOUT)); then
			echo "  !! hard timeout (${HARD_TIMEOUT}s) - killing run $run"
			((captured == 0)) && capture_stall "$PACMAN_PID" "$run"
			kill_tree "$PACMAN_PID"
			break
		fi
	done

	wait "$PACMAN_PID" 2>/dev/null || true
	PACMAN_PID=""

	local ended
	printf -v ended '%(%s)T' -1
	LAST_ELAPSED=$((ended - started))
}

main() {
	validate_requirements

	if ((WATCH_MODE == 1)); then
		mkdir -p "$OUT_DIR"
		watch_forever
	else
		local pkg_file
		pkg_file="$(resolve_package_file)"

		mkdir -p "$OUT_DIR"

		echo "============================================================================"
		echo "pacman hook-stall diagnosis"
		echo "============================================================================"
		echo "  package     : $PACKAGE ($pkg_file)"
		echo "  runs        : $RUNS"
		echo "  stall after : ${STALL_TIMEOUT}s of pacman.log silence"
		echo "  hard timeout: ${HARD_TIMEOUT}s"
		local load_desc="idle"
		((WITH_LOAD == 1)) && load_desc="memory pressure ON"
		echo "  load        : $load_desc"
		echo "  dumps       : $OUT_DIR"
		echo

		start_load

		local durations=()
		while ((RUN_INDEX < RUNS)); do
			RUN_INDEX=$((RUN_INDEX + 1))
			run_one "$pkg_file" "$RUN_INDEX"
			durations+=("$LAST_ELAPSED")
			local marker=""
			((LAST_ELAPSED >= STALL_TIMEOUT)) && marker="   <-- slow"
			printf '  run %2d/%d: %3ds%s\n' "$RUN_INDEX" "$RUNS" "$LAST_ELAPSED" "$marker"
		done

		stop_load

		print_summary durations
	fi
}

# Escalate BEFORE parsing: after the parse loop "$@" has been shifted away, so
# re-exec'ing under sudo there would silently drop every flag.
require_root "$@"

# Parse arguments
while [[ $# -gt 0 ]]; do
	case $1 in
	-n | --runs)
		RUNS="$2"
		shift 2
		;;
	-p | --package)
		PACKAGE="$2"
		shift 2
		;;
	-t | --timeout)
		STALL_TIMEOUT="$2"
		shift 2
		;;
	--hard-timeout)
		HARD_TIMEOUT="$2"
		shift 2
		;;
	--with-load)
		WITH_LOAD=1
		shift
		;;
	--watch)
		WATCH_MODE=1
		shift
		;;
	-o | --out)
		OUT_DIR="$2"
		shift 2
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
