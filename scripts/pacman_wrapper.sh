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

# Function to check if user is trying to install specific packages that require confirmation
function check_for_steam() {
    # List of packages that require confirmation
    local restricted_packages=("steam" "freetube-bin")
    
    # Check if the command is an installation command
    if [[ "$1" == "-S" || "$1" == "-Sy" || "$1" == "-Syu" || "$1" == "-Syyu" ]]; then
        # Check all arguments
        for arg in "$@"; do
            # Check if argument matches any restricted package
            for package in "${restricted_packages[@]}"; do
                if [[ "$arg" == "$package" ]]; then
                    return 0  # Restricted package found
                fi
            done
        done
    fi
    return 1  # No restricted package found
}

# Function to prompt for a generated random string
function prompt_for_random_string() {
    echo -e "${YELLOW}WARNING: You are trying to install Steam.${NC}"
    
    # Generate a random 32-character string
    random_string=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 32)
    
    echo -e "${YELLOW}To confirm installation, please type (not copy/paste) this exact string:${NC}"
    echo -e "${YELLOW}The string will be displayed for 10 seconds only.${NC}"
    echo -e "${YELLOW}Get ready to type...${NC}"
    sleep 2
    
    # Display string character by character with spaces to prevent easy copying
    echo -e "${CYAN}"
    for ((i=0; i<${#random_string}; i++)); do
        # Add random spacing and line breaks to make copying harder
        if ((i % 8 == 0)) && ((i > 0)); then
            echo ""
        fi
        printf " %c " "${random_string:$i:1}"
    done
    echo -e "${NC}"
    
    # Set a timer to clear the string
    (sleep 10 && echo -e "\033[2J\033[H" && echo -e "${YELLOW}Time's up! Enter the string you memorized:${NC}") &
    timer_pid=$!
    
    echo -e "${YELLOW}Enter the string shown above:${NC}"
    read -r user_input
    
    # Kill the timer if it's still running
    kill $timer_pid &>/dev/null
    
    if [[ "$user_input" == "$random_string" ]]; then
        echo -e "${GREEN}String matched. Proceeding with installation...${NC}"
        return 0
    else
        echo -e "${RED}Error: String did not match. Steam installation aborted.${NC}"
        return 1
    fi
}

# Check for wrapper-specific commands
if [[ "$1" == "--help-wrapper" ]]; then
    show_help
    exit 0
fi

# Check if trying to install steam
if check_for_steam "$@"; then
    prompt_for_random_string
    if [[ $? -ne 0 ]]; then
        exit 1
    fi
fi

# Display operation
display_operation "$1"

# Echo the command that's about to be executed
echo -e "${GREEN}Executing:${NC} $PACMAN_BIN $@"

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