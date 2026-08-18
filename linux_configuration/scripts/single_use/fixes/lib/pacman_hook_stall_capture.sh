#!/bin/bash
# Stall diagnostics capture for diagnose_pacman_hook_stall.sh.
# Sourced, not executed; inherits the caller's strict mode and globals.

# Print every descendant PID of $1, including $1 itself.
descendant_pids() {
	local root="$1"
	local pids=("$root")
	local i=0
	while ((i < ${#pids[@]})); do
		local parent="${pids[i]}"
		local child
		# Explicit fd, not `done < <(...)`: kcov's xtrace-based line
		# instrumentation never emits a trace event for a `done <redirect>`
		# line, leaving it permanently "uncovered". Can't become a pipe
		# instead (`... | while read ...`) -- that runs the loop body in a
		# subshell, so `pids+=("$child")` would never survive back into
		# this function and the walk would silently stop at the root.
		exec 9< <(ps -o pid= --ppid "$parent" 2>/dev/null | tr -d ' ')
		while read -r child <&9; do
			[[ -n "$child" ]] && pids+=("$child")
		done
		exec 9<&-
		i=$((i + 1))
	done
	printf '%s\n' "${pids[@]}"
}

kill_tree() {
	local root="$1"
	local pid
	# A pipe (not `done < <(...)`) is safe here: the loop body only calls
	# kill, so running it in a subshell (which a pipe implies) changes
	# nothing observable -- unlike descendant_pids above.
	descendant_pids "$root" | tac | while read -r pid; do
		kill -9 "$pid" 2>/dev/null || true
	done
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
	# Pipes, not a done-with-redirect loop or a redirected group command:
	# kcov's xtrace-based line instrumentation never emits a trace event for
	# the loop-closing or group-closing line when it carries a trailing
	# redirect, leaving it permanently "uncovered". Safe to pipe here --
	# unlike descendant_pids, nothing in this loop body needs to survive
	# outside a subshell.
	descendant_pids "$root_pid" | while read -r pid; do
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
		} 2>&1 | cat >>"$dir/procs.txt"
	done

	cp /proc/meminfo "$dir/meminfo.txt" 2>/dev/null || true
	{
		echo "--- pressure/memory ---"
		cat /proc/pressure/memory 2>/dev/null || true
		echo "--- pressure/io ---"
		cat /proc/pressure/io 2>/dev/null || true
		echo "--- pressure/cpu ---"
		cat /proc/pressure/cpu 2>/dev/null || true
	} 2>&1 | cat >"$dir/pressure.txt"

	journalctl -k -n 50 --no-pager >"$dir/dmesg-tail.txt" 2>&1 || true
	tail -30 "$PACMAN_LOG" >"$dir/pacman-log-tail.txt" 2>&1 || true

	STALLS=$((STALLS + 1))
}
