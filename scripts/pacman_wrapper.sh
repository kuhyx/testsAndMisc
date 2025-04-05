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

# Define paths for both pacman and pacman.orig
PACMAN_BIN="/usr/bin/pacman"
PACMAN_ORIG_BIN="/usr/bin/pacman.orig.real"

# Detect if script is being called as pacman.orig
SCRIPT_NAME=$(basename "$0")
if [[ "$SCRIPT_NAME" == "pacman.orig" ]]; then
    IS_PACMAN_ORIG=true
else
    IS_PACMAN_ORIG=false
fi

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
    local restricted_packages=("steam" "freetube-bin" "seamonkey-bin" "seamonkey" "google-chrome" "mirosoft-edge-stable-bin" "opera" "slimjet" "vivaldi" "yandex-browser" "min-browser-bin" "vieb-bin")
    
    # Check if the command is an installation command
    if [[ "$1" == "-S" || "$1" == "-Sy" || "$1" == "-Syu" || "$1" == "-Syyu" || "$1" == "-U" ]]; then
        # Check all arguments
        for arg in "$@"; do
            # Fix the comment that was accidentally merged with code
            # Check if argument matches any restricted package
            for package in "${restricted_packages[@]}"; do
                if [[ "$arg" == "$package" ]]; then
                    return 0  # Restricted package found
                fi
                
                # Check if the argument is a path containing the restricted package
                if [[ "$arg" == *"$package"*".pkg.tar."* ]]; then
                    return 0  # Restricted package found in path
                fi
            done
        done
    fi
    return 1  # No restricted package found
}

# Function to prompt for solving a math problem
function prompt_for_math_solution() {
    echo -e "${YELLOW}WARNING: You are trying to install a restricted package.${NC}"
    
    # Generate a random math problem with a random number of operations
    # Define possible operations
    operations=('+' '-' '*' '/')
    
    # Decide on the number of operations (2-4)
    num_operations=$((RANDOM % 4 + 3))
    
    # Start with a random number
    current_value=$((RANDOM % 50 + 10))
    problem="$current_value"
    
    # Build the problem step by step
    for ((i=1; i<=num_operations; i++)); do
        # Choose a random operation
        op=${operations[$((RANDOM % ${#operations[@]}))]}
        
        # Generate the next operand based on the operation
        case $op in
            '+') 
                next_num=$((RANDOM % 50 + 5))
                ;;
            '-') 
                next_num=$((RANDOM % 50 + 5))
                ;;
            '*') 
                next_num=$((RANDOM % 10 + 2))  # Smaller numbers for multiplication
                ;;
            '/') 
                # For division, ensure it's clean (no remainder)
                next_num=$((RANDOM % 5 + 2))
                current_value=$((next_num * (RANDOM % 10 + 1)))
                problem="$current_value"
                i=1  # Reset counter to ensure we still get the right number of operations
                continue
                ;;
        esac
        
        problem="$problem $op $next_num"
        
        # Update current value for next iteration
        case $op in
            '+') current_value=$((current_value + next_num)) ;;
            '-') current_value=$((current_value - next_num)) ;;
            '*') current_value=$((current_value * next_num)) ;;
            '/') current_value=$((current_value / next_num)) ;;
        esac
    done
    
    # Calculate solution using bash's evaluation
    solution=$(eval "echo \$(($problem))")
    
    echo -e "${YELLOW}To confirm installation, please solve this math problem:${NC}"
    echo -e "${CYAN}$problem = ?${NC}"
    
    echo -e "${YELLOW}Enter your answer:${NC}"
    read -r user_input
    
    # Trim whitespaces from user input
    user_input=$(echo $user_input | xargs)
    
    if [[ "$user_input" == "$solution" ]]; then
        echo -e "${GREEN}Correct! Proceeding with installation...${NC}"
        return 0
    else
        echo -e "${RED}Incorrect answer. Installation aborted. The correct answer was $solution.${NC}"
        return 1
    fi
}

# Check for wrapper-specific commands
if [[ "$1" == "--help-wrapper" ]]; then
    show_help
    exit 0
fi

# Check if trying to install restricted packages
if check_for_steam "$@"; then
    prompt_for_math_solution
    if [[ $? -ne 0 ]]; then
        exit 1
    fi
fi

# Display operation
display_operation "$1"

# Determine which binary to use
if [[ "$IS_PACMAN_ORIG" == true ]]; then
    echo -e "${GREEN}Executing via pacman.orig:${NC} $PACMAN_ORIG_BIN $@"
    EXEC_BIN="$PACMAN_ORIG_BIN"
else
    echo -e "${GREEN}Executing:${NC} $PACMAN_BIN $@"
    EXEC_BIN="$PACMAN_BIN"
fi

# Record start time for statistics
start_time=$(date +%s)

# Execute the real pacman command
"$EXEC_BIN" "$@"
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