#!/usr/bin/env bash
# sudoers, lightdm autologin, i3 session and misc configuration writers.
#
# Sourced by setup_passwordless_system.sh, which owns the ordering and the
# safety checks; this file defines functions only.

# Function to configure passwordless sudo
configure_passwordless_sudo() {
  echo ""
  echo "1. Configuring Passwordless Sudo..."
  echo "=================================="

  local sudoers_file="/etc/sudoers.d/99-passwordless-${TARGET_USER}"

  # Create sudoers configuration for passwordless access
  cat > "$sudoers_file" << EOF
# Passwordless sudo configuration for user: ${TARGET_USER}
# Created by setup_passwordless_system.sh on $(date)
# WARNING: This allows the user to run any command without password

# Allow user to run all commands without password
${TARGET_USER} ALL=(ALL) NOPASSWD: ALL

# Ensure user can run sudo without TTY (useful for scripts)
Defaults:${TARGET_USER} !requiretty

# Keep environment variables for user convenience
Defaults:${TARGET_USER} env_keep += "HOME PATH DISPLAY XAUTHORITY"
EOF

  # Set proper permissions for sudoers file
  chmod 440 "$sudoers_file"

  # Verify the sudoers file syntax
  if visudo -c -f "$sudoers_file"; then
    echo "✓ Passwordless sudo configured for user: $TARGET_USER"
    echo "✓ Sudoers file created: $sudoers_file"
  else
    echo "✗ Error: Invalid sudoers syntax. Removing file for safety."
    rm -f "$sudoers_file"
    exit 1
  fi
}

# Function to configure lightdm auto-login
configure_lightdm_autologin() {
  echo ""
  echo "2. Configuring LightDM Auto-Login..."
  echo "==================================="

  local lightdm_conf="/etc/lightdm/lightdm.conf"
  local lightdm_conf_dir="/etc/lightdm/lightdm.conf.d"
  local custom_conf="$lightdm_conf_dir/50-autologin.conf"

  # Create lightdm config directory if it doesn't exist
  mkdir -p "$lightdm_conf_dir"

  # Backup existing lightdm configuration
  backup_file "$lightdm_conf"

  # Check if lightdm is installed
  if ! command -v lightdm &> /dev/null; then
    echo "Warning: LightDM not found. Installing lightdm..."
    pacman -S --noconfirm lightdm lightdm-gtk-greeter
  fi

  # Method 1: Update the main lightdm.conf file directly
  sed -i "/^#autologin-user=/c\autologin-user=${TARGET_USER}" "$lightdm_conf"
  sed -i "/^#autologin-user-timeout=/c\autologin-user-timeout=0" "$lightdm_conf"
  sed -i "/^#autologin-session=/c\autologin-session=i3" "$lightdm_conf"
  sed -i "/^#autologin-in-background=/c\autologin-in-background=false" "$lightdm_conf"

  # Also set user-session to i3 as fallback
  sed -i "/^#user-session=/c\user-session=i3" "$lightdm_conf"

  echo "✓ LightDM auto-login configured in main config file"

  # Method 2: Also create the separate config file for redundancy
  cat > "$custom_conf" << EOF
# LightDM Auto-Login Configuration
# Created by setup_passwordless_system.sh on $(date)

[Seat:*]
# Enable auto-login
autologin-user=${TARGET_USER}
autologin-user-timeout=0
autologin-session=i3

# Disable user switching and guest account
allow-user-switching=false
allow-guest=false

# Set session defaults
user-session=i3
greeter-session=lightdm-gtk-greeter

# Disable screen lock timeout during login
autologin-in-background=false
EOF

  echo "✓ LightDM auto-login also configured in separate config file: $custom_conf"

  # Enable lightdm service
  systemctl enable lightdm.service
  echo "✓ LightDM service enabled"

  # Restart lightdm to apply changes only if --logout flag is provided
  if [[ $ALLOW_LOGOUT == true ]]; then
    echo "Restarting LightDM to apply auto-login settings..."
    systemctl restart lightdm.service
    echo "✓ LightDM restarted"
  else
    echo "✓ LightDM configuration complete (restart lightdm or reboot to activate auto-login)"
  fi
}

# Function to configure i3 session
configure_i3_session() {
  echo ""
  echo "3. Configuring i3 Session..."
  echo "==========================="

  local xsessions_dir="/usr/share/xsessions"
  local i3_desktop="$xsessions_dir/i3.desktop"

  # Create xsessions directory if it doesn't exist
  mkdir -p "$xsessions_dir"

  # Check if i3.desktop exists, create if not
  if [[ ! -f $i3_desktop ]]; then
    cat > "$i3_desktop" << EOF
[Desktop Entry]
Name=i3
Comment=improved dynamic tiling window manager
Exec=i3
TryExec=i3
Type=Application
X-LightDM-DesktopName=i3
DesktopNames=i3
Keywords=tiling;wm;windowmanager;window;manager;
EOF
    echo "✓ Created i3 desktop session file: $i3_desktop"
  else
    echo "✓ i3 desktop session file already exists"
  fi

  # Ensure user has i3 config directory
  local user_home="/home/${TARGET_USER}"
  local i3_config_dir="$user_home/.config/i3"

  if [[ ! -d $i3_config_dir ]]; then
    sudo -u "$TARGET_USER" mkdir -p "$i3_config_dir"
    echo "✓ Created i3 config directory for user: $TARGET_USER"
  fi
}

# Function to configure additional auto-login settings
configure_additional_settings() {
  echo ""
  echo "4. Configuring Additional Settings..."
  echo "===================================="

  # Add user to autologin group if it exists
  if getent group autologin &> /dev/null; then
    usermod -a -G autologin "$TARGET_USER"
    echo "✓ Added $TARGET_USER to autologin group"
  else
    # Create autologin group
    groupadd -r autologin
    usermod -a -G autologin "$TARGET_USER"
    echo "✓ Created autologin group and added $TARGET_USER"
  fi

  # Configure pam for auto-login (if needed)
  local pam_lightdm="/etc/pam.d/lightdm-autologin"
  if [[ ! -f $pam_lightdm ]]; then
    cat > "$pam_lightdm" << EOF
#%PAM-1.0
# LightDM auto-login PAM configuration
# Created by setup_passwordless_system.sh on $(date)

auth        required    pam_unix.so nullok
auth        optional    pam_permit.so
auth        optional    pam_gnome_keyring.so
account     include     system-local-login
password    include     system-local-login
session     include     system-local-login
session     optional    pam_gnome_keyring.so auto_start
EOF
    echo "✓ Created PAM configuration for auto-login"
  fi
}
