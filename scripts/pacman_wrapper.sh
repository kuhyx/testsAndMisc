#!/bin/bash
# filepath: pacman-wrapper.sh
# A helpful wrapper for Arch Linux's pacman package manager

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

PACMAN_BIN="/usr/bin/pacman"

# Function to display help
function show_help() {
    echo -e "${BOLD}Pacman Wrapper Help${NC}"
    echo "This wrapper adds helpful features while preserving all pacman functionality."
    echo ""
    echo "Additional commands:"
    echo "  --help-wrapper    Show this help message"
}

# Function to display a message before executing
function display_operation() {
    case "$1" in
        -S|-Sy|-S\ *)
            echo -e "${BLUE}Installing packages...${NC}"
            ;;
        -Syu|-Syyu)
            echo -e "${BLUE}Updating system...${NC}"
            ;;
        -R|-Rs|-Rns|-R\ *)
            echo -e "${YELLOW}Removing packages...${NC}"
            ;;
        -Ss|-Ss\ *)
            echo -e "${CYAN}Searching for packages...${NC}"
            ;;
        -Q|-Qs|-Qi|-Ql|-Q\ *)
            echo -e "${CYAN}Querying package database...${NC}"
            ;;
        -U|-U\ *)
            echo -e "${BLUE}Installing local packages...${NC}"
            ;;
        -Scc)
            echo -e "${YELLOW}Cleaning package cache...${NC}"
            ;;
        *)
            echo -e "${CYAN}Executing pacman command...${NC}"
            ;;
    esac
}

# Check for wrapper-specific commands
if [[ "$1" == "--help-wrapper" ]]; then
    show_help
    exit 0
fi

# Display operation
display_operation "$1"

# Echo the command that's about to be executed
echo -e "${GREEN}Executing:${NC} $PACMAN_BIN $@"

# ...existing code...
# Record start time for statistics
start_time=$(date +%s)

# Execute the real pacman command
"$PACMAN_BIN" "$@"
exit_code=$?

# Record end time for statistics
end_time=$(date +%s)
duration=$((end_time - start_time))

# Display results
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}Command completed successfully in ${duration}s.${NC}"
else
    echo -e "${RED}Command failed with exit code ${exit_code}.${NC}"
fi

# Display some helpful tips depending on the operation
if [[ "$1" == "-S" || "$1" == "-S "* ]] && [ $exit_code -eq 0 ]; then
    echo -e "${CYAN}Tip:${NC} You may need to log out or restart to use some newly installed software."
fi

if [[ "$1" == "-Syu" || "$1" == "-Syyu" ]] && [ $exit_code -eq 0 ]; then
    echo -e "${CYAN}Tip:${NC} Consider restarting after major updates."
fi

exit $exit_code