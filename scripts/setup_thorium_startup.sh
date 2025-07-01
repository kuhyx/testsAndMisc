#!/bin/bash
# Script to set up automatic Thorium browser launch with Fitatu website on startup
# Opens https://www.fitatu.com/ in Thorium browser every time the system boots

set -e  # Exit on any error

# Function to check and request sudo privileges
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script requires sudo privileges to create systemd services."
        echo "Requesting sudo access..."
        exec sudo "$0" "$@"
    fi
}

# Check for sudo privileges first
check_sudo "$@"

echo "Thorium Browser Auto-Startup Setup"
echo "=================================="
echo "Current Date: $(date)"
echo "User: $USER"
echo "Original user: ${SUDO_USER:-$USER}"

# Target URL
TARGET_URL="https://www.fitatu.com/app/planner"
BROWSER_COMMAND="thorium-browser"
USER_HOME="/home/${SUDO_USER}"

echo ""
echo "Target URL: $TARGET_URL"
echo "Browser: $BROWSER_COMMAND"
echo "User home: $USER_HOME"

# Function to check if Thorium browser is installed
check_thorium_browser() {
    echo ""
    echo "1. Checking Thorium Browser Installation..."
    echo "=========================================="
    
    if ! command -v "$BROWSER_COMMAND" &> /dev/null; then
        echo "Warning: Thorium browser not found in PATH"
        echo "Checking alternative locations..."
        
        # Check common installation paths
        local alt_paths=(
            "/opt/thorium/thorium"
            "/usr/bin/thorium"
            "/usr/local/bin/thorium"
            "/opt/thorium-browser/thorium-browser"
            "${USER_HOME}/.local/bin/thorium-browser"
        )
        
        local found=false
        for path in "${alt_paths[@]}"; do
            if [[ -x "$path" ]]; then
                BROWSER_COMMAND="$path"
                echo "✓ Found Thorium browser at: $path"
                found=true
                break
            fi
        done
        
        if [[ "$found" != true ]]; then
            echo "Error: Thorium browser not found!"
            echo "Please install Thorium browser first or ensure it's in your PATH."
            echo ""
            echo "You can install Thorium browser from:"
            echo "https://thorium.rocks/"
            echo ""
            read -p "Continue anyway? The service will be created but may fail to start (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    else
        echo "✓ Thorium browser found: $(which $BROWSER_COMMAND)"
    fi
}

# Function to create the browser launcher script
create_launcher_script() {
    echo ""
    echo "2. Creating Browser Launcher Script..."
    echo "====================================="
    
    local launcher_script="/usr/local/bin/thorium-fitatu-launcher.sh"
    
    cat > "$launcher_script" << EOF
#!/bin/bash
# Thorium browser launcher for Fitatu website
# Created by setup_thorium_startup.sh on $(date)

# Set up environment
export DISPLAY=:0
export HOME="$USER_HOME"

# Function to wait for X11 server and desktop environment
wait_for_desktop() {
    local max_attempts=30
    local attempt=0
    
    echo "Waiting for X11 server and window manager to be ready..." >&2
    
    # Wait for X11 server
    while [[ \$attempt -lt \$max_attempts ]]; do
        if xset q &>/dev/null 2>&1; then
            echo "X11 server is ready" >&2
            break
        fi
        sleep 1
        ((attempt++))
    done
    
    if [[ \$attempt -eq \$max_attempts ]]; then
        echo "Timeout waiting for X11 server" >&2
        return 1
    fi
    
    # Quick check for window manager (no waiting loop)
    if pgrep -x i3 >/dev/null 2>&1; then
        echo "i3 window manager detected and running" >&2
    elif pgrep -x "i3wm" >/dev/null 2>&1; then
        echo "i3wm window manager detected and running" >&2
    elif wmctrl -m >/dev/null 2>&1; then
        echo "Window manager detected via wmctrl" >&2
    else
        echo "Window manager not detected, proceeding anyway" >&2
    fi
    
    return 0
}

# Function to launch browser
launch_browser() {
    echo "Launching Thorium browser with Fitatu..." >&2
    
    # Try to launch browser as the original user
    if command -v sudo &>/dev/null && [[ -n "${SUDO_USER}" ]]; then
        sudo -u "${SUDO_USER}" env DISPLAY=:0 HOME="$USER_HOME" "$BROWSER_COMMAND" "$TARGET_URL" &
    else
        "$BROWSER_COMMAND" "$TARGET_URL" &
    fi
    
    local browser_pid=\$!
    echo "Browser launched with PID: \$browser_pid" >&2
    
    return 0
}

# Main execution
echo "\$(date): Starting Thorium-Fitatu launcher" >&2

if wait_for_desktop; then
    launch_browser
    echo "\$(date): Thorium browser launch completed" >&2
else
    echo "\$(date): Failed to launch - desktop environment not ready" >&2
    exit 1
fi
EOF

    chmod +x "$launcher_script"
    echo "✓ Created launcher script: $launcher_script"
}

