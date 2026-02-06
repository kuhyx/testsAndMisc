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
#   --watch-controller    -> Treat game controller (e.g., Xbox) input as user activity to keep session awake
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
		--watch-controller  Watch game controllers and generate activity to keep the session awake
		-h, --help          Show this help and exit

What this does:
	- X11: xset -dpms; xset s off; xset s noblank
	- GNOME: disable idle-delay and lock, power idle to 'nothing'
	- KDE: disable auto-lock via kscreenlockerrc (best-effort), plus X11 DPMS via xset
	- Sway: kill swayidle if running
	- TTY: setterm -blank 0 -powersave off -powerdown 0
		- Optional: systemd-logind IdleAction=ignore
		- Optional: watch controller input and reset idle timers
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

reset_idle_activity() {
  # Trigger activity hints depending on environment
  if [[ -n ${DISPLAY:-} ]]; then
    if has_cmd xset; then
      xset s reset || true
      xset -dpms || true
      xset s off || true
      xset s noblank || true
    fi
    if has_cmd xdotool; then
      # No-op mousemove to generate X11 activity without visible movement
      xdotool mousemove_relative -- 0 0 2> /dev/null || true
    fi
  fi
}

watch_js_device() {
  local dev="$1"
  log "Watching controller device: $dev"
  while :; do
    if [[ ! -e $dev ]]; then
      warn "Device disappeared: $dev"
      break
    fi
    # Joystick API event size is 8 bytes; block until an event arrives
    if dd if="$dev" bs=8 count=1 status=none of=/dev/null; then
      reset_idle_activity
      # Debounce bursts of events
      sleep 0.3
    else
      # On read error (e.g., permission), backoff
      sleep 1
    fi
  done
}

start_controller_watchers() {
  # Attempt to watch all /dev/input/js* devices; rescan periodically for new ones
  declare -A pids

  # Initial permission check
  local any_js=false any_readable=false
  for dev in /dev/input/js*; do
    [[ -e $dev ]] || continue
    any_js=true
    if [[ -r $dev ]]; then any_readable=true; fi
  done
  if [[ $any_js == true && $any_readable == false ]]; then
    warn "No read permission to /dev/input/js*; add your user to the 'input' group or create udev rules."
  fi

  while :; do
    local found_any=false
    for dev in /dev/input/js*; do
      [[ -e $dev ]] || continue
      found_any=true
      if [[ -z ${pids[$dev]:-} ]] || ! kill -0 "${pids[$dev]}" 2> /dev/null; then
        # Start a watcher for this device in background
        watch_js_device "$dev" &
        pids[$dev]=$!
      fi
    done
    if [[ $found_any == false ]]; then
      # No joystick devices; quiet rescan
      sleep 5
    else
      # Rescan less frequently when active
      sleep 2
    fi
  done
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
    log "Controller activity watcher enabled"
    # Keep the script alive to watch controllers
    start_controller_watchers &
    watcher_pid=$!
    log "Watcher PID: $watcher_pid"
    # Wait indefinitely and forward termination
    trap 'log "Stopping controller watcher"; kill "$watcher_pid" 2>/dev/null || true; exit 0' INT TERM
    wait "$watcher_pid"
  else
    log "Done. The screen should no longer blank, lock, or power down automatically."
  fi
}

main "$@"
