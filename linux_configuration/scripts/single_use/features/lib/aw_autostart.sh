#!/bin/bash
# Autostart unit and the installed/running checks.
#
# Sourced by setup_activitywatch.sh; split out to keep aw_service.sh under the
# 250-line cap. Sourced rather than run, so it inherits the caller's
# strict mode and the variables defined above the source line.

# Function to setup autostart
setup_autostart() {
	echo ""
	echo "5. Setting Up Autostart..."
	echo "========================="

	local autostart_dir="$USER_HOME/.config/autostart"
	local desktop_file="$autostart_dir/activitywatch.desktop"
	local i3_config="$USER_HOME/.config/i3/config"

	# Method 1: XDG Autostart (works with most desktop environments)
	if [[ $EUID -eq 0 ]]; then
		sudo -u "$ACTUAL_USER" mkdir -p "$autostart_dir"
	else
		mkdir -p "$autostart_dir"
	fi

	# Create desktop file for autostart
	cat >"$desktop_file" <<EOF
[Desktop Entry]
Type=Application
Name=ActivityWatch
Comment=Automated time tracker
Exec=aw-qt
Icon=activitywatch
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
Terminal=false
Categories=Utility;
EOF

	# Set proper ownership if running as root
	if [[ $EUID -eq 0 ]]; then
		chown "$ACTUAL_USER:$ACTUAL_USER" "$desktop_file"
	fi

	echo "✓ Created XDG autostart entry: $desktop_file"

	# Method 2: i3 config autostart (specific to i3)
	if [[ -f $i3_config ]]; then
		# Check if autostart entry already exists
		if ! grep -q "aw-qt" "$i3_config"; then
			# Add autostart entry to i3 config
			if [[ $EUID -eq 0 ]]; then
				# Running as root
				sudo -u "$ACTUAL_USER" bash -c "cat <<'EOF' >> '$i3_config'

# Auto-start ActivityWatch
exec --no-startup-id aw-qt
EOF"
			else
				{
					printf '\n'
					printf '# Auto-start ActivityWatch\n'
					printf 'exec --no-startup-id aw-qt\n'
				} >>"$i3_config"
			fi

			echo "✓ Added ActivityWatch to i3 config autostart"
		else
			echo "✓ ActivityWatch autostart already exists in i3 config"
		fi
	else
		echo "! i3 config not found at $i3_config"
	fi
}

# Function to create i3blocks status script
create_i3blocks_status() {
	echo ""
	echo "6. Creating i3blocks Status Script..."
	echo "===================================="

	local i3blocks_dir="$USER_HOME/.config/i3blocks"
	local status_script="$i3blocks_dir/activitywatch_status.sh"

	# Create i3blocks directory if it doesn't exist
	if [[ $EUID -eq 0 ]]; then
		sudo -u "$ACTUAL_USER" mkdir -p "$i3blocks_dir"
	else
		mkdir -p "$i3blocks_dir"
	fi

	# Create the status script
	cat >"$status_script" <<'EOF'
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
EOF

	chmod +x "$status_script"

	# Set proper ownership if running as root
	if [[ $EUID -eq 0 ]]; then
		chown "$ACTUAL_USER:$ACTUAL_USER" "$status_script"
	fi

	echo "✓ Created i3blocks status script: $status_script"

	# Show configuration instructions
	echo ""
	echo "To add to your i3blocks config, add this block:"
	echo ""
	echo "[activitywatch]"
	echo "command=~/.config/i3blocks/activitywatch_status.sh"
	echo "interval=10"
	echo "color=#FFFFFF"
	echo ""
}

# Function to test the setup
test_setup() {
	echo ""
	echo "7. Testing Setup..."
	echo "=================="

	echo "Installation status:"
	if check_activitywatch_installed >/dev/null 2>&1; then
		echo "✓ ActivityWatch is installed"
	else
		echo "✗ ActivityWatch is not installed"
	fi

	echo "Running status:"
	if check_activitywatch_running >/dev/null 2>&1; then
		echo "✓ ActivityWatch is running"
	else
		echo "✗ ActivityWatch is not running"
	fi

	echo "Autostart files:"
	if [[ -f "$USER_HOME/.config/autostart/activitywatch.desktop" ]]; then
		echo "✓ XDG autostart file exists"
	else
		echo "✗ XDG autostart file missing"
	fi

	if [[ -f "$USER_HOME/.config/i3/config" ]] && grep -q "aw-qt" "$USER_HOME/.config/i3/config"; then
		echo "✓ i3 autostart configured"
	else
		echo "! i3 autostart may not be configured"
	fi

	echo "i3blocks status script:"
	if [[ -x "$USER_HOME/.config/i3blocks/activitywatch_status.sh" ]]; then
		echo "✓ i3blocks status script created"
		echo "Testing status script:"
		if [[ $EUID -eq 0 ]]; then
			sudo -u "$ACTUAL_USER" "$USER_HOME/.config/i3blocks/activitywatch_status.sh"
		else
			"$USER_HOME/.config/i3blocks/activitywatch_status.sh"
		fi
	else
		echo "✗ i3blocks status script missing"
	fi
}

# Function to show final instructions
show_instructions() {
	echo ""
	echo "=========================================="
	echo "ActivityWatch Setup Complete"
	echo "=========================================="
	echo "Summary:"
	echo "✓ ActivityWatch installation checked/completed"
	echo "✓ ActivityWatch startup configured"
	echo "✓ Autostart configured (XDG + i3)"
	echo "✓ i3blocks status script created"
	echo ""
	echo "Next steps:"
	echo "1. Add the i3blocks configuration to your config file:"
	echo "   ~/.config/i3blocks/config"
	echo ""
	echo "2. Reload i3 configuration:"
	echo "   Super+Shift+R"
	echo ""
	echo "3. ActivityWatch web interface should be available at:"
	echo "   http://localhost:5600"
	echo ""
	echo "4. Check system tray for ActivityWatch icon"
	echo ""
	echo "Files created:"
	echo "  ~/.config/autostart/activitywatch.desktop"
	echo "  ~/.config/i3blocks/activitywatch_status.sh"
	echo "  ~/.config/i3/config (modified)"
	echo ""
}