# Function to create systemd service for user session
create_user_systemd_service() {
    echo ""
    echo "3. Creating User Systemd Service..."
    echo "=================================="
    
    local user_systemd_dir="$USER_HOME/.config/systemd/user"
    local service_file="$user_systemd_dir/thorium-fitatu-startup.service"
    
    # Create user systemd directory
    sudo -u "${SUDO_USER}" mkdir -p "$user_systemd_dir"
    
    # Create the service file
    sudo -u "${SUDO_USER}" tee "$service_file" > /dev/null << EOF
[Unit]
Description=Launch Thorium Browser with Fitatu on Startup
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=oneshot
Environment=DISPLAY=:0
Environment=HOME=$USER_HOME
ExecStart=/usr/local/bin/thorium-fitatu-launcher.sh
StandardOutput=journal
StandardError=journal
RemainAfterExit=yes

# Restart settings
Restart=no

# Timeout settings
TimeoutStartSec=120

[Install]
WantedBy=default.target
EOF

    echo "✓ Created user systemd service: $service_file"
}

# Function to create system-wide systemd service (alternative approach)
create_system_systemd_service() {
    echo ""
    echo "4. Creating System Systemd Service..."
    echo "===================================="
    
    local service_file="/etc/systemd/system/thorium-fitatu-startup.service"
    
    cat > "$service_file" << EOF
[Unit]
Description=Launch Thorium Browser with Fitatu on Startup
After=multi-user.target network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/thorium-fitatu-launcher.sh
StandardOutput=journal
StandardError=journal
RemainAfterExit=yes

# Environment
Environment=DISPLAY=:0

# Restart settings
Restart=no

# Timeout settings
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
EOF

    echo "✓ Created system systemd service: $service_file"
}

# Function to create autostart desktop entry (additional method)
create_autostart_entry() {
    echo ""
    echo "5. Creating Autostart Desktop Entry..."
    echo "====================================="
    
    local autostart_dir="$USER_HOME/.config/autostart"
    local desktop_file="$autostart_dir/thorium-fitatu.desktop"
    
    # Create autostart directory
    sudo -u "${SUDO_USER}" mkdir -p "$autostart_dir"
    
    # Create desktop entry
    sudo -u "${SUDO_USER}" tee "$desktop_file" > /dev/null << EOF
[Desktop Entry]
Type=Application
Name=Thorium Fitatu Startup
Comment=Launch Thorium Browser with Fitatu website
Exec=/usr/local/bin/thorium-fitatu-launcher.sh
Icon=thorium-browser
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
Terminal=false
Categories=Network;WebBrowser;
EOF

    echo "✓ Created autostart desktop entry: $desktop_file"
}

# Function to create i3 config autostart entry
create_i3_autostart() {
    echo ""
    echo "6. Creating i3 Config Autostart Entry..."
    echo "======================================="
    
    local i3_config="$USER_HOME/.config/i3/config"
    local i3_config_dir="$USER_HOME/.config/i3"
    
    # Create i3 config directory if it doesn't exist
    sudo -u "${SUDO_USER}" mkdir -p "$i3_config_dir"
    
    # Check if i3 config exists
    if [[ -f "$i3_config" ]]; then
        # Check if autostart entry already exists
        if ! sudo -u "${SUDO_USER}" grep -q "thorium-fitatu-launcher" "$i3_config"; then
            # Add autostart entry to i3 config
            sudo -u "${SUDO_USER}" bash -c "echo '' >> '$i3_config'"
            sudo -u "${SUDO_USER}" bash -c "echo '# Auto-start Thorium browser with Fitatu' >> '$i3_config'"
            sudo -u "${SUDO_USER}" bash -c "echo 'exec --no-startup-id /usr/local/bin/thorium-fitatu-launcher.sh' >> '$i3_config'"
            echo "✓ Added autostart entry to i3 config: $i3_config"
        else
            echo "✓ Autostart entry already exists in i3 config"
        fi
    else
        echo "Warning: i3 config file not found at $i3_config"
        echo "You may need to manually add the following line to your i3 config:"
        echo "exec --no-startup-id /usr/local/bin/thorium-fitatu-launcher.sh"
    fi
}

