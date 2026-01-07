#!/bin/bash
# filepath: /home/kuhy/linux-configuration/scripts/install_pacman_wrapper.sh

# Auto-sudo functionality
if [ "$EUID" -ne 0 ]; then
  echo "Executing with sudo..."
  sudo "$0" "$@"
  exit $?
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script locations
WRAPPER_SOURCE="$(dirname "$0")/pacman_wrapper.sh"
WORDS_SOURCE="$(dirname "$0")/words.txt"
BLOCKED_SOURCE="$(dirname "$0")/pacman_blocked_keywords.txt"
WHITELIST_SOURCE="$(dirname "$0")/pacman_whitelist.txt"
GREYLIST_SOURCE="$(dirname "$0")/pacman_greylist.txt"
INSTALL_DIR="/usr/local/bin"
WRAPPER_DEST="${INSTALL_DIR}/pacman_wrapper"
WORDS_DEST="${INSTALL_DIR}/words.txt"
BLOCKED_DEST="${INSTALL_DIR}/pacman_blocked_keywords.txt"
WHITELIST_DEST="${INSTALL_DIR}/pacman_whitelist.txt"
GREYLIST_DEST="${INSTALL_DIR}/pacman_greylist.txt"
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
cp "$WORDS_SOURCE" "$WORDS_DEST"
if [ -f "$BLOCKED_SOURCE" ]; then
  cp "$BLOCKED_SOURCE" "$BLOCKED_DEST"
else
  echo -e "${YELLOW}Warning:${NC} Missing blocked keywords source at ${BLOCKED_SOURCE}${NC}"
fi

if [ -f "$WHITELIST_SOURCE" ]; then
  cp "$WHITELIST_SOURCE" "$WHITELIST_DEST"
else
  echo -e "${YELLOW}Warning:${NC} Missing whitelist source at ${WHITELIST_SOURCE}${NC}"
fi

if [ -f "$GREYLIST_SOURCE" ]; then
  cp "$GREYLIST_SOURCE" "$GREYLIST_DEST"
else
  echo -e "${YELLOW}Warning:${NC} Missing greylist source at ${GREYLIST_SOURCE}${NC}"
fi
chmod +x "$WRAPPER_DEST"
chmod 644 "$WORDS_DEST" "$BLOCKED_DEST" "$WHITELIST_DEST" "$GREYLIST_DEST" 2> /dev/null || true

# Automatically use symbolic link installation method
echo -e "${YELLOW}Installing using symbolic link method...${NC}"

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
