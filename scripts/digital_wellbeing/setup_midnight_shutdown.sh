#!/bin/bash
# Script to set up automatic PC shutdown with day-specific time windows
# Monday-Wednesday: Shutdown between 21:00-05:00
# Thursday-Sunday: Shutdown between 22:00-05:00
# Handles sudo privileges automatically

set -e # Exit on any error

# Function to show usage
show_usage() {
  echo "Day-Specific Auto-Shutdown Setup for Arch Linux"
  echo "==============================================="
  echo "Usage: $0 [enable|disable|status]"
  echo ""
  echo "Commands:"
  echo "  enable   - Set up automatic shutdown with day-specific windows (default)"
  echo "  disable  - Remove automatic shutdown"
  echo "  status   - Show current status"
  echo ""
  echo "Shutdown Schedule:"
  echo "  Monday-Wednesday: 21:00-05:00"
  echo "  Thursday-Sunday:  22:00-05:00"
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
if [[ -n $SUDO_USER ]]; then
  ACTUAL_USER="$SUDO_USER"
  USER_HOME="/home/$SUDO_USER"
else
  ACTUAL_USER="$USER"
  USER_HOME="$HOME"
fi

# Function to disable and remove midnight shutdown
disable_midnight_shutdown() {
  echo "Disabling Day-Specific Auto-Shutdown"
  echo "===================================="
  echo "Current Date: $(date)"
  echo "User: $ACTUAL_USER"
  echo ""

  local timer_file="/etc/systemd/system/day-specific-shutdown.timer"
  local service_file="/etc/systemd/system/day-specific-shutdown.service"
  local script_file="/usr/local/bin/day-specific-shutdown-manager.sh"
  local check_script="/usr/local/bin/day-specific-shutdown-check.sh"
  local removed_files=()

  # Stop and disable timer if it exists
  if systemctl is-active day-specific-shutdown.timer &> /dev/null; then
    echo "Stopping day-specific-shutdown timer..."
    systemctl stop day-specific-shutdown.timer
    echo "✓ Timer stopped"
  fi

  if systemctl is-enabled day-specific-shutdown.timer &> /dev/null; then
    echo "Disabling day-specific-shutdown timer..."
    systemctl disable day-specific-shutdown.timer
    echo "✓ Timer disabled"
  fi

  # Remove timer file
  if [[ -f $timer_file ]]; then
    rm -f "$timer_file"
    removed_files+=("$timer_file")
    echo "✓ Removed timer file: $timer_file"
  fi

  # Remove service file
  if [[ -f $service_file ]]; then
    rm -f "$service_file"
    removed_files+=("$service_file")
    echo "✓ Removed service file: $service_file"
  fi

  # Remove management script
  if [[ -f $script_file ]]; then
    rm -f "$script_file"
    removed_files+=("$script_file")
    echo "✓ Removed management script: $script_file"
  fi

  # Remove check script
  if [[ -f $check_script ]]; then
    rm -f "$check_script"
    removed_files+=("$check_script")
    echo "✓ Removed check script: $check_script"
  fi

  # Reload systemd daemon
  if [[ ${#removed_files[@]} -gt 0 ]]; then
    echo "Reloading systemd daemon..."
    systemctl daemon-reload
    echo "✓ Systemd daemon reloaded"
  fi

  echo ""
  echo "============================================="
  echo "Day-Specific Auto-Shutdown Removal Complete"
  echo "============================================="

  if [[ ${#removed_files[@]} -gt 0 ]]; then
    echo "Removed files:"
    printf "  %s\n" "${removed_files[@]}"
    echo ""
    echo "✓ Automatic day-specific shutdown has been completely disabled"
    echo "✓ Your PC will no longer shutdown automatically"
  else
    echo "No day-specific shutdown configuration was found to remove."
  fi

  echo ""
}

# Function to show current status
show_current_status() {
  echo "Day-Specific Auto-Shutdown Status"
  echo "================================="
  echo "Current Date: $(date)"
  echo "User: $ACTUAL_USER"
  echo ""

  local timer_exists=false

  # Check if files exist
  if [[ -f "/etc/systemd/system/day-specific-shutdown.timer" ]]; then
    timer_exists=true
    echo "✓ Timer file exists"
  else
    echo "✗ Timer file missing"
  fi

  if [[ -f "/etc/systemd/system/day-specific-shutdown.service" ]]; then
    echo "✓ Service file exists"
  else
    echo "✗ Service file missing"
  fi

  if [[ -f "/usr/local/bin/day-specific-shutdown-manager.sh" ]]; then
    echo "✓ Management script exists"
  else
    echo "✗ Management script missing"
  fi

  echo ""

  # Check systemd status
  if $timer_exists; then
    if systemctl is-enabled day-specific-shutdown.timer &> /dev/null; then
      echo "✓ Timer is enabled"
      if systemctl is-active day-specific-shutdown.timer &> /dev/null; then
        echo "✓ Timer is active"
        echo ""
        echo "Next scheduled shutdown check:"
        systemctl list-timers day-specific-shutdown.timer --no-pager 2> /dev/null | grep day-specific-shutdown || echo "Timer information not available"
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
  echo "Shutdown Schedule:"
  echo "  Monday-Wednesday: 21:00-05:00"
  echo "  Thursday-Sunday:  22:00-05:00"
  echo ""
}

# Function to create the shutdown service
create_shutdown_service() {
  echo ""
  echo "1. Creating Systemd Shutdown Service..."
  echo "======================================"

  local service_file="/etc/systemd/system/day-specific-shutdown.service"

  cat > "$service_file" << 'EOF'
[Unit]
Description=Automatic PC shutdown with day-specific time windows
DefaultDependencies=false
Before=shutdown.target reboot.target halt.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/day-specific-shutdown-check.sh
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

  local timer_file="/etc/systemd/system/day-specific-shutdown.timer"

  cat > "$timer_file" << 'EOF'
[Unit]
Description=Timer for automatic PC shutdown with day-specific windows
Requires=day-specific-shutdown.service

[Timer]
OnCalendar=*-*-* 21:00:00
OnCalendar=*-*-* 21:30:00
OnCalendar=*-*-* 22:00:00
OnCalendar=*-*-* 22:30:00
OnCalendar=*-*-* 23:00:00
OnCalendar=*-*-* 23:30:00
OnCalendar=*-*-* 00:00:00
OnCalendar=*-*-* 00:30:00
OnCalendar=*-*-* 01:00:00
OnCalendar=*-*-* 01:30:00
OnCalendar=*-*-* 02:00:00
OnCalendar=*-*-* 02:30:00
OnCalendar=*-*-* 03:00:00
OnCalendar=*-*-* 03:30:00
OnCalendar=*-*-* 04:00:00
OnCalendar=*-*-* 04:30:00
OnCalendar=*-*-* 05:00:00
Persistent=false
AccuracySec=1s
WakeSystem=false
RandomizedDelaySec=0

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

  local script_file="/usr/local/bin/day-specific-shutdown-manager.sh"

  cat > "$script_file" << 'EOF'
#!/bin/bash
# Day-Specific Auto-Shutdown Manager
# Provides easy management of the day-specific shutdown feature

TIMER_NAME="day-specific-shutdown.timer"
SERVICE_NAME="day-specific-shutdown.service"

show_status() {
    echo "Day-Specific Auto-Shutdown Status"
    echo "================================="
    
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
    echo "Shutdown Schedule:"
    echo "  Monday-Wednesday: 21:00-05:00"
    echo "  Thursday-Sunday:  22:00-05:00"
    
    echo ""
    echo "Next scheduled checks:"
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
        echo "Day-Specific Auto-Shutdown Logs"
        echo "==============================="
        journalctl -u "$SERVICE_NAME" --no-pager -n 20
        ;;
    *)
        echo "Day-Specific Auto-Shutdown Manager"
        echo "Usage: $0 {status|logs}"
        echo ""
        echo "Commands:"
        echo "  status   - Show current status and next shutdown checks"
        echo "  logs     - Show recent shutdown logs"
        echo ""
        echo "Shutdown Schedule:"
        echo "  Monday-Wednesday: 21:00-05:00"
        echo "  Thursday-Sunday:  22:00-05:00"
        echo ""
        show_status
        ;;
esac
EOF

  chmod +x "$script_file"
  echo "✓ Created management script: $script_file"
}

# Function to create smart shutdown check script
create_shutdown_check_script() {
  echo ""
  echo "4. Creating Smart Shutdown Check Script..."
  echo "========================================"

  local check_script="/usr/local/bin/day-specific-shutdown-check.sh"

  cat > "$check_script" << 'EOF'
#!/bin/bash
# Smart day-specific shutdown check script
# Different shutdown windows based on day of week:
# Monday-Wednesday: 21:00-05:00
# Thursday-Sunday: 22:00-05:00

# Get current time and day
current_hour=$(date +%H)
current_minute=$(date +%M)
current_time_minutes=$((10#$current_hour * 60 + 10#$current_minute))
day_of_week=$(date +%u)  # 1=Monday, 7=Sunday
day_name=$(date +%A)

# Convert time to minutes for easier comparison
# 21:00 = 1260 minutes, 22:00 = 1320 minutes, 05:00 = 300 minutes
# 00:00 = 0 minutes, 05:00 = 300 minutes

logger -t day-specific-shutdown "Checking shutdown conditions at $(date) - Day: $day_name ($day_of_week), Time: $current_hour:$current_minute"

# Determine if we should shutdown based on day and time
should_shutdown=false

if [[ $day_of_week -ge 1 ]] && [[ $day_of_week -le 3 ]]; then
    # Monday (1), Tuesday (2), Wednesday (3): shutdown window 21:00-05:00
    logger -t day-specific-shutdown "Today is $day_name - checking 21:00-05:00 window"
    
    # Check if time is between 21:00 (1260 minutes) and 23:59 (1439 minutes)
    # OR between 00:00 (0 minutes) and 05:00 (300 minutes)
    if [[ $current_time_minutes -ge 1260 ]] || [[ $current_time_minutes -le 300 ]]; then
        should_shutdown=true
        if [[ $current_time_minutes -ge 1260 ]]; then
            logger -t day-specific-shutdown "Time $current_hour:$current_minute is within evening shutdown window (21:00-23:59)"
        else
            logger -t day-specific-shutdown "Time $current_hour:$current_minute is within morning shutdown window (00:00-05:00)"
        fi
    else
        logger -t day-specific-shutdown "Time $current_hour:$current_minute is outside shutdown window (21:00-05:00)"
    fi
else
    # Thursday (4), Friday (5), Saturday (6), Sunday (7): shutdown window 22:00-05:00
    logger -t day-specific-shutdown "Today is $day_name - checking 22:00-05:00 window"
    
    # Check if time is between 22:00 (1320 minutes) and 23:59 (1439 minutes)
    # OR between 00:00 (0 minutes) and 05:00 (300 minutes)
    if [[ $current_time_minutes -ge 1320 ]] || [[ $current_time_minutes -le 300 ]]; then
        should_shutdown=true
        if [[ $current_time_minutes -ge 1320 ]]; then
            logger -t day-specific-shutdown "Time $current_hour:$current_minute is within evening shutdown window (22:00-23:59)"
        else
            logger -t day-specific-shutdown "Time $current_hour:$current_minute is within morning shutdown window (00:00-05:00)"
        fi
    else
        logger -t day-specific-shutdown "Time $current_hour:$current_minute is outside shutdown window (22:00-05:00)"
    fi
fi

if [[ $should_shutdown == true ]]; then
    echo "$(date): Executing shutdown - current time $current_hour:$current_minute is within shutdown window for $day_name"
    logger -t day-specific-shutdown "Executing scheduled shutdown at $(date)"
    /usr/bin/systemctl poweroff
else
    echo "$(date): Skipping shutdown - not within shutdown window for $day_name (current: $current_hour:$current_minute)"
    logger -t day-specific-shutdown "Skipped shutdown - not within shutdown window for $day_name (current: $current_hour:$current_minute)"
fi
EOF

  chmod +x "$check_script"
  echo "✓ Created smart shutdown check script: $check_script"
}

# Function to enable the timer
enable_timer() {
  echo ""
  echo "5. Enabling Shutdown Timer..."
  echo "============================"

  # Reload systemd daemon
  systemctl daemon-reload
  echo "✓ Reloaded systemd daemon"

  # Enable the timer
  systemctl enable day-specific-shutdown.timer
  echo "✓ Enabled day-specific-shutdown timer"

  # Start the timer
  systemctl start day-specific-shutdown.timer
  echo "✓ Started day-specific-shutdown timer"
}

# Function to test the setup
test_setup() {
  echo ""
  echo "6. Testing Setup..."
  echo "=================="

  echo "Service files:"
  if [[ -f "/etc/systemd/system/day-specific-shutdown.service" ]]; then
    echo "✓ Service file exists"
  else
    echo "✗ Service file missing"
  fi

  if [[ -f "/etc/systemd/system/day-specific-shutdown.timer" ]]; then
    echo "✓ Timer file exists"
  else
    echo "✗ Timer file missing"
  fi

  echo ""
  echo "Timer status:"
  if systemctl is-enabled day-specific-shutdown.timer &> /dev/null; then
    echo "✓ Timer is enabled"
  else
    echo "✗ Timer is not enabled"
  fi

  if systemctl is-active day-specific-shutdown.timer &> /dev/null; then
    echo "✓ Timer is active"
  else
    echo "✗ Timer is not active"
  fi

  echo ""
  echo "Next scheduled checks:"
  systemctl list-timers day-specific-shutdown.timer --no-pager 2> /dev/null | head -5 | grep day-specific-shutdown || echo "Timer information not available"
}

# Function to show final instructions
show_instructions() {
  echo ""
  echo "================================================="
  echo "Day-Specific Auto-Shutdown Setup Complete"
  echo "================================================="
  echo "Summary:"
  echo "✓ Systemd service created (/etc/systemd/system/day-specific-shutdown.service)"
  echo "✓ Systemd timer created (/etc/systemd/system/day-specific-shutdown.timer)"
  echo "✓ Management script created (/usr/local/bin/day-specific-shutdown-manager.sh)"
  echo "✓ Smart check script created (/usr/local/bin/day-specific-shutdown-check.sh)"
  echo "✓ Timer enabled and started"
  echo ""
  echo "Shutdown Schedule:"
  echo "  Monday-Wednesday: 21:00-05:00 (9:00 PM to 5:00 AM)"
  echo "  Thursday-Sunday:  22:00-05:00 (10:00 PM to 5:00 AM)"
  echo ""
  echo "Management commands:"
  echo "  sudo day-specific-shutdown-manager.sh status   - Check status"
  echo "  sudo day-specific-shutdown-manager.sh logs     - View shutdown logs"
  echo ""
  echo "How it works:"
  echo "• Timer checks every 30 minutes during potential shutdown windows"
  echo "• Smart logic determines shutdown eligibility based on day and time"
  echo "• Prevents accidental shutdowns outside designated time windows"
  echo ""
  echo "WARNING: This will automatically shutdown your PC during designated hours."
  echo "Make sure to save your work before the shutdown windows!"
  echo ""
}

# Function to prompt for confirmation
confirm_setup() {
  echo ""
  echo "WARNING: Day-Specific Auto-Shutdown Confirmation"
  echo "==============================================="
  echo "This will set up your PC to automatically shutdown during specific time windows."
  echo ""
  echo "Shutdown Schedule:"
  echo "  Monday-Wednesday: 21:00-05:00 (9:00 PM to 5:00 AM)"
  echo "  Thursday-Sunday:  22:00-05:00 (10:00 PM to 5:00 AM)"
  echo ""
  echo "Important considerations:"
  echo "- Any unsaved work will be lost during shutdown windows"
  echo "- Running processes will be terminated"
  echo "- Downloads/uploads in progress will be interrupted"
  echo "- You'll need to manually power on your PC each day"
  echo "- Timer checks every 30 minutes during potential shutdown windows"
  echo ""
  read -r -p "Do you want to proceed? (y/N): " confirm

  case "$confirm" in
    [yY] | [yY][eE][sS])
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
  echo "Disable Day-Specific Auto-Shutdown Confirmation"
  echo "==============================================="
  echo "This will completely remove the automatic day-specific shutdown configuration."
  echo ""
  echo "After disabling:"
  echo "- Your PC will no longer shutdown automatically during any time windows"
  echo "- All related systemd services and timers will be removed"
  echo "- The management and check scripts will be deleted"
  echo ""
  read -r -p "Do you want to proceed with disabling? (y/N): " confirm

  case "$confirm" in
    [yY] | [yY][eE][sS])
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
  echo "Day-Specific Auto-Shutdown Setup for Arch Linux"
  echo "==============================================="
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
  create_shutdown_check_script

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
  "help" | "-h" | "--help")
    show_usage
    ;;
  *)
    echo "Error: Unknown command '$1'"
    echo ""
    show_usage
    exit 1
    ;;
esac
