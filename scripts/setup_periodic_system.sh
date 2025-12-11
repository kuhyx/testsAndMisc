#!/bin/bash
# Script to set up periodic execution of pacman wrapper and hosts file installation
# Executes every hour and on system startup
# Handles sudo privileges automatically

set -e # Exit on any error

# Source common library for shared functions
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

# Initialize setup script (parse args, require root, print header)
init_setup_script "Periodic System Setup - Pacman Wrapper & Hosts File" "$@"

# Get the directory where this script is located
CONFIG_DIR="$(dirname "$SCRIPT_DIR")"

# Define paths
PACMAN_WRAPPER_SCRIPT="$CONFIG_DIR/scripts/digital_wellbeing/pacman/pacman_wrapper.sh"
PACMAN_WRAPPER_INSTALL="$CONFIG_DIR/scripts/digital_wellbeing/pacman/install_pacman_wrapper.sh"
HOSTS_INSTALL_SCRIPT="$CONFIG_DIR/hosts/install.sh"

echo ""
echo "Configuration directory: $CONFIG_DIR"
echo "Pacman wrapper script: $PACMAN_WRAPPER_SCRIPT"
echo "Pacman wrapper installer: $PACMAN_WRAPPER_INSTALL"
echo "Hosts install script: $HOSTS_INSTALL_SCRIPT"

# Templates directory (version-controlled files)
TEMPLATES_BASE="$CONFIG_DIR/scripts/system-maintenance"
BIN_TEMPLATES="$TEMPLATES_BASE/bin"
SYSTEMD_TEMPLATES="$TEMPLATES_BASE/systemd"
LOGROTATE_TEMPLATES="$TEMPLATES_BASE/logrotate"

# Template files
TEMPLATE_MAINT_SCRIPT="$BIN_TEMPLATES/periodic-system-maintenance.sh"
TEMPLATE_HOSTS_MONITOR="$BIN_TEMPLATES/hosts-file-monitor.sh"
TEMPLATE_BROWSER_WRAPPER="$BIN_TEMPLATES/browser-preexec-wrapper.sh"
TEMPLATE_SVC_MAINT="$SYSTEMD_TEMPLATES/periodic-system-maintenance.service"
TEMPLATE_TIMER="$SYSTEMD_TEMPLATES/periodic-system-maintenance.timer"
TEMPLATE_STARTUP="$SYSTEMD_TEMPLATES/periodic-system-startup.service"
TEMPLATE_HOSTS_SVC="$SYSTEMD_TEMPLATES/hosts-file-monitor.service"
TEMPLATE_LOGROTATE="$LOGROTATE_TEMPLATES/periodic-system-maintenance"

