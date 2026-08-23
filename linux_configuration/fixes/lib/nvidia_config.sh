#!/usr/bin/env bash
# Xorg, GCC-workaround and pyroveil configuration for nvidia_troubleshoot.sh.
#
# Sourced by the entry script, which owns the ordering; this file defines
# functions only, so sourcing it has no side effects.

# Function to backup file if it exists
backup_file() {
	local file="$1"
	if [[ -f $file ]]; then
		cp "$file" "$file.backup.$(date +%Y%m%d_%H%M%S)"
		echo "✓ Backed up $file"
	fi
}

# Function to add or update xorg.conf for RenderAccel
configure_xorg() {
	echo ""
	echo "2. Configuring Xorg Settings..."
	echo "==============================="

	# These paths default to the real locations and are overridden only by
	# the test harness. They are plain globals ASSIGNED here rather than read
	# from the environment, so the default has to live at the assignment --
	# an exported value alone would be overwritten on entry.
	XORG_CONF="${XORG_CONF:-/etc/X11/xorg.conf}"
	XORG_CONF_D="${XORG_CONF_D:-/etc/X11/xorg.conf.d}"
	NVIDIA_CONF="$XORG_CONF_D/20-nvidia.conf"

	# Create xorg.conf.d directory if it doesn't exist
	mkdir -p "$XORG_CONF_D"

	# Backup existing xorg.conf if it exists
	backup_file "$XORG_CONF"
	backup_file "$NVIDIA_CONF"

	# Create NVIDIA-specific configuration
	# NOTE: RenderAccel must be "true" (or omitted, since it defaults to true).
	# Setting it to "false" forces software rendering, causing Xorg to consume
	# 30%+ CPU on the desktop and making the system feel extremely sluggish.
	cat >"$NVIDIA_CONF" <<EOF
# NVIDIA configuration - hardware acceleration enabled
# Created by nvidia_troubleshoot.sh on $(date)
Section "Device"
    Identifier "NVIDIA Card"
    Driver "nvidia"
    Option "RenderAccel" "true"
EndSection
EOF

	echo "✓ Created $NVIDIA_CONF with RenderAccel enabled"
}

# Function to add GCC mismatch workaround
configure_gcc_workaround() {
	echo ""
	echo "3. Configuring GCC Mismatch Workaround..."
	echo "=========================================="

	local PROFILE_FILE="${PROFILE_FILE:-/etc/profile}"
	local timestamp
	timestamp=$(date)
	backup_file "$PROFILE_FILE"

	# Check if IGNORE_CC_MISMATCH is already set
	if ! grep -q "IGNORE_CC_MISMATCH" "$PROFILE_FILE"; then
		{
			printf '\n'
			printf '# NVIDIA GCC version mismatch workaround\n'
			printf '# Added by nvidia_troubleshoot.sh on %s\n' "$timestamp"
			printf 'export IGNORE_CC_MISMATCH=1\n'
		} >>"$PROFILE_FILE"
		echo "✓ Added IGNORE_CC_MISMATCH=1 to $PROFILE_FILE"
	else
		echo "✓ IGNORE_CC_MISMATCH already configured in $PROFILE_FILE"
	fi
}

# Function to install pyroveil for mesh shader issues
install_pyroveil() {
	echo ""
	echo "4. Pyroveil Setup for Mesh Shader Issues..."
	echo "==========================================="

	local user_home="${USER_HOME:-/home/$SUDO_USER}"
	local pyroveil_dir="$user_home/pyroveil"

	echo "Mesh shaders have poor support on NVIDIA drivers, causing issues in games"
	echo "like Final Fantasy VII Rebirth. Pyroveil can work around these problems."
	echo ""

	local install_pyroveil=true

	if [[ $INTERACTIVE_MODE == "true" ]]; then
		read -p "Would you like to install Pyroveil? (y/N): " -n 1 -r
		echo
		if [[ ! $REPLY =~ ^[Yy]$ ]]; then
			install_pyroveil=false
		fi
	else
		echo "Auto-installing Pyroveil (use --interactive to prompt)"
	fi

	if [[ $install_pyroveil == "true" ]]; then
		# Check for required dependencies
		local missing_deps=()

		for dep in git cmake ninja gcc; do
			if ! command -v "$dep" &>/dev/null; then
				missing_deps+=("$dep")
			fi
		done

		if [[ ${#missing_deps[@]} -gt 0 ]]; then
			echo "Missing dependencies: ${missing_deps[*]}"
			echo "Please install them first. On Arch Linux:"
			echo "pacman -S base-devel git cmake ninja"
			return 1
		fi

		# Clone and build pyroveil as the original user
		echo "Installing Pyroveil to $pyroveil_dir..."

		if [[ -d $pyroveil_dir ]]; then
			echo "Pyroveil directory already exists. Updating..."
			sudo -u "$SUDO_USER" bash -c "cd '$pyroveil_dir' && git pull"
		else
			sudo -u "$SUDO_USER" git clone https://github.com/HansKristian-Work/pyroveil.git "$pyroveil_dir"
		fi

		sudo -u "$SUDO_USER" bash -c "
            cd '$pyroveil_dir'
            git submodule update --init
            cmake . -Bbuild -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$user_home/.local
            ninja -C build install
        "

		echo "✓ Pyroveil installed successfully"
		echo ""
		echo "To use Pyroveil with games that have mesh shader issues:"
		echo "1. For Final Fantasy VII Rebirth:"
		echo "   PYROVEIL=1 PYROVEIL_CONFIG=$pyroveil_dir/hacks/ffvii-rebirth-nvidia/pyroveil.json %command%"
		echo ""
		echo "2. For Steam games, add to launch options:"
		echo "   PYROVEIL=1 PYROVEIL_CONFIG=/path/to/config/pyroveil.json %command%"
		echo ""
		echo "Available configs in: $pyroveil_dir/hacks/"

		# Create a helper script
		cat >"$user_home/run-with-pyroveil.sh" <<EOF
#!/bin/bash
# Helper script to run games with Pyroveil
# Usage: ./run-with-pyroveil.sh <config-name> <command>

PYROVEIL_DIR="$pyroveil_dir"

if [[ \$# -lt 2 ]]; then
    echo "Usage: \$0 <config-name> <command>"
    echo "Available configs:"
    ls "\$PYROVEIL_DIR/hacks/"
    exit 1
fi

CONFIG_NAME="\$1"
shift

export PYROVEIL=1
export PYROVEIL_CONFIG="\$PYROVEIL_DIR/hacks/\$CONFIG_NAME/pyroveil.json"

echo "Running with Pyroveil config: \$CONFIG_NAME"
echo "Config file: \$PYROVEIL_CONFIG"

exec "\$@"
EOF

		chown "$SUDO_USER:$SUDO_USER" "$user_home/run-with-pyroveil.sh"
		chmod +x "$user_home/run-with-pyroveil.sh"
		echo "✓ Created helper script: $user_home/run-with-pyroveil.sh"

	else
		echo "Skipping Pyroveil installation"
		echo "Note: You can manually install it later for mesh shader issues"
	fi
}
