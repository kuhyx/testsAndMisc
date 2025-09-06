#!/bin/bash
# Script to set up periodic execution of pacman wrapper and hosts file installation
# Executes every hour and on system startup
# Handles sudo privileges automatically

set -e  # Exit on any error

# Default to non-interactive mode
INTERACTIVE_MODE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--interactive)
            INTERACTIVE_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -i, --interactive    Enable interactive prompts (default: auto-yes)"
            echo "  -h, --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Function to check and request sudo privileges
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script requires sudo privileges to create systemd services and timers."
        echo "Requesting sudo access..."
        exec sudo "$0" "$@"
    fi
}

# Check for sudo privileges after argument parsing
check_sudo "$@"

echo "Periodic System Setup - Pacman Wrapper & Hosts File"
echo "==================================================="
echo "Current Date: $(date)"
echo "User: $USER"
echo "Original user: ${SUDO_USER:-$USER}"
if [[ "$INTERACTIVE_MODE" == "true" ]]; then
    echo "Mode: Interactive (prompts enabled)"
else
    echo "Mode: Automatic (auto-yes, use --interactive for prompts)"
fi

# Get the directory where this script is located
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
CONFIG_DIR="$(dirname "$SCRIPT_DIR")"

# Define paths
PACMAN_WRAPPER_SCRIPT="$CONFIG_DIR/scripts/pacman_wrapper.sh"
PACMAN_WRAPPER_INSTALL="$CONFIG_DIR/scripts/install_pacman_wrapper.sh"
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
    
    if [[ ! -f "$PACMAN_WRAPPER_SCRIPT" ]]; then
        missing_files+=("$PACMAN_WRAPPER_SCRIPT")
    fi
    
    if [[ ! -f "$PACMAN_WRAPPER_INSTALL" ]]; then
        missing_files+=("$PACMAN_WRAPPER_INSTALL")
    fi
    
    if [[ ! -f "$HOSTS_INSTALL_SCRIPT" ]]; then
        missing_files+=("$HOSTS_INSTALL_SCRIPT")
    fi
    
    # Check template files as well
    for tmpl in \
        "$TEMPLATE_MAINT_SCRIPT" \
        "$TEMPLATE_HOSTS_MONITOR" \
        "$TEMPLATE_SVC_MAINT" \
        "$TEMPLATE_TIMER" \
        "$TEMPLATE_STARTUP" \
        "$TEMPLATE_HOSTS_SVC" \
        "$TEMPLATE_LOGROTATE"; do
        if [[ ! -f "$tmpl" ]]; then
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
        "$TEMPLATE_MAINT_SCRIPT" > "$exec_script"

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
        "$TEMPLATE_HOSTS_MONITOR" > "$monitor_script"
    chmod +x "$monitor_script"
    echo "✓ Installed hosts monitor script from template: $monitor_script"

    # Install the systemd service from template
    install -m 0644 "$TEMPLATE_HOSTS_SVC" "$monitor_service"
    echo "✓ Installed hosts monitor service from template: $monitor_service"
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
    
    if [[ "$INTERACTIVE_MODE" == "true" ]]; then
        echo "Would you like to run the system maintenance now to test the setup?"
        read -p "Run initial execution? (y/N): " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            run_initial=false
        fi
    else
        echo "Auto-running initial execution to test the setup (use --interactive to prompt)"
    fi
    
    if [[ "$run_initial" == "true" ]]; then
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
