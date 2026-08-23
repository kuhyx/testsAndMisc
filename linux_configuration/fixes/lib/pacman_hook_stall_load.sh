#!/bin/bash
# Memory-pressure load generator for diagnose_pacman_hook_stall.sh.
# Sourced, not executed; inherits the caller's strict mode and globals.

mem_available_mb() {
	local kb=0 key value rest
	# Explicit fd, not `done </proc/meminfo`: kcov's xtrace-based line
	# instrumentation never emits a trace event for a `done <redirect>`
	# line, so it stays "uncovered" no matter how the loop body is
	# exercised. An explicit fd keeps the redirect on a line of its own
	# that kcov *does* trace.
	exec 9</proc/meminfo
	while read -r key value rest <&9; do
		if [[ $key == "MemAvailable:" ]]; then
			kb="$value"
			break
		fi
	done
	exec 9<&-
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
