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

# Function to prompt for solving a math problem
function prompt_for_math_solution() {
    echo -e "${YELLOW}WARNING: You are trying to install a restricted package.${NC}"
    
    # Generate a random math problem
    operation_type=$((RANDOM % 5 + 1))
    
    case $operation_type in
        1) # Addition
            num1=$((RANDOM % 90 + 10))
            num2=$((RANDOM % 90 + 10))
            problem="$num1 + $num2"
            solution=$((num1 + num2))
            ;;
        2) # Subtraction
            num1=$((RANDOM % 90 + 10))
            num2=$((RANDOM % 90 + 10))
            # Make sure num1 > num2 for positive result
            if [[ $num1 -lt $num2 ]]; then
                temp=$num1
                num1=$num2
                num2=$temp
            fi
            problem="$num1 - $num2"
            solution=$((num1 - num2))
            ;;
        3) # Multiplication
            num1=$((RANDOM % 15 + 2))
            num2=$((RANDOM % 15 + 2))
            problem="$num1 * $num2"
            solution=$((num1 * num2))
            ;;
        4) # Division (with whole number result)
            num2=$((RANDOM % 10 + 2))
            num1=$((num2 * (RANDOM % 10 + 1)))
            problem="$num1 / $num2"
            solution=$((num1 / num2))
            ;;
        5) # Mixed with parentheses
            num1=$((RANDOM % 20 + 5))
            num2=$((RANDOM % 10 + 2))
            num3=$((RANDOM % 20 + 5))
            
            # Random sub-operation
            sub_op=$((RANDOM % 3 + 1))
            
            case $sub_op in
                1)
                    problem="($num1 + $num2) * $num3"
                    solution=$(((num1 + num2) * num3))
                    ;;
                2)
                    if [[ $num1 -lt $num2 ]]; then
                        temp=$num1
                        num1=$num2
                        num2=$temp
                    fi
                    problem="($num1 - $num2) * $num3"
                    solution=$(((num1 - num2) * num3))
                    ;;
                3)
                    problem="$num1 * ($num2 + $num3)"
                    solution=$((num1 * (num2 + num3)))
                    ;;
            esac
            ;;
    esac
    
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

# Check if trying to install steam
if check_for_steam "$@"; then
    prompt_for_math_solution
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