#!/bin/bash
# https://wiki.archlinux.org/title/NVIDIA/Troubleshooting
# Script to disable NVIDIA GSP firmware and apply comprehensive NVIDIA fixes
# This addresses GSP issues, mesh shaders, OpenGL problems, and other NVIDIA issues

set -e # Exit on any error

# shellcheck source=lib/nvidia_config.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/nvidia_config.sh"

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
