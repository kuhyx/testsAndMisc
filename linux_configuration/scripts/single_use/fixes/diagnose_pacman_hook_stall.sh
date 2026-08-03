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

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly PACMAN_BIN="/usr/bin/pacman.orig"
readonly PACMAN_LOG="/var/log/pacman.log"
readonly CACHE_DIR="/var/cache/pacman/pkg"

# Defaults
RUNS=40
PACKAGE="base-devel"
STALL_TIMEOUT=20 # seconds with no new pacman.log line => declare a stall
HARD_TIMEOUT=120 # seconds before we give up and kill the stalled transaction
OUT_DIR="/var/log/pacman-hook-stall"
WITH_LOAD=0
WATCH_MODE=0
LOAD_FLOOR_MB=800     # never push MemAvailable below this
LOAD_MIN_FREE_MB=1500 # refuse to start --with-load below this much available

HOG_FILE=""
LOAD_PID=""
PACMAN_PID=""
STALLS=0
RUN_INDEX=0
LAST_ELAPSED=0

usage() {
	cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Drives repeated pacman transactions and captures diagnostics when one stalls
at its first PreTransaction hook.

Options:
  -n, --runs N          Number of transactions to drive (default: $RUNS)
  -p, --package NAME    Package to reinstall from cache (default: $PACKAGE)
  -t, --timeout S       Seconds of pacman.log silence => stall (default: $STALL_TIMEOUT)
      --hard-timeout S  Seconds before killing a stalled run (default: $HARD_TIMEOUT)
      --with-load       Also apply memory pressure (the hypothesis under test).
                        Run this with nothing else going - it deliberately
                        breaks the one-heavy-job-at-a-time rule.
      --watch           Passive mode: drive nothing, just watch pacman.log and
                        dump diagnostics when someone else's transaction stalls
                        on a hook. Intended to run as a systemd service.
  -o, --out DIR         Where to write stall dumps (default: $OUT_DIR)
  -h, --help            Show this help

Exit status: 0 if the loop completed (with or without stalls), non-zero on a
setup failure. The stall count is reported in the summary.
EOF
	exit 0
}

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
	if [[ -e /var/lib/pacman/db.lck ]]; then
		echo "Error: /var/lib/pacman/db.lck exists - another transaction is in" >&2
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

# ----------------------------------------------------------------------------
# Load generator (tmpfs allocation = real anonymous-ish memory, no extra deps)
# ----------------------------------------------------------------------------

mem_available_mb() {
	local kb=0 key value rest
	while read -r key value rest; do
		if [[ $key == "MemAvailable:" ]]; then
			kb="$value"
			break
		fi
	done </proc/meminfo
	printf '%d\n' $((kb / 1024))
}

start_load() {
	((WITH_LOAD == 1)) || return 0

	local avail
	avail="$(mem_available_mb)"
	if ((avail < LOAD_MIN_FREE_MB)); then
		echo "Error: only ${avail} MB available; --with-load needs >= ${LOAD_MIN_FREE_MB} MB" >&2
		echo "Close Chromium / builds first." >&2
		exit 1
	fi

	local target=$((avail - LOAD_FLOOR_MB))
	HOG_FILE="$(mktemp /dev/shm/hook-stall-hog.XXXXXX)"
	echo "Applying memory pressure: allocating ${target} MB (floor ${LOAD_FLOOR_MB} MB available)"
	dd if=/dev/zero of="$HOG_FILE" bs=1M count="$target" status=none 2>/dev/null || true
	echo "MemAvailable now: $(mem_available_mb) MB"
}

stop_load() {
	if [[ -n "$LOAD_PID" ]] && kill -0 "$LOAD_PID" 2>/dev/null; then
		kill "$LOAD_PID" 2>/dev/null || true
	fi
	if [[ -n "$HOG_FILE" && -e "$HOG_FILE" ]]; then
		rm -f "$HOG_FILE"
		HOG_FILE=""
	fi
}

# ----------------------------------------------------------------------------
# Diagnostics capture
# ----------------------------------------------------------------------------

