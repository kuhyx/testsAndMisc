#!/usr/bin/env bash

# Turn off idle detection, screen blanking, DPMS, and auto-lock across common Arch Linux setups.
#
# Supported environments:
# - X11 (xset: DPMS/screensaver/blanking)
# - GNOME (gsettings: idle/lock + power 'nothing')
# - KDE Plasma (best-effort: disable kscreenlocker; X11 DPMS still handled by xset)
# - Sway/Wayland (kill swayidle)
# - Linux console TTYs (setterm)
#
# Optional persistence (requires sudo):
#   --persist-systemd     -> Set IdleAction=ignore in /etc/systemd/logind.conf and restart logind
# Optional activity watcher:
#   --watch-controller    -> Hold a systemd idle inhibitor while a game controller is connected (keeps the session awake, fork-free; does NOT block deliberate suspend/hibernate)
#
# Notes:
# - This script focuses on keeping the screen on and unlocked. Use with care on shared systems.
# - For desktop-specific persistence (GNOME/KDE), settings are applied per-user and should persist.

set -euo pipefail

log() { printf "[idle-off] %s\n" "$*"; }
warn() { printf "[idle-off][WARN] %s\n" "$*" >&2; }
has_cmd() { command -v "$1" > /dev/null 2>&1; }

persist_systemd=false
watch_controller=false
for arg in "${@:-}"; do
  case "$arg" in
    --persist-systemd)
      persist_systemd=true
      ;;
    --watch-controller)
      watch_controller=true
      ;;
    -h | --help)
      cat << EOF
Usage: $(basename "$0") [--persist-systemd] [--watch-controller]

Disables idle detection, screen blanking, and auto-lock for the current session.

Options:
		--persist-systemd   Also set IdleAction=ignore in /etc/systemd/logind.conf (needs sudo)
		--watch-controller  Hold an idle inhibitor while a game controller is connected
		-h, --help          Show this help and exit

What this does:
	- X11: xset -dpms; xset s off; xset s noblank
	- GNOME: disable idle-delay and lock, power idle to 'nothing'
	- KDE: disable auto-lock via kscreenlockerrc (best-effort), plus X11 DPMS via xset
	- Sway: kill swayidle if running
	- TTY: setterm -blank 0 -powersave off -powerdown 0
		- Optional: systemd-logind IdleAction=ignore
		- Optional: hold a systemd idle inhibitor while a controller is connected
EOF
      exit 0
      ;;
  esac
done

disable_x11_idle() {
  if [[ -n ${DISPLAY:-} ]] && has_cmd xset; then
    log "Disabling X11 DPMS/screensaver/blanking via xset"
    xset -dpms || true
    xset s off || true
    xset s noblank || true
  else
    log "X11/xset not detected or DISPLAY not set; skipping xset"
  fi
}

disable_gnome_idle() {
  if has_cmd gsettings; then
    # Detect GNOME by presence of GNOME schemas
    if gsettings list-schemas 2> /dev/null | grep -q '^org\.gnome\.desktop\.session$'; then
      log "Applying GNOME settings to disable idle and lock"
      # No lock on idle
      gsettings set org.gnome.desktop.screensaver lock-enabled false 2> /dev/null || warn "Failed to set GNOME lock-enabled"
      # No idle delay (0 = never)
      gsettings set org.gnome.desktop.session idle-delay 0 2> /dev/null || warn "Failed to set GNOME idle-delay"
      # No automatic suspend on AC or battery
      gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing' 2> /dev/null || true
      gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing' 2> /dev/null || true
      # Optional: ensure screensaver idle-activation-enabled is false (for older setups)
      gsettings set org.gnome.desktop.screensaver idle-activation-enabled false 2> /dev/null || true
    fi
  fi
}

disable_kde_idle() {
  # Best-effort: turn off auto-locker; note: Plasma on Wayland still may rely on compositor-level settings
  if has_cmd kwriteconfig5; then
    log "Disabling KDE Plasma screen auto-lock (kscreenlockerrc)"
    kwriteconfig5 --file kscreenlockerrc --group Daemon --key Autolock false 2> /dev/null || true
    kwriteconfig5 --file kscreenlockerrc --group Daemon --key LockOnResume false 2> /dev/null || true
    kwriteconfig5 --file kscreenlockerrc --group Daemon --key Timeout 0 2> /dev/null || true
  fi
}

disable_sway_idle() {
  # Sway commonly uses swayidle for idle actions; killing it prevents screen blanking/locking
  if pgrep -x sway > /dev/null 2>&1; then
    if pgrep -x swayidle > /dev/null 2>&1; then
      log "Killing swayidle to prevent Wayland idle actions"
      pkill -x swayidle || true
    fi
  fi
}

disable_lock_daemons() {
  # Stop common screen lockers/idle helpers if running
  local daemons=(xss-lock light-locker xscreensaver gnome-screensaver)
  local found=false
  for d in "${daemons[@]}"; do
    if pgrep -x "$d" > /dev/null 2>&1; then
      found=true
      log "Stopping ${d}"
      pkill -x "$d" || true
    fi
  done
  if [[ $found == false ]]; then
    log "No known lock daemons running"
  fi
}

disable_tty_idle() {
  if has_cmd setterm; then
    log "Disabling TTY blanking and powersave"
    # Apply to the current TTY; also attempt to broadcast to common TTYs
    setterm -blank 0 -powersave off -powerdown 0 || true
    for tty in /dev/tty{1..12}; do
      [[ -e $tty ]] || continue
      setterm -blank 0 -powersave off -powerdown 0 < "$tty" > /dev/null 2>&1 || true
    done
  fi
}

# PID of the single long-lived idle inhibitor we hold while a controller
# is connected. Empty when no inhibitor is active.
inhibit_pid=""

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
  if [[ $persist_systemd != true ]]; then
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

main() {
  log "Starting idle/lock disablement"

  # Environment-aware steps
  disable_x11_idle
  disable_gnome_idle
  disable_kde_idle
  disable_sway_idle

  # Generic steps
  disable_lock_daemons
  disable_tty_idle

  # Optional persistence
  persist_with_systemd_logind

  if [[ $watch_controller == true ]]; then
    log "Controller activity watcher enabled (idle-inhibitor mode)"
    # Blocks until terminated; releases the inhibitor on exit via its own trap.
    start_controller_watchers
  else
    log "Done. The screen should no longer blank, lock, or power down automatically."
  fi
}

main "$@"