# Function to verify required files exist
verify_files() {
	echo ""
	echo "1. Verifying Required Files..."
	echo "=============================="

	local missing_files=()

	if [[ ! -f $PACMAN_WRAPPER_SCRIPT ]]; then
		missing_files+=("$PACMAN_WRAPPER_SCRIPT")
	fi

	if [[ ! -f $PACMAN_WRAPPER_INSTALL ]]; then
		missing_files+=("$PACMAN_WRAPPER_INSTALL")
	fi

	if [[ ! -f $HOSTS_INSTALL_SCRIPT ]]; then
		missing_files+=("$HOSTS_INSTALL_SCRIPT")
	fi

	# Check template files as well
	for tmpl in \
		"$TEMPLATE_MAINT_SCRIPT" \
		"$TEMPLATE_HOSTS_MONITOR" \
		"$TEMPLATE_BROWSER_WRAPPER" \
		"$TEMPLATE_SVC_MAINT" \
		"$TEMPLATE_TIMER" \
		"$TEMPLATE_STARTUP" \
		"$TEMPLATE_HOSTS_SVC" \
		"$TEMPLATE_LOGROTATE"; do
		if [[ ! -f $tmpl ]]; then
			missing_files+=("$tmpl")
		fi
	done

	if [[ ${#missing_files[@]} -gt 0 ]]; then
		echo "Error: The following required files are missing:"
		for file in "${missing_files[@]}"; do
			echo "  - $file"
		done
		exit 1
	fi

	echo "✓ All required files found"
}

# Function to create the combined execution script
create_execution_script() {
	echo ""
	echo "2. Creating Combined Execution Script..."
	echo "======================================="

	local exec_script="/usr/local/bin/periodic-system-maintenance.sh"

	# Install from template with path substitutions
	sed \
		-e "s|__PACMAN_WRAPPER_INSTALL__|$PACMAN_WRAPPER_INSTALL|g" \
		-e "s|__HOSTS_INSTALL_SCRIPT__|$HOSTS_INSTALL_SCRIPT|g" \
		"$TEMPLATE_MAINT_SCRIPT" >"$exec_script"

	chmod +x "$exec_script"
	echo "✓ Installed execution script from template: $exec_script"
}

# Function to create systemd service
create_systemd_service() {
	echo ""
	echo "3. Creating Systemd Service..."
	echo "============================="

	local service_file="/etc/systemd/system/periodic-system-maintenance.service"
	install -m 0644 "$TEMPLATE_SVC_MAINT" "$service_file"
	echo "✓ Installed systemd service from template: $service_file"
}

# Function to create systemd timer for hourly execution
create_systemd_timer() {
	echo ""
	echo "4. Creating Systemd Timer..."
	echo "============================"

	local timer_file="/etc/systemd/system/periodic-system-maintenance.timer"
	install -m 0644 "$TEMPLATE_TIMER" "$timer_file"
	echo "✓ Installed systemd timer from template: $timer_file"
}

# Function to create startup service (additional to timer)
create_startup_service() {
	echo ""
	echo "5. Creating Startup Service..."
	echo "=============================="

	local startup_service="/etc/systemd/system/periodic-system-startup.service"
	install -m 0644 "$TEMPLATE_STARTUP" "$startup_service"
	echo "✓ Installed startup service from template: $startup_service"
}

# Function to create hosts file monitor service
create_hosts_monitor_service() {
	echo ""
	echo "6. Creating Hosts File Monitor Service..."
	echo "========================================"

	local monitor_script="/usr/local/bin/hosts-file-monitor.sh"
	local monitor_service="/etc/systemd/system/hosts-file-monitor.service"

	# Install the monitor script from template with substitution
	sed -e "s|__HOSTS_INSTALL_SCRIPT__|$HOSTS_INSTALL_SCRIPT|g" \
		"$TEMPLATE_HOSTS_MONITOR" >"$monitor_script"
	chmod +x "$monitor_script"
	echo "✓ Installed hosts monitor script from template: $monitor_script"

	# Install the systemd service from template
	install -m 0644 "$TEMPLATE_HOSTS_SVC" "$monitor_service"
	echo "✓ Installed hosts monitor service from template: $monitor_service"
}

# Function to install browser pre-exec wrapper and wire common browser names
install_browser_preexec_wrapper() {
	echo ""
	echo "6.1 Installing Browser Pre-Exec Wrapper..."
	echo "========================================="

	local wrapper="/usr/local/bin/browser-preexec-wrapper"
	sed -e "s|__HOSTS_INSTALL_SCRIPT__|$HOSTS_INSTALL_SCRIPT|g" \
		"$TEMPLATE_BROWSER_WRAPPER" >"$wrapper"
	chmod +x "$wrapper"
	echo "✓ Installed wrapper: $wrapper"

	# Allow passwordless execution of hosts installer for root-only actions
	local sudoers_file="/etc/sudoers.d/hosts-install-no-passwd"
	if command -v visudo >/dev/null 2>&1; then
		echo "${SUDO_USER:-$USER} ALL=(ALL) NOPASSWD: $HOSTS_INSTALL_SCRIPT" >"$sudoers_file"
		chmod 440 "$sudoers_file"
		# Validate syntax
		visudo -c >/dev/null || echo "Warning: sudoers validation returned non-zero"
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

	# Show timer status
	echo ""
	echo "Timer Status:"
	systemctl status periodic-system-maintenance.timer --no-pager -l

	echo ""
	echo "Hosts Monitor Status:"
	systemctl status hosts-file-monitor.service --no-pager -l

	echo ""
	echo "Next scheduled runs:"
	systemctl list-timers periodic-system-maintenance.timer --no-pager
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
verify_files
create_execution_script
create_systemd_service
create_systemd_timer
create_startup_service
create_hosts_monitor_service
install_browser_preexec_wrapper
enable_services
create_log_rotation
run_initial_execution

echo ""
echo "=========================================="
echo "Periodic System Setup Complete"
echo "=========================================="
echo "Summary:"
echo "✓ Execution script created: /usr/local/bin/periodic-system-maintenance.sh"
echo "✓ Systemd service created and enabled: periodic-system-maintenance.service"
echo "✓ Systemd timer created and enabled: periodic-system-maintenance.timer"
echo "✓ Startup service created and enabled: periodic-system-startup.service"
echo "✓ Hosts file monitor script and service created and enabled"
echo "✓ Log rotation configured: /etc/logrotate.d/periodic-system-maintenance"
echo ""
echo "The system will now:"
echo "• Run maintenance every hour"
echo "• Run maintenance 5 minutes after system startup"
echo "• Monitor hosts file for changes and restore if needed"
echo "• Log all activities to /var/log/periodic-system-maintenance.log and /var/log/hosts-file-monitor.log"
echo ""
echo "To check status:"
echo "  systemctl status periodic-system-maintenance.timer"
echo "  systemctl list-timers periodic-system-maintenance.timer"
echo "  systemctl status hosts-file-monitor.service"
echo ""
echo "To view logs:"
echo "  tail -f /var/log/periodic-system-maintenance.log"
echo "  journalctl -u periodic-system-maintenance.service -f"
echo "  tail -f /var/log/hosts-file-monitor.log"
echo "  journalctl -u hosts-file-monitor.service -f"
echo ""
echo "To disable (if needed):"
echo "  sudo systemctl disable periodic-system-maintenance.timer"
echo "  sudo systemctl disable periodic-system-startup.service"
echo "  sudo systemctl disable hosts-file-monitor.service"
