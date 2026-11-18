#!/bin/bash
# ExecStartPre for xfce4-notifyd.service: hold the start until $DISPLAY
# answers, up to WAIT_FOR_X_SECS (default 15). The notifier is D-Bus
# activated and the systemd --user manager outlives X sessions, so a request
# that lands while X restarts (night lockdown, lightdm) used to fail five
# times at once, hit the start limit and fail the activation. Waiting turns
# that into one start that succeeds as soon as X is back.
set -euo pipefail

readonly deadline=$((SECONDS + ${WAIT_FOR_X_SECS:-15}))
until xset q >/dev/null 2>&1; do
	if ((SECONDS >= deadline)); then
		echo "wait_for_x: DISPLAY=${DISPLAY:-unset} not answering after ${WAIT_FOR_X_SECS:-15}s" >&2
		exit 1
	fi
	sleep 0.25
done
