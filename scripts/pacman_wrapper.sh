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
    local restricted_packages=("steam" "freetube-bin" "seamonkey-bin" "seamonkey" "min-browser-bin" "min-browser" "beaker-browser" "catalyst-browser-bin" "hamsket" "min" "vieb-bin" "yt-dlp" "yt-dlp" "yt-dlp-git")
    
    # Check if the command is an installation command
    if [[ "$1" == "-S" || "$1" == "-Sy" || "$1" == "-Syu" || "$1" == "-Syyu" || "$1" == "-U" ]]; then
        # Check all arguments
        for arg in "$@"; do
            # Check if argument matches any restricted package
            for package in "${restricted_packages[@]}"; do
                if [[ "$arg" == "$package" || "$arg" == *"/$package-"* || "$arg" == *"/$package/"* ]]; then
                    return 0  # Restricted package found
                fi
            done
        done
    fi
    return 1  # No restricted package found
}

# Function to prompt for solving a word unscrambling challenge
function prompt_for_math_solution() {
    echo -e "${YELLOW}WARNING: You are trying to install a restricted package.${NC}"
    echo -e "${YELLOW}Challenge will begin shortly...${NC}"
    
    # Sleep for random 20-40 seconds
    sleep_duration=$((RANDOM % 20 + 20))
    sleep $sleep_duration
    
    # Define path to words.txt (in the same directory as the script)
    script_dir="$(dirname "$(readlink -f "$0")")"
    words_file="$script_dir/words.txt"
    
    # Check if words.txt exists
    if [[ ! -f "$words_file" ]]; then
        echo -e "${RED}Error: words.txt file not found at $words_file${NC}"
        return 1
    fi
    
    # Filter words by length (5-8 characters) and load random words
    words_count=160
    mapfile -t selected_words < <(grep -E '^[a-zA-Z]{5,8}$' "$words_file" | shuf -n $words_count)
    
    # If we couldn't get enough words of the right length
    if [[ ${#selected_words[@]} -lt $words_count ]]; then
        echo -e "${RED}Warning: Could only find ${#selected_words[@]} words of the required length.${NC}"
        words_count=${#selected_words[@]}
        if [[ $words_count -eq 0 ]]; then
            echo -e "${RED}Error: No words of length 5-8 found in $words_file${NC}"
            return 1
        fi
    fi
    
    # Convert all words to uppercase
    for i in "${!selected_words[@]}"; do
        selected_words[$i]=$(echo "${selected_words[$i]}" | tr '[:lower:]' '[:upper:]')
    done
    
    echo -e "${CYAN}Here are ${words_count} random words. Remember them:${NC}"
    
    # Display the words in a grid (4 columns)
    for (( i=0; i<words_count; i++ )); do
        printf "${BLUE}%-15s${NC}" "${selected_words[$i]}"
        if (( (i+1) % 4 == 0 )); then
            echo ""
        fi
    done

    # Select a random word to scramble (already in uppercase)
    target_index=$((RANDOM % ${words_count}))
    target_word="${selected_words[$target_index]}"
    
    # Scramble the word
    scrambled_word=$(echo "$target_word" | fold -w1 | shuf | tr -d '\n')
    
    # Ensure scrambled word is different from original
    if [[ "$scrambled_word" == "$target_word" ]]; then
        # Use simple reversal as fallback
        scrambled_word=$(echo "$target_word" | rev)
    fi
    
    echo -e "\n${YELLOW}One of those words has been scrambled to:${NC} ${CYAN}$scrambled_word${NC}"
    echo -e "${YELLOW}Unscramble the word to proceed with installation:${NC}"
    read -r user_input
    
    # Convert user input to uppercase and trim whitespaces
    user_input=$(echo "$user_input" | tr '[:lower:]' '[:upper:]' | xargs)
    
    if [[ "$user_input" == "$target_word" ]]; then
        echo -e "${GREEN}Correct! Proceeding with installation...${NC}"
        return 0
    else
        echo -e "${RED}Incorrect answer. Installation aborted. The correct word was '$target_word'.${NC}"
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