#!/bin/bash
# https://wiki.archlinux.org/title/NVIDIA/Troubleshooting
# Script to disable NVIDIA GSP firmware and apply comprehensive NVIDIA fixes
# This addresses GSP issues, mesh shaders, OpenGL problems, and other NVIDIA issues

set -e # Exit on any error

# Source common library for shared functions
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

# Parse interactive/help arguments
parse_interactive_args "$@"
shift "$COMMON_ARGS_SHIFT"

# Check for sudo privileges
require_root "$@"

print_setup_header "NVIDIA Comprehensive Troubleshooter & GSP Disabler"

# Check if nvidia module is loaded
if ! lsmod | grep -q nvidia; then
	echo "Warning: NVIDIA module not currently loaded"
fi

# Create modprobe configuration directory if it doesn't exist
MODPROBE_DIR="/etc/modprobe.d"
CONFIG_FILE="$MODPROBE_DIR/nvidia-gsp-disable.conf"

echo ""
echo "1. Configuring GSP Firmware Disable..."
echo "======================================"
mkdir -p "$MODPROBE_DIR"

# Create the configuration file
cat >"$CONFIG_FILE" <<EOF
# Disable NVIDIA GSP firmware to prevent Vulkan failures and crashes
# Created by nvidia_troubleshoot.sh on $(date)
options nvidia NVreg_EnableGpuFirmware=0
EOF

echo "✓ Configuration written to: $CONFIG_FILE"

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

	XORG_CONF="/etc/X11/xorg.conf"
	XORG_CONF_D="/etc/X11/xorg.conf.d"
	NVIDIA_CONF="$XORG_CONF_D/20-nvidia.conf"

	# Create xorg.conf.d directory if it doesn't exist
	mkdir -p "$XORG_CONF_D"

	# Backup existing xorg.conf if it exists
	backup_file "$XORG_CONF"
	backup_file "$NVIDIA_CONF"

	# Create NVIDIA-specific configuration
	cat >"$NVIDIA_CONF" <<EOF
# NVIDIA configuration with RenderAccel disabled
# Created by nvidia_troubleshoot.sh on $(date)
Section "Device"
    Identifier "NVIDIA Card"
    Driver "nvidia"
    Option "RenderAccel" "false"
EndSection
EOF

	echo "✓ Created $NVIDIA_CONF with RenderAccel disabled"
}

# Function to add GCC mismatch workaround
configure_gcc_workaround() {
	echo ""
	echo "3. Configuring GCC Mismatch Workaround..."
	echo "=========================================="

	local PROFILE_FILE="/etc/profile"
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

	local user_home="/home/$SUDO_USER"
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

# Function to check for kernel parameter modifications
suggest_kernel_params() {
	echo ""
	echo "5. Kernel Parameter Recommendations..."
	echo "====================================="

	echo "NVIDIA Driver Issues and Recommended Kernel Parameters:"
	echo ""
	echo "A) For 'conflicting memory type' or 'failed to allocate primary buffer' errors"
	echo "   (especially with nvidia-96xx drivers):"
	echo "   → Add 'nopat' to kernel parameters"
	echo ""
	echo "B) For OpenGL visual glitches, hangs, and errors with modern CPUs:"
	echo "   → Consider disabling micro-op cache in BIOS settings"
	echo "   → This affects Intel Sandy Bridge (2011+) and AMD Zen (2017+) CPUs"
	echo "   → Helps with severe graphical glitches in Xwayland applications"
	echo "   → Note: Disabling micro-op cache reduces CPU performance"
	echo ""
	echo "To add kernel parameters:"
	echo "1. Edit /etc/default/grub"
	echo "2. Add parameters to GRUB_CMDLINE_LINUX_DEFAULT"
	echo "3. Run: grub-mkconfig -o /boot/grub/grub.cfg"
	echo "4. Reboot"
	echo ""
	echo "Example GRUB_CMDLINE_LINUX_DEFAULT line:"
	echo 'GRUB_CMDLINE_LINUX_DEFAULT="quiet nopat"'

	# Check current CPU for micro-op cache relevance
	echo ""
	echo "CPU Information (for micro-op cache consideration):"
	if command -v lscpu &>/dev/null; then
		local cpu_info
		cpu_info=$(lscpu | grep "Model name" | cut -d: -f2 | xargs)
		echo "Current CPU: $cpu_info"

		if echo "$cpu_info" | grep -qi "intel"; then
			echo "→ Intel CPU detected. Sandy Bridge (2011) and later have micro-op cache"
		elif echo "$cpu_info" | grep -qi "amd"; then
			echo "→ AMD CPU detected. Zen (2017) and later have micro-op cache"
		fi
	fi
}

# Function to suggest desktop environment settings
suggest_desktop_settings() {
	echo ""
	echo "6. Desktop Environment Recommendations..."
	echo "========================================"

	echo "For fullscreen application freezing/crashing issues:"
	echo ""
	echo "Enable Display Compositing and Direct fullscreen rendering:"
	echo ""
	echo "• KDE Plasma:"
	echo "  System Settings → Display and Monitor → Compositor"
	echo "  → Enable compositor + Enable direct rendering for fullscreen windows"
	echo ""
	echo "• GNOME:"
	echo "  Use Extensions or dconf-editor to enable compositing features"
	echo ""
	echo "• XFCE:"
	echo "  Settings → Window Manager Tweaks → Compositor"
	echo "  → Enable display compositing"
	echo ""
	echo "• Cinnamon:"
	echo "  System Settings → Effects → Enable desktop effects"

	# Detect current desktop environment
	if [[ -n $XDG_CURRENT_DESKTOP ]]; then
		echo ""
		echo "Detected desktop environment: $XDG_CURRENT_DESKTOP"
	fi
}

# Apply all configurations
configure_xorg
configure_gcc_workaround
install_pyroveil

# Regenerate initramfs
echo ""
echo "7. Regenerating Initramfs..."
echo "============================"
if command -v mkinitcpio &>/dev/null; then
	mkinitcpio -P
	echo "✓ Initramfs regenerated with mkinitcpio"
elif command -v dracut &>/dev/null; then
	dracut --force
	echo "✓ Initramfs regenerated with dracut"
else
	echo "Warning: Could not find mkinitcpio or dracut. You may need to manually regenerate initramfs."
fi

# Display all recommendations
suggest_kernel_params
suggest_desktop_settings

echo ""
echo "=========================================="
echo "NVIDIA Troubleshooting Summary"
echo "=========================================="
echo "Applied Configurations:"
echo "✓ GSP firmware disabled"
echo "✓ RenderAccel disabled in Xorg configuration"
echo "✓ GCC version mismatch workaround added"
if [[ -d "/home/$SUDO_USER/pyroveil" ]]; then
	echo "✓ Pyroveil installed for mesh shader issues"
fi
echo "✓ Initramfs regenerated"
echo ""
echo "Manual Configurations Needed:"
echo "• Consider BIOS micro-op cache settings for OpenGL issues"
echo "• Configure desktop environment compositing settings"
echo "• Add kernel parameters if needed (nopat for memory issues)"
echo ""
echo "IMPORTANT: You must reboot for changes to take effect!"
echo "After reboot, verify GSP with: cat /proc/driver/nvidia/params | grep EnableGpuFirmware"
