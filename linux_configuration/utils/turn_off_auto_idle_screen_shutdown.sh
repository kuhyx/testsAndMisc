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

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
# shellcheck source=lib/idle_inhibit.sh
source "$SCRIPT_DIR/lib/idle_inhibit.sh"

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
  persist_with_systemd_logind "$persist_systemd"

  if [[ $watch_controller == true ]]; then
    # Singleton. i3 re-execs its `exec` lines on `i3-msg restart`, and a second
    # long-lived watcher would sit there holding a redundant inhibitor for the
    # rest of the session. One lock, taken for as long as the watcher lives.
    exec 8> "${XDG_RUNTIME_DIR:-/tmp}/idle-off-watch.lock"
    if ! flock -n 8; then
      log "Controller watcher already running; not starting a second one."
      exit 0
    fi
    log "Controller activity watcher enabled (idle-inhibitor mode)"
    # Blocks until terminated; releases the inhibitor on exit via its own trap.
    start_controller_watchers
  else
    log "Done. The screen should no longer blank, lock, or power down automatically."
  fi
}

main "$@"
