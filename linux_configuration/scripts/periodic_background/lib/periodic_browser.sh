#!/bin/bash
# Browser wrapper install, desktop-entry redirect, auto-update units and
# service enablement for the periodic system setup.
#
# Sourced by setup_periodic_system.sh; split out to keep it under the
# 250-line cap. Sourced rather than run, so it inherits the caller's strict
# mode and the variables defined above the source line.

# Function to install browser pre-exec wrapper and wire common browser names
install_browser_preexec_wrapper() {
  echo ""
  echo "6.1 Installing Browser Pre-Exec Wrapper..."
  echo "========================================="

  local wrapper="/usr/local/bin/browser-preexec-wrapper"
  sed -e "s|__HOSTS_INSTALL_SCRIPT__|$HOSTS_INSTALL_SCRIPT|g" \
    "$TEMPLATE_BROWSER_WRAPPER" > "$wrapper"
  chmod +x "$wrapper"
  echo "✓ Installed wrapper: $wrapper"

  # Allow passwordless execution of hosts installer for root-only actions
  local sudoers_file="/etc/sudoers.d/hosts-install-no-passwd"
  if command -v visudo > /dev/null 2>&1; then
    echo "${SUDO_USER:-$USER} ALL=(ALL) NOPASSWD: $HOSTS_INSTALL_SCRIPT" > "$sudoers_file"
    chmod 440 "$sudoers_file"
    # Validate syntax
    visudo -c > /dev/null || echo "Warning: sudoers validation returned non-zero"
    echo "✓ Sudoers drop-in created: $sudoers_file"
  else
    echo "visudo not found; skipping sudoers drop-in"
  fi

  # Create symlinks for common browser commands to the wrapper in /usr/local/bin
  # This takes precedence over /usr/bin in PATH on most systems.
  local browsers=("thorium-browser" "google-chrome" "google-chrome-stable" "chromium" "brave" "brave-browser" "vivaldi-stable" "firefox")
  for b in "${browsers[@]}"; do
    local link="/usr/local/bin/$b"
    ln -sf "$wrapper" "$link"
  done
  echo "✓ Symlinked wrapper for common browsers in /usr/local/bin"

  redirect_app_mode_desktop_entries
}

# Chromium "app mode" shortcuts (--app-id=...) are auto-generated with a direct
# Exec=/opt/<browser>/<browser> line, bypassing /usr/local/bin entirely. That
# means neither the flags file nor the crash logging applies to them, and it is
# silent: on 2026-08-09 five such Thorium entries were found still launching
# without the --disable-gpu-compositing mitigation added on 2026-07-25.
# Chromium regenerates these files, so this re-runs on every install.
redirect_app_mode_desktop_entries() {
  local target_user="${SUDO_USER:-$USER}"
  local apps_dir
  apps_dir="$(getent passwd "$target_user" | cut -d: -f6)/.local/share/applications"

  [[ -d $apps_dir ]] || return 0

  local rewritten=0 f
  while IFS= read -r -d '' f; do
    if grep -q '^Exec=/opt/' "$f"; then
      # Keep only the BASENAME, whatever the nesting depth:
      #   /opt/thorium-browser/thorium-browser -> /usr/local/bin/thorium-browser
      #   /opt/google/chrome/google-chrome     -> /usr/local/bin/google-chrome
      # The greedy .* up to the last slash is what makes depth irrelevant;
      # matching a single path segment silently mangles the nested case.
      sed -i -E 's|^Exec=/opt/.*/([^/ ]+)|Exec=/usr/local/bin/\1|' "$f"
      rewritten=$((rewritten + 1))
    fi
  done < <(find "$apps_dir" -maxdepth 1 -type f -name '*.desktop' -print0 2> /dev/null)

  if ((rewritten > 0)); then
    chown "$target_user" "$apps_dir"/*.desktop 2> /dev/null || true
    echo "✓ Redirected $rewritten app-mode .desktop entries through the wrapper"
  else
    echo "✓ No app-mode .desktop entries needed redirecting"
  fi
}

# Function to install automatic system update service
install_auto_update() {
  echo ""
  echo "6.2 Installing Automatic System Update..."
  echo "========================================="

  local update_script="/usr/local/bin/auto-system-update.sh"
  local update_service="/etc/systemd/system/auto-system-update.service"
  local update_timer="/etc/systemd/system/auto-system-update.timer"

  # Install script from template with user substitution
  local actual_user="${SUDO_USER:-$USER}"
  sed -e "s|__ACTUAL_USER__|$actual_user|g" \
    "$TEMPLATE_AUTO_UPDATE" > "$update_script"
  chmod +x "$update_script"
  echo "✓ Installed auto-update script: $update_script (user: $actual_user)"

  # Install systemd service and timer from templates
  install -m 0644 "$TEMPLATE_AUTO_UPDATE_SVC" "$update_service"
  echo "✓ Installed auto-update service: $update_service"

  install -m 0644 "$TEMPLATE_AUTO_UPDATE_TIMER" "$update_timer"
  echo "✓ Installed auto-update timer: $update_timer"
}

# Function to enable and start services
enable_services() {
  echo ""
  echo "7. Enabling Services and Timer..."
  echo "================================="

  # Reload systemd daemon
  systemctl daemon-reload
  echo "✓ Systemd daemon reloaded"

  # Enable and start the timer
  systemctl enable periodic-system-maintenance.timer
  systemctl start periodic-system-maintenance.timer
  echo "✓ Timer enabled and started"

  # Enable startup service (but don't start it now)
  systemctl enable periodic-system-startup.service
  echo "✓ Startup service enabled"

  # Enable hosts file monitor service
  systemctl enable hosts-file-monitor.service
  systemctl start hosts-file-monitor.service
  echo "✓ Hosts file monitor service enabled and started"

  # Enable and start auto-update timer
  systemctl enable auto-system-update.timer
  systemctl start auto-system-update.timer
  echo "✓ Auto-update timer enabled and started"

  # Show timer status
  echo ""
  echo "Timer Status:"
  systemctl status periodic-system-maintenance.timer --no-pager -l

  echo ""
  echo "Auto-Update Timer Status:"
  systemctl status auto-system-update.timer --no-pager -l

  echo ""
  echo "Hosts Monitor Status:"
  systemctl status hosts-file-monitor.service --no-pager -l

  echo ""
  echo "Next scheduled runs:"
  systemctl list-timers periodic-system-maintenance.timer auto-system-update.timer --no-pager
}

# Function to create log rotation configuration
create_log_rotation() {
  echo ""
  echo "8. Setting up Log Rotation..."
  echo "============================="

  local logrotate_conf="/etc/logrotate.d/periodic-system-maintenance"
  install -m 0644 "$TEMPLATE_LOGROTATE" "$logrotate_conf"
  echo "✓ Installed log rotation configuration from template: $logrotate_conf"
}

# Function to run initial execution
run_initial_execution() {
  echo ""
  echo "9. Running Initial Execution..."
  echo "==============================="

  local run_initial=true

  if [[ $INTERACTIVE_MODE == "true" ]]; then
    echo "Would you like to run the system maintenance now to test the setup?"
    read -p "Run initial execution? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      run_initial=false
    fi
  else
    echo "Auto-running initial execution to test the setup (use --interactive to prompt)"
  fi

  if [[ $run_initial == "true" ]]; then
    echo "Running initial system maintenance..."
    /usr/local/bin/periodic-system-maintenance.sh
    echo "✓ Initial execution completed"
  else
    echo "Skipping initial execution"
  fi
}

# Main execution
