#!/bin/bash
# Shutdown timer monitor script
# Watches the day-specific-shutdown timer and re-enables it if disabled
# This file is installed by setup_midnight_shutdown.sh

set -euo pipefail

LOG_FILE="/var/log/shutdown-timer-monitor.log"
TIMER_NAME="day-specific-shutdown.timer"
SERVICE_NAME="day-specific-shutdown.service"
CHECK_INTERVAL=30

# Log with timestamp (shutdown-timer-monitor specific)
log_message() {
  printf '%s [shutdown-monitor] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" | tee -a "$LOG_FILE" >&2
}

# Function to check if timer needs to be re-enabled
timer_needs_restoration() {
  # Check if timer is enabled
  if ! systemctl is-enabled "$TIMER_NAME" &> /dev/null; then
    log_message "Timer $TIMER_NAME is not enabled"
    return 0
  fi

  # Check if timer is active
  if ! systemctl is-active "$TIMER_NAME" &> /dev/null; then
    log_message "Timer $TIMER_NAME is not active"
    return 0
  fi

  # Check if timer unit file exists
  if [[ ! -f "/etc/systemd/system/$TIMER_NAME" ]]; then
    log_message "Timer unit file missing: /etc/systemd/system/$TIMER_NAME"
    return 0
  fi

  # Check if service unit file exists
  if [[ ! -f "/etc/systemd/system/$SERVICE_NAME" ]]; then
    log_message "Service unit file missing: /etc/systemd/system/$SERVICE_NAME"
    return 0
  fi

  # Check if check script exists
  if [[ ! -f "/usr/local/bin/day-specific-shutdown-check.sh" ]]; then
    log_message "Check script missing: /usr/local/bin/day-specific-shutdown-check.sh"
    return 0
  fi

  return 1 # Timer is properly configured
}

# Function to restore timer
restore_timer() {
  log_message "Shutdown timer tampering detected - initiating restoration"

  # Reload systemd daemon in case unit files were modified
  systemctl daemon-reload

  # Re-enable timer if disabled
  if ! systemctl is-enabled "$TIMER_NAME" &> /dev/null; then
    log_message "Re-enabling $TIMER_NAME"
    systemctl enable "$TIMER_NAME" 2> /dev/null || true
  fi

  # Re-start timer if not active
  if ! systemctl is-active "$TIMER_NAME" &> /dev/null; then
    log_message "Re-starting $TIMER_NAME"
    systemctl start "$TIMER_NAME" 2> /dev/null || true
  fi

  # Verify restoration
  if systemctl is-active "$TIMER_NAME" &> /dev/null; then
    log_message "Timer restoration completed successfully"
  else
    log_message "WARNING: Timer restoration may have failed"
  fi
}

# Function to monitor timer with systemd events
monitor_with_dbus() {
  log_message "Starting shutdown timer monitoring with D-Bus events"

  # Use busctl to monitor systemd unit changes
  # Fall back to polling if this fails
  if command -v busctl &> /dev/null; then
    # Monitor for unit state changes
    busctl monitor --system org.freedesktop.systemd1 2> /dev/null |
      while read -r line; do
        # Check if the line mentions our timer
        if echo "$line" | grep -q "$TIMER_NAME\|$SERVICE_NAME"; then
          log_message "Systemd event detected for shutdown timer"
          sleep 2
          if timer_needs_restoration; then
            restore_timer
          fi
        fi
      done
  else
    log_message "busctl not available, falling back to polling"
    monitor_with_polling
  fi
}

# Function to monitor with polling (primary method for reliability)
monitor_with_polling() {
  log_message "Starting shutdown timer monitoring with polling (interval: ${CHECK_INTERVAL}s)"

  while true; do
    if timer_needs_restoration; then
      restore_timer
    fi
    sleep "$CHECK_INTERVAL"
  done
}

# Main execution
log_message "=== Shutdown Timer Monitor Started ==="
log_message "Monitoring timer: $TIMER_NAME"
log_message "Monitoring service: $SERVICE_NAME"

# Initial check
if timer_needs_restoration; then
  log_message "Initial check: Timer needs restoration"
  restore_timer
else
  log_message "Initial check: Timer is properly configured"
fi

# Use polling for reliability (D-Bus monitoring can miss events)
monitor_with_polling
