#!/bin/bash
set -euo pipefail

LOG_DIR="$HOME/.local/share/gpu-log"
ERR_LOG="$LOG_DIR/pmon-errors.log"
mkdir -p "$LOG_DIR"

if ! command -v nvidia-smi >/dev/null 2>&1; then
	echo "nvidia-pmon-logger: nvidia-smi not found" >&2
	exit 1
fi

# Wake every 60s to (a) check that the pmon child is still alive and (b) rotate
# the log on day-rollover. This used to spin in a `read -r -t 20` loop, but
# under systemd stdin is /dev/null, so `read` returned instantly on EOF. That
# turned the loop into a hot fork-storm calling `date +%Y%m%d` thousands of
# times per second (~22% of one core, ~122 CPU-hours/day).
#
# Use the bash printf %(...)T builtin (zero forks) for the date check, and a
# real sleep (one fork/min, ~1440/day — negligible) for the wait.

while true; do
	printf -v day '%(%Y%m%d)T' -1
	out_file="$LOG_DIR/pmon-${day}.log"

	nvidia-smi pmon -d 10 -o DT >>"$out_file" 2>>"$ERR_LOG" &
	pmon_pid=$!

	while kill -0 "$pmon_pid" >/dev/null 2>&1; do
		printf -v today '%(%Y%m%d)T' -1
		if [[ $today != "$day" ]]; then
			kill "$pmon_pid" >/dev/null 2>&1 || true
			wait "$pmon_pid" 2>/dev/null || true
			break
		fi
		sleep 60
	done
done
