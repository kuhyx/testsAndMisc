#!/bin/bash
# Idle-inhibit process and the controller-connection watchers.
#
# Sourced by turn_off_auto_idle_screen_shutdown.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

start_idle_inhibit() {
  # Hold one systemd idle inhibitor for the whole time a controller is
  # connected. This replaces the previous per-event fork storm (4 xset + an
  # xdotool + a dd read + a sleep on *every* joystick event, ~21 forks/s while
  # gaming): a single long-lived process keeps logind from treating the session
  # as idle (so it won't auto-suspend or lock), while X11 blanking stays off
  # thanks to the one-shot disable_x11_idle above. Idempotent — a live inhibitor
  # is reused.
  if [[ -n $inhibit_pid ]] && kill -0 "$inhibit_pid" 2> /dev/null; then
    return 0
  fi
  # NOTE: --what=idle only (NOT idle:sleep). An idle inhibitor already stops
  # logind's idle-triggered auto-suspend/lock — which is all gaming needs — but
  # a *sleep* inhibitor would also block *deliberate* suspend/hibernate, e.g.
  # the scheduled digital-wellbeing day-specific-shutdown hibernate. Blocking
  # sleep here once silently kept the PC running past every shutdown window.
  systemd-inhibit --what=idle --who="idle-off" \
    --why="game controller connected" sleep infinity &
  inhibit_pid=$!
  log "Holding idle inhibitor (pid ${inhibit_pid}) while a controller is connected"
}

stop_idle_inhibit() {
  if [[ -z $inhibit_pid ]]; then
    return 0
  fi
  kill "$inhibit_pid" 2> /dev/null || true
  wait "$inhibit_pid" 2> /dev/null || true
  inhibit_pid=""
  log "Released idle inhibitor; normal idle behaviour resumes"
}

controller_connected() {
  # Pure-bash glob check — zero forks. True if any /dev/input/js* node exists.
  local dev
  for dev in /dev/input/js*; do
    [[ -e $dev ]] && return 0
  done
  return 1
}

sync_inhibit_to_controllers() {
  # Hold the inhibitor exactly when a controller is present.
  if controller_connected; then
    start_idle_inhibit
  else
    stop_idle_inhibit
  fi
}

start_controller_watchers() {
  # Event-driven and fork-free in the hot path: react only to input-device
  # add/remove (rare udev events), never to individual joystick *input* events,
  # and hold a single systemd-inhibit lock while a controller is present.
  if ! has_cmd systemd-inhibit; then
    warn "systemd-inhibit not found; cannot hold an idle inhibitor"
    return 0
  fi
  # EXIT covers every termination path (including a SIGTERM that interrupts the
  # blocking read below); INT/TERM additionally give a clean exit status.
  trap 'stop_idle_inhibit' EXIT
  trap 'exit 0' INT TERM

  sync_inhibit_to_controllers # apply current state once at startup

  if has_cmd udevadm; then
    log "Watching controller hotplug via udev (no polling)"
    # Process substitution (not a pipe) keeps the loop in this shell so
    # inhibit_pid persists across events.
    while read -r _; do
      sync_inhibit_to_controllers
    done < <(udevadm monitor --udev --subsystem-match=input 2> /dev/null)
  else
    # Fallback when udevadm is unavailable: a low-frequency presence poll. One
    # sleep per 30 s cycle (~0.03 forks/s) versus the old ~21 forks/s.
    warn "udevadm not found; falling back to a 30 s presence poll"
    while :; do
      sync_inhibit_to_controllers
      sleep 30
    done
  fi
}

persist_with_systemd_logind() {
  # Set IdleAction=ignore in /etc/systemd/logind.conf and restart logind
  # Warning: restarting logind can affect user sessions (e.g., inhibit handling). Use with care.
  # Takes the flag as an argument rather than reading the caller's global, so
  # this file is checkable on its own.
  local persist="${1:-false}"
  if [[ $persist != true ]]; then
    return 0
  fi
  if ! has_cmd sudo; then
    warn "sudo not found; cannot persist systemd-logind setting"
    return 0
  fi
  log "Persisting: setting systemd-logind IdleAction=ignore (requires sudo)"
  sudo sh -c '
		set -e
		conf=/etc/systemd/logind.conf
		if [ ! -f "$conf" ]; then
			touch "$conf"
		fi
		# Backup once
		[ -f "${conf}.bak" ] || cp -a "$conf" "${conf}.bak"
		# Ensure the key exists and is set to ignore
		if grep -q "^#\?IdleAction=" "$conf"; then
			sed -i "s/^#\?IdleAction=.*/IdleAction=ignore/" "$conf"
		else
			printf "\nIdleAction=ignore\n" >> "$conf"
		fi
	'
  log "Restarting systemd-logind to apply changes (may briefly affect session inhibitors)"
  sudo systemctl restart systemd-logind || warn "Failed to restart systemd-logind"
}
