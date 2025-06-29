#!/bin/bash
# Script to set up periodic execution of pacman wrapper and hosts file installation
# Executes every hour and on system startup
# Handles sudo privileges automatically

set -e  # Exit on any error

# Function to check and request sudo privileges
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script requires sudo privileges to create systemd services and timers."
        echo "Requesting sudo access..."
        exec sudo "$0" "$@"
    fi
}

# Check for sudo privileges first
check_sudo "$@"

echo "Periodic System Setup - Pacman Wrapper & Hosts File"
echo "==================================================="
echo "Current Date: $(date)"
echo "User: $USER"
echo "Original user: ${SUDO_USER:-$USER}"

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
    
    cat > "$exec_script" << EOF
#!/bin/bash
# Periodic system maintenance script
# Installs pacman wrapper and updates hosts file
# Created by setup_periodic_system.sh on $(date)

set -e

LOG_FILE="/var/log/periodic-system-maintenance.log"

# Function to log with timestamp
log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" >> "\$LOG_FILE"
}

# Function to execute with logging
execute_with_log() {
    local script_path="\$1"
    local script_name="\$2"
    
    log_message "Starting \$script_name"
    echo "Executing \$script_name..." >&2
    
    if [[ -f "\$script_path" ]]; then
        if bash "\$script_path" >> "\$LOG_FILE" 2>&1; then
            log_message "\$script_name completed successfully"
            echo "✓ \$script_name completed successfully" >&2
        else
            log_message "\$script_name failed with exit code \$?"
            echo "✗ \$script_name failed" >&2
        fi
    else
        log_message "\$script_name not found at \$script_path"
        echo "✗ \$script_name not found at \$script_path" >&2
    fi
}

# Start maintenance
log_message "=== Periodic System Maintenance Started ==="

# Install pacman wrapper
execute_with_log "$PACMAN_WRAPPER_INSTALL" "Pacman Wrapper Installation"

# Update hosts file
execute_with_log "$HOSTS_INSTALL_SCRIPT" "Hosts File Update"

log_message "=== Periodic System Maintenance Completed ==="
echo "Periodic system maintenance completed. Check $LOG_FILE for details." >&2
EOF

    chmod +x "$exec_script"
    echo "✓ Created execution script: $exec_script"
}

# Function to create systemd service
create_systemd_service() {
    echo ""
    echo "3. Creating Systemd Service..."
    echo "============================="
    
    local service_file="/etc/systemd/system/periodic-system-maintenance.service"
    
    cat > "$service_file" << EOF
[Unit]
Description=Periodic System Maintenance (Pacman Wrapper & Hosts File)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/periodic-system-maintenance.sh
StandardOutput=journal
StandardError=journal

# Timeout settings
TimeoutStartSec=300
TimeoutStopSec=30

# Restart settings
Restart=no

[Install]
WantedBy=multi-user.target
EOF

    echo "✓ Created systemd service: $service_file"
}

# Function to create systemd timer for hourly execution
create_systemd_timer() {
    echo ""
    echo "4. Creating Systemd Timer..."
    echo "============================"
    
    local timer_file="/etc/systemd/system/periodic-system-maintenance.timer"
    
    cat > "$timer_file" << EOF
[Unit]
Description=Run Periodic System Maintenance every hour
Requires=periodic-system-maintenance.service

[Timer]
# Run every hour
OnCalendar=hourly
# Run on system startup (5 minutes after boot)
OnBootSec=5min
# Add randomization to prevent all systems from running simultaneously
RandomizedDelaySec=300
# Ensure timer persists across reboots
Persistent=true

[Install]
WantedBy=timers.target
EOF

    echo "✓ Created systemd timer: $timer_file"
}

# Function to create startup service (additional to timer)
create_startup_service() {
    echo ""
    echo "5. Creating Startup Service..."
    echo "=============================="
    
    local startup_service="/etc/systemd/system/periodic-system-startup.service"
    
    cat > "$startup_service" << EOF
[Unit]
Description=System Maintenance on Startup (Pacman Wrapper & Hosts File)
After=network-online.target systemd-resolved.service
Wants=network-online.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/periodic-system-maintenance.sh
StandardOutput=journal
StandardError=journal
RemainAfterExit=yes

# Timeout settings
TimeoutStartSec=300
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

    echo "✓ Created startup service: $startup_service"
}

# Function to enable and start services
enable_services() {
    echo ""
    echo "6. Enabling Services and Timer..."
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
    
    # Show timer status
    echo ""
    echo "Timer Status:"
    systemctl status periodic-system-maintenance.timer --no-pager -l
    
    echo ""
    echo "Next scheduled runs:"
    systemctl list-timers periodic-system-maintenance.timer --no-pager
}

# Function to create log rotation configuration
create_log_rotation() {
    echo ""
    echo "7. Setting up Log Rotation..."
    echo "============================="
    
    local logrotate_conf="/etc/logrotate.d/periodic-system-maintenance"
    
    cat > "$logrotate_conf" << EOF
/var/log/periodic-system-maintenance.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        systemctl reload-or-restart rsyslog > /dev/null 2>&1 || true
    endscript
}
EOF

    echo "✓ Created log rotation configuration: $logrotate_conf"
}

# Function to run initial execution
run_initial_execution() {
    echo ""
    echo "8. Running Initial Execution..."
    echo "==============================="
    
    echo "Would you like to run the system maintenance now to test the setup?"
    read -p "Run initial execution? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
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
echo "✓ Log rotation configured: /etc/logrotate.d/periodic-system-maintenance"
echo ""
echo "The system will now:"
echo "• Run maintenance every hour"
echo "• Run maintenance 5 minutes after system startup"
echo "• Log all activities to /var/log/periodic-system-maintenance.log"
echo ""
echo "To check status:"
echo "  systemctl status periodic-system-maintenance.timer"
echo "  systemctl list-timers periodic-system-maintenance.timer"
echo ""
echo "To view logs:"
echo "  tail -f /var/log/periodic-system-maintenance.log"
echo "  journalctl -u periodic-system-maintenance.service -f"
echo ""
echo "To disable (if needed):"
echo "  sudo systemctl disable periodic-system-maintenance.timer"
echo "  sudo systemctl disable periodic-system-startup.service"
