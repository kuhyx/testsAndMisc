#!/bin/bash
# filepath: /home/kuhy/linux-configuration/scripts/install_pacman_wrapper.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Script locations
WRAPPER_SOURCE="$(dirname "$0")/pacman_wrapper.sh"
INSTALL_DIR="/usr/local/bin"
WRAPPER_DEST="${INSTALL_DIR}/pacman_wrapper"

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root${NC}"
  exit 1
fi

# Check if the wrapper script exists
if [ ! -f "$WRAPPER_SOURCE" ]; then
  echo -e "${RED}Error: Wrapper script not found at ${WRAPPER_SOURCE}${NC}"
  exit 1
fi

echo -e "${CYAN}Installing pacman wrapper...${NC}"

# Install the wrapper script
echo -e "${BLUE}Copying wrapper script to ${WRAPPER_DEST}...${NC}"
cp "$WRAPPER_SOURCE" "$WRAPPER_DEST"
chmod +x "$WRAPPER_DEST"

# Choose installation method
echo -e "${YELLOW}Select installation method:${NC}"
echo "1. Create alias in /etc/profile.d/ (recommended)"
echo "2. Create symbolic link (advanced)"
read -p "Enter choice (1-2): " choice

case $choice in
  1)
    # Create an alias file in /etc/profile.d/
    echo -e "${BLUE}Creating system-wide alias...${NC}"
    cat > /etc/profile.d/pacman-wrapper.sh << EOF
#!/bin/bash
alias pacman='$WRAPPER_DEST'
EOF
    chmod +x /etc/profile.d/pacman-wrapper.sh
    echo -e "${GREEN}Installation complete!${NC}"
    echo -e "${YELLOW}Note:${NC} You need to log out and log back in for the alias to take effect."
    echo -e "Alternatively, run: ${CYAN}source /etc/profile.d/pacman-wrapper.sh${NC}"
    ;;
  2)
    # Create a symbolic link
    echo -e "${YELLOW}Warning: This method replaces the pacman command directly.${NC}"
    echo -e "Make sure your wrapper script is fully functional to avoid system issues."
    read -p "Are you sure you want to continue? (y/N): " confirm
    if [[ "$confirm" == [yY] || "$confirm" == [yY][eE][sS] ]]; then
      # Backup original pacman
      if [ ! -f "/usr/bin/pacman.orig" ]; then
        echo -e "${BLUE}Backing up original pacman to /usr/bin/pacman.orig...${NC}"
        cp /usr/bin/pacman /usr/bin/pacman.orig
      fi
      
      # Update the PACMAN_BIN variable in the wrapper to point to the original
      sed -i 's|PACMAN_BIN="\/usr\/bin\/pacman"|PACMAN_BIN="\/usr\/bin\/pacman.orig"|g' "$WRAPPER_DEST"
      
      # Create symbolic link
      echo -e "${BLUE}Creating symbolic link...${NC}"
      ln -sf "$WRAPPER_DEST" /usr/bin/pacman
      echo -e "${GREEN}Installation complete!${NC}"
      echo -e "Pacman is now wrapped. The original pacman is available at ${CYAN}/usr/bin/pacman.orig${NC}"
    else
      echo -e "${YELLOW}Installation cancelled.${NC}"
      exit 0
    fi
    ;;
  *)
    echo -e "${RED}Invalid choice. Installation cancelled.${NC}"
    exit 1
    ;;
esac

# Create uninstaller
echo -e "${BLUE}Creating uninstaller...${NC}"
cat > "${INSTALL_DIR}/uninstall_pacman_wrapper.sh" << EOF
#!/bin/bash
# Uninstall script for pacman wrapper

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

if [ "\$EUID" -ne 0 ]; then
  echo -e "\${RED}Please run as root\${NC}"
  exit 1
fi

echo -e "\${BLUE}Uninstalling pacman wrapper...\${NC}"

# Remove alias if exists
if [ -f /etc/profile.d/pacman-wrapper.sh ]; then
  echo -e "\${YELLOW}Removing alias file...\${NC}"
  rm /etc/profile.d/pacman-wrapper.sh
fi

# Restore original pacman if needed
if [ -L /usr/bin/pacman ] && [ -f /usr/bin/pacman.orig ]; then
  echo -e "\${YELLOW}Restoring original pacman...\${NC}"
  rm /usr/bin/pacman
  cp /usr/bin/pacman.orig /usr/bin/pacman
fi

# Remove wrapper
if [ -f "${WRAPPER_DEST}" ]; then
  echo -e "\${YELLOW}Removing wrapper script...\${NC}"
  rm "${WRAPPER_DEST}"
fi

echo -e "\${GREEN}Pacman wrapper has been uninstalled.\${NC}"
echo -e "\${YELLOW}Note:\${NC} You may need to log out and log back in for changes to take effect."

# Self-destruct
rm "\$0"
EOF

chmod +x "${INSTALL_DIR}/uninstall_pacman_wrapper.sh"

echo -e "${CYAN}To uninstall, run: ${BOLD}sudo ${INSTALL_DIR}/uninstall_pacman_wrapper.sh${NC}"
echo -e "${GREEN}Thank you for installing the pacman wrapper!${NC}"