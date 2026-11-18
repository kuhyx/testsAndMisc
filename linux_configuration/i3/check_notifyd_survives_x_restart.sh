#!/bin/bash
# Check: a D-Bus-activated xfce4-notifyd survives an X server that is still
# coming up (night lockdown / lightdm restart). Never touches the live X: the
# user manager's DISPLAY is pointed at a private Xvfb that starts 3 s late,
# and the original environment and notifier are restored on exit.
# Exit 0 = notify-send worked; non-zero = the 2026-11-18 failure reproduced.
set -euo pipefail

readonly TEST_DISPLAY=":98"
readonly UNIT="xfce4-notifyd.service"
orig_display="$(systemctl --user show-environment | sed -n 's/^DISPLAY=//p')"
orig_xauth="$(systemctl --user show-environment | sed -n 's/^XAUTHORITY=//p')"
xvfb_pid=""

cleanup() {
	if [[ -n "$xvfb_pid" ]]; then kill "$xvfb_pid" 2>/dev/null || true; fi
	systemctl --user stop "$UNIT" 2>/dev/null || true
	systemctl --user reset-failed "$UNIT" 2>/dev/null || true
	if [[ -n "$orig_display" ]]; then systemctl --user set-environment "DISPLAY=$orig_display"; fi
	if [[ -n "$orig_xauth" ]]; then systemctl --user set-environment "XAUTHORITY=$orig_xauth"; fi
	# Bring the live notifier back (starting it shows no toast).
	systemctl --user start "$UNIT" || echo "WARN: live $UNIT did not restart" >&2
}
trap cleanup EXIT

[[ ! -e /tmp/.X11-unix/X98 ]] || {
	echo "X98 already in use" >&2
	exit 2
}
systemctl --user stop "$UNIT" 2>/dev/null || true
systemctl --user reset-failed "$UNIT" 2>/dev/null || true
systemctl --user set-environment "DISPLAY=$TEST_DISPLAY"
systemctl --user unset-environment XAUTHORITY

# X "restarts" 3 s after the notification request.
(sleep 3 && exec Xvfb "$TEST_DISPLAY" -nolisten tcp -screen 0 640x480x24) >/dev/null 2>&1 &
xvfb_pid=$!

# The summary is the display name: the toast only ever lands on the private Xvfb.
systemd-run --user --wait --collect --quiet notify-send -t 1 -- "$TEST_DISPLAY"
echo "OK: notify-send succeeded while X came up late"
