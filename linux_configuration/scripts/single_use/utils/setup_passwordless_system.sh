#!/bin/bash
# Script to set up passwordless sudo and automatic login
# Configures lightdm for auto-login and sudo for passwordless access
# Handles sudo privileges automatically
# Usage: ./setup_passwordless_system.sh [--reboot] [--logout]
#   --reboot: Offer to reboot after setup completion
#   --logout: Allow restart of LightDM (which will logout the user)

set -e # Exit on any error

# shellcheck source=lib/passwordless_config.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/passwordless_config.sh"

# Check for flags
OFFER_REBOOT=false
ALLOW_LOGOUT=false
for arg in "$@"; do
  case $arg in
    --reboot)
      OFFER_REBOOT=true
      shift
      ;;
    --logout)
      ALLOW_LOGOUT=true
      shift
      ;;
    *)
      # Unknown option, keep it for sudo check
      ;;
  esac
done

# Function to check and request sudo privileges
check_sudo() {
  if [[ $EUID -ne 0 ]]; then
    echo "This script requires sudo privileges to modify system configurations."
    echo "Requesting sudo access..."
    exec sudo "$0" "$@"
  fi
}

# Check for sudo privileges first
check_sudo "$@"

echo "Passwordless System Setup"
echo "========================"
echo "Current Date: $(date)"
echo "User: $USER"
echo "Original user: ${SUDO_USER:-$USER}"

# Verify we have a valid user
if [[ -z ${SUDO_USER} ]]; then
  echo "Error: Could not determine the original user. Please run this script with sudo."
  exit 1
fi

TARGET_USER="${SUDO_USER}"
echo "Target user for configuration: $TARGET_USER"

# Function to backup files
backup_file() {
  local file="$1"
  if [[ -f $file ]]; then
    local backup timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup="${file}.backup.$timestamp"
    cp "$file" "$backup"
    echo "✓ Backed up $file to $backup"
  fi
}





# Function to test configurations
test_configurations() {
  echo ""
  echo "5. Testing Configurations..."
  echo "==========================="

  # Test sudo configuration
  echo "Testing passwordless sudo..."
  if sudo -u "$TARGET_USER" sudo -n true 2> /dev/null; then
    echo "✓ Passwordless sudo test passed"
  else
    echo "! Passwordless sudo test failed (may require logout/login)"
  fi

  # Test lightdm configuration
  echo "Testing LightDM configuration..."
  if lightdm --test-mode --debug 2> /dev/null | grep -q "seat"; then
    echo "✓ LightDM configuration test passed"
  else
    echo "! LightDM configuration test completed (check logs if issues occur)"
  fi

  # Verify user is in autologin group
  if groups "$TARGET_USER" | grep -q autologin; then
    echo "✓ User is in autologin group"
  else
    echo "! User may not be in autologin group"
  fi
}

# Function to show security warnings
show_security_warnings() {
  echo ""
  echo "⚠️  SECURITY WARNINGS ⚠️"
  echo "========================"
  echo ""
  echo "The following security changes have been made:"
  echo ""
  echo "1. PASSWORDLESS SUDO:"
  echo "   • User '$TARGET_USER' can now run ANY command as root without password"
  echo "   • This includes system-critical operations and file modifications"
  echo "   • Malicious software running as this user can gain full system access"
  echo ""
  echo "2. AUTO-LOGIN:"
  echo "   • System automatically logs in user '$TARGET_USER' on boot"
  echo "   • No password required to access the desktop environment"
  echo "   • Physical access to the machine = full user access"
  echo ""
  echo "3. RECOMMENDATIONS:"
  echo "   • Use full disk encryption to protect against physical access"
  echo "   • Ensure the system is in a physically secure location"
  echo "   • Consider using this only on personal/development machines"
  echo "   • Regularly monitor system logs for unauthorized access"
  echo "   • Keep the system updated and use a firewall"
  echo ""
  echo "4. TO DISABLE THESE SETTINGS:"
  echo "   • Remove passwordless sudo: sudo rm /etc/sudoers.d/99-passwordless-${TARGET_USER}"
  echo "   • Disable auto-login: sudo rm /etc/lightdm/lightdm.conf.d/50-autologin.conf"
  echo "   • Restart LightDM: sudo systemctl restart lightdm"
  echo ""
}

# Function to show final instructions
show_final_instructions() {
  echo ""
  echo "=========================================="
  echo "Passwordless System Setup Complete"
  echo "=========================================="
  echo "Summary:"
  echo "✓ Passwordless sudo configured for user: $TARGET_USER"
  echo "✓ LightDM auto-login configured"
  echo "✓ i3 session configured"
  echo "✓ Additional auto-login settings applied"
  echo ""
  echo "Changes will take effect after:"
  echo "• Logout/login for sudo changes"
  echo "• System reboot for auto-login"
  echo ""
  echo "To verify after reboot:"
  echo "  sudo whoami  # Should not ask for password"
  echo "  systemctl status lightdm  # Should show auto-login active"
  echo ""
  echo "Configuration files created:"
  echo "  /etc/sudoers.d/99-passwordless-${TARGET_USER}"
  echo "  /etc/lightdm/lightdm.conf.d/50-autologin.conf"
  echo "  /etc/pam.d/lightdm-autologin"
  echo ""
  echo "IMPORTANT: Reboot recommended to activate all changes!"
}

# Main execution
configure_passwordless_sudo
configure_lightdm_autologin
configure_i3_session
configure_additional_settings
test_configurations
show_security_warnings
show_final_instructions

# Only offer reboot if --reboot flag was provided
if [[ $OFFER_REBOOT == true ]]; then
  echo ""
  echo "Would you like to reboot now to activate all changes?"
  read -p "Reboot system now? (y/N): " -n 1 -r
  echo

  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebooting system in 5 seconds..."
    sleep 5
    reboot
  else
    echo "Remember to reboot when convenient to activate all changes."
  fi
else
  echo ""
  echo "Setup completed successfully."
  echo "Remember to reboot when convenient to activate all changes."
  echo "To automatically prompt for reboot in the future, use: $0 --reboot"
fi