# Function to create a script to enable user service after login
create_user_enable_script() {
    local enable_script="$USER_HOME/.config/thorium-enable-service.sh"
    
    sudo -u "${SUDO_USER}" tee "$enable_script" > /dev/null << 'EOF'
#!/bin/bash
# Script to enable thorium-fitatu-startup user service
# This runs once to enable the service, then removes itself

# Enable the user service
systemctl --user daemon-reload
systemctl --user enable thorium-fitatu-startup.service

# Remove this script after successful execution
rm "$0"
EOF

    sudo -u "${SUDO_USER}" chmod +x "$enable_script"
    
    # Add to user's .bashrc to run on next login
    local bashrc="$USER_HOME/.bashrc"
    if [[ -f "$bashrc" ]]; then
        sudo -u "${SUDO_USER}" bash -c "echo '' >> '$bashrc'"
        sudo -u "${SUDO_USER}" bash -c "echo '# Auto-enable thorium service (temporary)' >> '$bashrc'"
        sudo -u "${SUDO_USER}" bash -c "echo '[[ -x ~/.config/thorium-enable-service.sh ]] && ~/.config/thorium-enable-service.sh' >> '$bashrc'"
    fi
}

# Function to enable services
enable_services() {
    echo ""
    echo "7. Enabling Services..."
    echo "======================"
    
    # Reload systemd daemon
    systemctl daemon-reload
    echo "✓ System daemon reloaded"
    
    # Enable system service
    systemctl enable thorium-fitatu-startup.service
    echo "✓ System service enabled"
    
    # Enable lingering for the user (allows user services to run without login)
    loginctl enable-linger "${SUDO_USER}"
    echo "✓ User lingering enabled"
    
    # Create a script to enable user service after login
    create_user_enable_script
    echo "✓ User service will be enabled on next login"
}

# Function to test the setup
test_setup() {
    echo ""
    echo "8. Testing Setup..."
    echo "=================="
    
    echo "Would you like to test the browser launcher now?"
    read -p "Test launch Thorium browser with Fitatu? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Testing browser launch..."
        echo "Note: This will open Thorium browser with Fitatu website"
        
        # Test the launcher immediately
        if /usr/local/bin/thorium-fitatu-launcher.sh; then
            echo "✓ Test launch completed successfully"
        else
            echo "✗ Test launch failed"
            echo "Check that Thorium browser is properly installed and accessible"
        fi
    else
        echo "Skipping test launch"
    fi
}

# Function to show usage instructions
show_instructions() {
    echo ""
    echo "=========================================="
    echo "Thorium Browser Auto-Startup Setup Complete"
    echo "=========================================="
    echo "Summary:"
    echo "✓ Launcher script created: /usr/local/bin/thorium-fitatu-launcher.sh"
    echo "✓ System service created: thorium-fitatu-startup.service"
    echo "✓ User service created: ~/.config/systemd/user/thorium-fitatu-startup.service"
    echo "✓ Autostart entry created: ~/.config/autostart/thorium-fitatu.desktop"
    echo "✓ i3 autostart entry added to: ~/.config/i3/config"
    echo "✓ Services enabled for automatic startup"
    echo ""
    echo "The system will now:"
    echo "• Launch Thorium browser with $TARGET_URL on every startup"
    echo "• Use multiple methods to ensure reliable startup"
    echo "• Wait for desktop environment to be ready before launching"
    echo "• User service will be enabled automatically on next login"
    echo ""
    echo "To check status:"
    echo "  systemctl status thorium-fitatu-startup.service"
    echo "  systemctl --user status thorium-fitatu-startup.service (after login)"
    echo ""
    echo "To view logs:"
    echo "  journalctl -u thorium-fitatu-startup.service"
    echo "  journalctl --user -u thorium-fitatu-startup.service"
    echo ""
    echo "To disable (if needed):"
    echo "  sudo systemctl disable thorium-fitatu-startup.service"
    echo "  systemctl --user disable thorium-fitatu-startup.service"
    echo "  rm ~/.config/autostart/thorium-fitatu.desktop"
    echo ""
    echo "IMPORTANT: Browser will launch automatically on next reboot!"
}

# Main execution
check_thorium_browser
create_launcher_script
create_user_systemd_service
create_system_systemd_service
create_autostart_entry
create_i3_autostart
enable_services
test_setup
show_instructions
