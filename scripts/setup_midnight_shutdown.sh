#!/bin/bash
# Script to set up automatic PC shutdown at midnight on Arch Linux
# Creates systemd timer and service for daily shutdown at 00:00
# Handles sudo privileges automatically

set -e  # Exit on any error

# Function to show usage
show_usage() {
    echo "Midnight Auto-Shutdown Setup for Arch Linux"
    echo "==========================================="
    echo "Usage: $0 [enable|disable|status]"
    echo ""
    echo "Commands:"
    echo "  enable   - Set up automatic midnight shutdown (default)"
    echo "  disable  - Remove automatic midnight shutdown"
    echo "  status   - Show current status"
    echo ""
}

# Function to check and request sudo privileges
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script requires sudo privileges to manage systemd services."
        echo "Requesting sudo access..."
        exec sudo "$0" "$@"
    fi
}

# Get the actual user (even when running with sudo)
if [[ -n "$SUDO_USER" ]]; then
    ACTUAL_USER="$SUDO_USER"
    USER_HOME="/home/$SUDO_USER"
else
    ACTUAL_USER="$USER"
    USER_HOME="$HOME"
fi

# Function to disable and remove midnight shutdown
disable_midnight_shutdown() {
    echo "Disabling Midnight Auto-Shutdown"
    echo "==============================="
    echo "Current Date: $(date)"
    echo "User: $ACTUAL_USER"
    echo ""
    
    local timer_file="/etc/systemd/system/midnight-shutdown.timer"
    local service_file="/etc/systemd/system/midnight-shutdown.service"
    local script_file="/usr/local/bin/midnight-shutdown-manager.sh"
    local removed_files=()
    
    # Stop and disable timer if it exists
    if systemctl is-active midnight-shutdown.timer &>/dev/null; then
        echo "Stopping midnight-shutdown timer..."
        systemctl stop midnight-shutdown.timer
        echo "✓ Timer stopped"
    fi
    
    if systemctl is-enabled midnight-shutdown.timer &>/dev/null; then
        echo "Disabling midnight-shutdown timer..."
        systemctl disable midnight-shutdown.timer
        echo "✓ Timer disabled"
    fi
    
    # Remove timer file
    if [[ -f "$timer_file" ]]; then
        rm -f "$timer_file"
        removed_files+=("$timer_file")
        echo "✓ Removed timer file: $timer_file"
    fi
    
    # Remove service file
    if [[ -f "$service_file" ]]; then
        rm -f "$service_file"
        removed_files+=("$service_file")
        echo "✓ Removed service file: $service_file"
    fi
    
    # Remove management script
    if [[ -f "$script_file" ]]; then
        rm -f "$script_file"
        removed_files+=("$script_file")
        echo "✓ Removed management script: $script_file"
    fi
    
    # Reload systemd daemon
    if [[ ${#removed_files[@]} -gt 0 ]]; then
        echo "Reloading systemd daemon..."
        systemctl daemon-reload
        echo "✓ Systemd daemon reloaded"
    fi
    
    echo ""
    echo "=========================================="
    echo "Midnight Auto-Shutdown Removal Complete"
    echo "=========================================="
    
    if [[ ${#removed_files[@]} -gt 0 ]]; then
        echo "Removed files:"
        printf "  %s\n" "${removed_files[@]}"
        echo ""
        echo "✓ Automatic midnight shutdown has been completely disabled"
        echo "✓ Your PC will no longer shutdown automatically at midnight"
    else
        echo "No midnight shutdown configuration was found to remove."
    fi
    
    echo ""
}

# Function to show current status
show_current_status() {
    echo "Midnight Auto-Shutdown Status"
    echo "============================"
    echo "Current Date: $(date)"
    echo "User: $ACTUAL_USER"
    echo ""
    
    local timer_exists=false
    local service_exists=false
    local script_exists=false
    
    # Check if files exist
    if [[ -f "/etc/systemd/system/midnight-shutdown.timer" ]]; then
        timer_exists=true
        echo "✓ Timer file exists"
    else
        echo "✗ Timer file missing"
    fi
    
    if [[ -f "/etc/systemd/system/midnight-shutdown.service" ]]; then
        service_exists=true
        echo "✓ Service file exists"
    else
        echo "✗ Service file missing"
    fi
    
    if [[ -f "/usr/local/bin/midnight-shutdown-manager.sh" ]]; then
        script_exists=true
        echo "✓ Management script exists"
    else
        echo "✗ Management script missing"
    fi
    
    echo ""
    
    # Check systemd status
    if $timer_exists; then
        if systemctl is-enabled midnight-shutdown.timer &>/dev/null; then
            echo "✓ Timer is enabled"
            if systemctl is-active midnight-shutdown.timer &>/dev/null; then
                echo "✓ Timer is active"
                echo ""
                echo "Next scheduled shutdown:"
                systemctl list-timers midnight-shutdown.timer --no-pager 2>/dev/null | grep midnight-shutdown || echo "Timer information not available"
            else
                echo "✗ Timer is not active"
            fi
        else
            echo "✗ Timer is not enabled"
        fi
    else
        echo "Status: NOT CONFIGURED"
    fi
    
    echo ""
}

# Function to create the shutdown service
create_shutdown_service() {
    echo ""
    echo "1. Creating Systemd Shutdown Service..."
    echo "======================================"
    
    local service_file="/etc/systemd/system/midnight-shutdown.service"
    
    cat > "$service_file" << 'EOF'
[Unit]
Description=Automatic PC shutdown at midnight
DefaultDependencies=false
Before=shutdown.target reboot.target halt.target

[Service]
Type=oneshot
ExecStart=/usr/bin/systemctl poweroff
TimeoutStartSec=0
StandardOutput=journal
StandardError=journal
EOF

    echo "✓ Created systemd service: $service_file"
}

# Function to create the shutdown timer
create_shutdown_timer() {
    echo ""
    echo "2. Creating Systemd Shutdown Timer..."
    echo "==================================="
    
    local timer_file="/etc/systemd/system/midnight-shutdown.timer"
    
    cat > "$timer_file" << 'EOF'
[Unit]
Description=Timer for automatic PC shutdown at midnight
Requires=midnight-shutdown.service

[Timer]
OnCalendar=*-*-* 00:00:00
Persistent=false
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF

    echo "✓ Created systemd timer: $timer_file"
}

# Function to create management script
create_management_script() {
    echo ""
    echo "3. Creating Management Script..."
    echo "=============================="
    
    local script_file="/usr/local/bin/midnight-shutdown-manager.sh"
    
    cat > "$script_file" << 'EOF'
#!/bin/bash
# Midnight Auto-Shutdown Manager
# Provides easy management of the midnight shutdown feature

TIMER_NAME="midnight-shutdown.timer"
SERVICE_NAME="midnight-shutdown.service"

show_status() {
    echo "Midnight Auto-Shutdown Status"
    echo "============================"
    
    if systemctl is-enabled "$TIMER_NAME" &>/dev/null; then
        echo "Status: ENABLED"
        if systemctl is-active "$TIMER_NAME" &>/dev/null; then
            echo "Timer: ACTIVE"
        else
            echo "Timer: INACTIVE"
        fi
    else
        echo "Status: NOT ENABLED"
    fi
    
    echo ""
    echo "Next scheduled shutdown:"
    systemctl list-timers "$TIMER_NAME" --no-pager 2>/dev/null | grep "$TIMER_NAME" || echo "Timer not active"
    
    echo ""
    echo "Recent logs:"
    journalctl -u "$SERVICE_NAME" --no-pager -n 5 2>/dev/null || echo "No recent logs"
}

case "$1" in
    "status")
        show_status
        ;;
    "logs")
        echo "Midnight Auto-Shutdown Logs"
        echo "=========================="
        journalctl -u "$SERVICE_NAME" --no-pager -n 20
        ;;
    *)
        echo "Midnight Auto-Shutdown Manager"
        echo "Usage: $0 {status|logs}"
        echo ""
        echo "Commands:"
        echo "  status   - Show current status and next shutdown time"
        echo "  logs     - Show recent shutdown logs"
        echo ""
        show_status
        ;;
esac
EOF

    chmod +x "$script_file"
    echo "✓ Created management script: $script_file"
}

# Function to enable the timer
enable_timer() {
    echo ""
    echo "4. Enabling Shutdown Timer..."
    echo "============================"
    
    # Reload systemd daemon
    systemctl daemon-reload
    echo "✓ Reloaded systemd daemon"
    
    # Enable the timer
    systemctl enable midnight-shutdown.timer
    echo "✓ Enabled midnight-shutdown timer"
    
    # Start the timer
    systemctl start midnight-shutdown.timer
    echo "✓ Started midnight-shutdown timer"
}

# Function to test the setup
test_setup() {
    echo ""
    echo "5. Testing Setup..."
    echo "=================="
    
    echo "Service files:"
    if [[ -f "/etc/systemd/system/midnight-shutdown.service" ]]; then
        echo "✓ Service file exists"
    else
        echo "✗ Service file missing"
    fi
    
    if [[ -f "/etc/systemd/system/midnight-shutdown.timer" ]]; then
        echo "✓ Timer file exists"
    else
        echo "✗ Timer file missing"
    fi
    
    echo ""
    echo "Timer status:"
    if systemctl is-enabled midnight-shutdown.timer &>/dev/null; then
        echo "✓ Timer is enabled"
    else
        echo "✗ Timer is not enabled"
    fi
    
    if systemctl is-active midnight-shutdown.timer &>/dev/null; then
        echo "✓ Timer is active"
    else
        echo "✗ Timer is not active"
    fi
    
    echo ""
    echo "Next scheduled shutdown:"
    systemctl list-timers midnight-shutdown.timer --no-pager 2>/dev/null | grep midnight-shutdown || echo "Timer information not available"
}

# Function to show final instructions
show_instructions() {
    echo ""
    echo "=========================================="
    echo "Midnight Auto-Shutdown Setup Complete"
    echo "=========================================="
    echo "Summary:"
    echo "✓ Systemd service created (/etc/systemd/system/midnight-shutdown.service)"
    echo "✓ Systemd timer created (/etc/systemd/system/midnight-shutdown.timer)"
    echo "✓ Management script created (/usr/local/bin/midnight-shutdown-manager.sh)"
    echo "✓ Timer enabled and started"
    echo ""
    echo "Your PC will now automatically shutdown at 00:00 (midnight) every day."
    echo ""
    echo "Management commands:"
    echo "  sudo midnight-shutdown-manager.sh status   - Check status"
    echo "  sudo midnight-shutdown-manager.sh logs     - View shutdown logs"
    echo ""
    echo "Next shutdown: Tonight at 00:00"
    echo ""
    echo "WARNING: This will permanently shutdown your PC every night at midnight."
    echo "Make sure to save your work before midnight!"
    echo ""
}

# Function to prompt for confirmation
confirm_setup() {
    echo ""
    echo "WARNING: Auto-Shutdown Confirmation"
    echo "=================================="
    echo "This will set up your PC to automatically shutdown every day at midnight (00:00)."
    echo ""
    echo "Important considerations:"
    echo "- Any unsaved work will be lost"
    echo "- Running processes will be terminated"
    echo "- Downloads/uploads in progress will be interrupted"
    echo "- You'll need to manually power on your PC each day"
    echo ""
    read -p "Do you want to proceed? (y/N): " confirm
    
    case "$confirm" in
        [yY]|[yY][eE][sS])
            echo "Proceeding with setup..."
            return 0
            ;;
        *)
            echo "Setup cancelled."
            exit 0
            ;;
    esac
}

# Function to confirm disable
confirm_disable() {
    echo ""
    echo "Disable Auto-Shutdown Confirmation"
    echo "================================="
    echo "This will completely remove the automatic midnight shutdown configuration."
    echo ""
    echo "After disabling:"
    echo "- Your PC will no longer shutdown automatically at midnight"
    echo "- All related systemd services and timers will be removed"
    echo "- The management script will be deleted"
    echo ""
    read -p "Do you want to proceed with disabling? (y/N): " confirm
    
    case "$confirm" in
        [yY]|[yY][eE][sS])
            echo "Proceeding with disable..."
            return 0
            ;;
        *)
            echo "Disable cancelled."
            exit 0
            ;;
    esac
}

# Main execution flow for enable
enable_midnight_shutdown() {
    echo "Midnight Auto-Shutdown Setup for Arch Linux"
    echo "==========================================="
    echo "Current Date: $(date)"
    echo "User: $ACTUAL_USER"
    echo "Target user: $ACTUAL_USER"
    echo "User home: $USER_HOME"
    
    # Confirm setup
    confirm_setup
    
    # Create systemd files
    create_shutdown_service
    create_shutdown_timer
    create_management_script
    
    # Enable and start timer
    enable_timer
    
    # Test setup
    test_setup
    
    # Show instructions
    show_instructions
}

# Parse command line arguments
case "${1:-enable}" in
    "enable")
        check_sudo "$@"
        enable_midnight_shutdown
        ;;
    "disable")
        check_sudo "$@"
        confirm_disable
        disable_midnight_shutdown
        ;;
    "status")
        check_sudo "$@"
        show_current_status
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        echo "Error: Unknown command '$1'"
        echo ""
        show_usage
        exit 1
        ;;
esac