# Print every descendant PID of $1, including $1 itself.
descendant_pids() {
	local root="$1"
	local pids=("$root")
	local i=0
	while ((i < ${#pids[@]})); do
		local parent="${pids[i]}"
		local child
		while read -r child; do
			[[ -n "$child" ]] && pids+=("$child")
		done < <(ps -o pid= --ppid "$parent" 2>/dev/null | tr -d ' ')
		i=$((i + 1))
	done
	printf '%s\n' "${pids[@]}"
}

kill_tree() {
	local root="$1"
	local pid
	while read -r pid; do
		kill -9 "$pid" 2>/dev/null || true
	done < <(descendant_pids "$root" | tac)
}

capture_stall() {
	local root_pid="$1"
	local run="$2"
	local stamp
	printf -v stamp '%(%Y%m%d-%H%M%S)T' -1

	# Classify before capturing. The stall we are hunting leaves pacman.log
	# ending on a hook's "running '...hook'..." line; anything else stalled
	# somewhere unrelated and must not be counted as a reproduction.
	local kind="other"
	if tail -1 "$PACMAN_LOG" 2>/dev/null | grep -q "running '.*\.hook'"; then
		kind="hook"
	fi

	local dir="$OUT_DIR/${stamp}-run${run}-${kind}"
	mkdir -p "$dir"

	echo "  !! STALL ($kind) - capturing diagnostics to $dir"
	tail -1 "$PACMAN_LOG" >"$dir/last-log-line.txt" 2>&1 || true

	ps -eo pid,ppid,stat,wchan:32,etime,args --forest >"$dir/ps-forest.txt" 2>&1 || true

	local pid
	while read -r pid; do
		[[ -d "/proc/$pid" ]] || continue
		{
			echo "=== pid $pid ==="
			echo "--- cmdline ---"
			tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null || true
			echo
			echo "--- wchan ---"
			cat "/proc/$pid/wchan" 2>/dev/null || true
			echo
			echo "--- syscall ---"
			cat "/proc/$pid/syscall" 2>/dev/null || true
			echo "--- stack ---"
			cat "/proc/$pid/stack" 2>/dev/null || echo "(unavailable - needs CONFIG_STACKTRACE)"
			echo "--- status ---"
			grep -E "^(Name|State|Threads|VmRSS|SigBlk|SigIgn|SigCgt)" "/proc/$pid/status" 2>/dev/null || true
			echo "--- smaps_rollup (Pss) ---"
			grep -E "^Pss:" "/proc/$pid/smaps_rollup" 2>/dev/null || true
			echo
		} >>"$dir/procs.txt" 2>&1
	done < <(descendant_pids "$root_pid")

	cp /proc/meminfo "$dir/meminfo.txt" 2>/dev/null || true
	{
		echo "--- pressure/memory ---"
		cat /proc/pressure/memory 2>/dev/null || true
		echo "--- pressure/io ---"
		cat /proc/pressure/io 2>/dev/null || true
		echo "--- pressure/cpu ---"
		cat /proc/pressure/cpu 2>/dev/null || true
	} >"$dir/pressure.txt" 2>&1

	journalctl -k -n 50 --no-pager >"$dir/dmesg-tail.txt" 2>&1 || true
	tail -30 "$PACMAN_LOG" >"$dir/pacman-log-tail.txt" 2>&1 || true

	STALLS=$((STALLS + 1))
}

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

# Passive mode: watch OTHER people's transactions instead of driving our own.
#
# This exists because the active repro loop could not reproduce the stall: 65
# transactions (40 idle + 25 under 2.6 GB of memory pressure) ran clean, against
# a historical rate of 4 in 56. At a uniform 7% the odds of 65 clean runs are
# under 1%, so the trigger is conditional on something a synthetic loop does not
# recreate - which means the evidence has to be captured from a real stall, when
# it next happens, rather than manufactured.
#
# Runs as a systemd service; costs one stat(2) per second and nothing else.
watch_forever() {
	echo "Watching $PACMAN_LOG for hook stalls (>= ${STALL_TIMEOUT}s silent)"
	echo "Dumps: $OUT_DIR"

	local last_size last_change now armed=0 seq=0
	last_size="$(log_size)"
	printf -v last_change '%(%s)T' -1

	while true; do
		sleep 1
		local size
		size="$(log_size)"
		printf -v now '%(%s)T' -1

		if [[ $size != "$last_size" ]]; then
			last_size="$size"
			last_change="$now"
			armed=0
			continue
		fi

		# Silence alone is normal - no transaction is running most of the time.
		# Only a LIVE pacman sitting on a hook line is the signature we want.
		((armed == 1)) && continue
		((now - last_change >= STALL_TIMEOUT)) || continue

		local pacman_pid
		pacman_pid="$(pgrep -x pacman.orig | head -1 || true)"
		[[ -n $pacman_pid ]] || continue

		seq=$((seq + 1))
		capture_stall "$pacman_pid" "watch${seq}"
		logger -t pacman-hook-stall "captured a stalled transaction (pid $pacman_pid)"
		armed=1
	done
}

main() {
	validate_requirements

	if ((WATCH_MODE == 1)); then
		mkdir -p "$OUT_DIR"
		watch_forever
		return
	fi

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

	echo
	echo "============================================================================"
	echo "Summary"
	echo "============================================================================"
	printf '  transactions : %d\n' "$RUNS"
	printf '  stalls       : %d\n' "$STALLS"
	printf '  durations    : %s\n' "${durations[*]}"
	printf '%s\n' "${durations[@]}" | sort -n | awk '
        { d[NR] = $1 }
        END {
            if (NR == 0) exit
            printf "  min/median/max: %ds / %ds / %ds\n", d[1], d[int((NR+1)/2)], d[NR]
        }'
	if ((STALLS > 0)); then
		echo
		echo "  Captured dumps:"
		find "$OUT_DIR" -mindepth 1 -maxdepth 1 -type d -printf '    %p\n' \
			2>/dev/null | sort | tail -"$STALLS"
	fi
	echo "============================================================================"
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
