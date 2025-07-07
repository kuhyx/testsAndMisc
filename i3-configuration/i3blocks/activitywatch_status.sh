#!/bin/bash
# ActivityWatch status script for i3blocks
# Shows ActivityWatch installation and running status

# Check if ActivityWatch is installed
check_installed() {
    # Check if activitywatch-bin package is installed
    if pacman -Qi activitywatch-bin &>/dev/null; then
        return 0
    fi
    
    # Check if aw-qt binary exists
    if command -v aw-qt &>/dev/null; then
        return 0
    fi
    
    return 1
}

# Check if ActivityWatch is running
check_running() {
    # Check for aw-qt process
    if pgrep -f "aw-qt" >/dev/null 2>&1; then
        return 0
    fi
    
    # Check for aw-server process
    if pgrep -f "aw-server" >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# Main logic
if ! check_installed; then
    echo "AW uninstalled"
    echo
    echo "#FF0000"  # Red
elif check_running; then
    echo "AW on"
    echo
    echo "#00FF00"  # Green
else
    echo "AW off"
    echo
    echo "#FF0000"  # Red
fi
