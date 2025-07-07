#!/bin/bash
# Script to set up automatic PC shutdown at midnight on Arch Linux
# Creates systemd timer and service for daily shutdown at 00:00
# Handles sudo privileges automatically

set -e  # Exit on any error

echo "Midnight Auto-Shutdown Setup for Arch Linux"
echo "==========================================="
echo "Current Date: $(date)"
echo "User: ${SUDO_USER:-$USER}"

# Function to check and request sudo privileges
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script requires sudo privileges to create systemd services."
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

echo "Target user: $ACTUAL_USER"
echo "User home: $USER_HOME"

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

[Install]
WantedBy=multi-user.target
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

# Main execution flow
main() {
    # Check for sudo privileges
    check_sudo "$@"
    
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

# Run main function
main "$@"
