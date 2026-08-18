#!/bin/bash
# Passive watch mode for diagnose_pacman_hook_stall.sh.
# Sourced, not executed; inherits the caller's strict mode and globals.

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
