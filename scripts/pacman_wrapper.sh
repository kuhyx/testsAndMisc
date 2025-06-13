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
            echo -e "${BLUE}Installing packages...${NC}" >&2
            ;;
        -Syu|-Syyu)
            echo -e "${BLUE}Updating system...${NC}" >&2
            ;;
        -R|-Rs|-Rns|-R\ *)
            echo -e "${YELLOW}Removing packages...${NC}" >&2
            ;;
        -Ss|-Ss\ *)
            echo -e "${CYAN}Searching for packages...${NC}" >&2
            ;;
        -Q|-Qs|-Qi|-Ql|-Q\ *)
            echo -e "${CYAN}Querying package database...${NC}" >&2
            ;;
        -U|-U\ *)
            echo -e "${BLUE}Installing local packages...${NC}" >&2
            ;;
        -Scc)
            echo -e "${YELLOW}Cleaning package cache...${NC}" >&2
            ;;
        *)
            echo -e "${CYAN}Executing pacman command...${NC}" >&2
            ;;
    esac
}

# Function to check if user is trying to install packages that are always blocked
function check_for_always_blocked() {
    # List of packages that are ALWAYS blocked without any challenge
    local always_blocked_packages=("freetube-bin" "freetube" "seamonkey-bin" "seamonkey" "min-browser-bin" "min-browser" "beaker-browser" "catalyst-browser-bin" "hamsket" "min" "vieb-bin" "yt-dlp" "yt-dlp-git" "stremio" "stremio-git" "angelfish" "dooble" "eric" "falkon" "fiery" "maui" "konqueror" "liri" "otter" "quotebrowser" "beaker" "catalyst" "badwolf" "eolie" "epiphany" "surf" "uzbl" "vimb" "vimb-git" "web-browser" "web-browser-git" "web-browser-bin" "web-browser-bin-git" "web-browser-bin-git" "luakit" "nyxt" "tangram" "vimb" "dillo" "links" "netsurf" "amfora" "tartube")
     
    # Check if the command is an installation command
    if [[ "$1" == "-S" || "$1" == "-Sy" || "$1" == "-Syu" || "$1" == "-Syyu" || "$1" == "-U" ]]; then
        # Check all arguments
        for arg in "$@"; do
            # Strip repository prefix if present (like extra/ or community/)
            local package_name="${arg##*/}"
            
            # Check if argument matches any always blocked package
            for package in "${always_blocked_packages[@]}"; do
                if [[ "$arg" == "$package" || "$arg" == *"/$package-"* || "$arg" == *"/$package/"* || 
                      "$arg" == *"/$package" || "$package_name" == "$package" ]]; then
                    return 0  # Always blocked package found
                fi
            done
        done
    fi
    return 1  # No always blocked package found
}

# Function to check if user is trying to install steam (challenge-eligible package)
function check_for_steam() {
    # List of packages that require challenge (only steam in this case)
    local steam_packages=("steam")
     
    # Check if the command is an installation command
    if [[ "$1" == "-S" || "$1" == "-Sy" || "$1" == "-Syu" || "$1" == "-Syyu" || "$1" == "-U" ]]; then
        # Check all arguments
        for arg in "$@"; do
            # Strip repository prefix if present (like extra/ or community/)
            local package_name="${arg##*/}"
            
            # Check if argument matches steam
            for package in "${steam_packages[@]}"; do
                if [[ "$arg" == "$package" || "$arg" == *"/$package-"* || "$arg" == *"/$package/"* || 
                      "$arg" == *"/$package" || "$package_name" == "$package" ]]; then
                    return 0  # Steam package found
                fi
            done
        done
    fi
    return 1  # No steam package found
}

# Function to check if user is trying to install virtualbox (always challenge-eligible package)
function check_for_virtualbox() {
    # List of packages that require challenge (virtualbox packages)
    local virtualbox_packages=("virtualbox" "virtualbox-host-modules-arch" "virtualbox-guest-iso" "virtualbox-ext-vnc" "virtualbox-guest-utils" "virtualbox-host-dkms")
     
    # Check if the command is an installation command
    if [[ "$1" == "-S" || "$1" == "-Sy" || "$1" == "-Syu" || "$1" == "-Syyu" || "$1" == "-U" ]]; then
        # Check all arguments
        for arg in "$@"; do
            # Strip repository prefix if present (like extra/ or community/)
            local package_name="${arg##*/}"
            
            # Check if argument matches virtualbox
            for package in "${virtualbox_packages[@]}"; do
                if [[ "$arg" == "$package" || "$arg" == *"/$package-"* || "$arg" == *"/$package/"* || 
                      "$arg" == *"/$package" || "$package_name" == "$package" ]]; then
                    return 0  # VirtualBox package found
                fi
            done
        done
    fi
    return 1  # No virtualbox package found
}

# Function to check if current day is a weekday (after 4PM Friday until midnight Sunday)
function is_weekday() {
    local day_of_week=$(date +%u)  # %u gives 1-7 (Monday is 1, Sunday is 7)
    local hour=$(date +%H)         # %H gives hour in 24-hour format (00-23)
    
    # Monday through Thursday are always weekdays
    if [[ $day_of_week -ge 1 && $day_of_week -le 4 ]]; then
        return 0  # Is weekday
    # Friday before 4PM is weekday, after 4PM is weekend
    elif [[ $day_of_week -eq 5 ]]; then
        if [[ $hour -lt 16 ]]; then
            return 0  # Is weekday (Friday before 4PM)
        else
            return 1  # Is weekend (Friday after 4PM)
        fi
    # Saturday and Sunday are weekend
    else
        return 1  # Is weekend
    fi
}

# Function to prompt for solving a word unscrambling challenge (only for steam)
function prompt_for_steam_challenge() {
    echo -e "${YELLOW}WARNING: You are trying to install Steam.${NC}"
    
    # Check if it's a weekday and block completely
    if is_weekday; then
        local day_name=$(date +%A)
        echo -e "${RED}Steam installation BLOCKED: Steam cannot be installed on weekdays.${NC}"
        echo -e "${RED}Today is $day_name. Please try again on the weekend (Saturday or Sunday).${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Weekend Steam challenge will begin shortly...${NC}"
    
    # Sleep for random 20-40 seconds
    # sleep_duration=$((RANDOM % 20 + 20))
    sleep_duration=$((RANDOM % 20))
    sleep $sleep_duration
    
    # Define path to words.txt (in the same directory as the script)
    script_dir="$(dirname "$(readlink -f "$0")")"
    words_file="$script_dir/words.txt"
    
    # Check if words.txt exists
    if [[ ! -f "$words_file" ]]; then
        echo -e "${RED}Error: words.txt file not found at $words_file${NC}"
        return 1
    fi
    
    # Choose a specific word length (5, 6, 7, or 8 characters)
    #
    word_length=5
    echo -e "${CYAN}Today's challenge: Words with ${word_length} letters${NC}"
    
    # Filter words by the specific chosen length and load random words
    words_count=160
    mapfile -t selected_words < <(grep -E "^[a-zA-Z]{$word_length}$" "$words_file" | shuf -n $words_count)
    
    # If we couldn't get enough words of the right length
    if [[ ${#selected_words[@]} -lt $words_count ]]; then
        echo -e "${RED}Warning: Could only find ${#selected_words[@]} words of length $word_length.${NC}"
        words_count=${#selected_words[@]}
        if [[ $words_count -eq 0 ]]; then
            echo -e "${RED}Error: No words of length $word_length found in $words_file${NC}"
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
    echo -e "${YELLOW}Unscramble the word to proceed with installation (you have 2 minutes):${NC}"
    
    # Set up a background process to display the timer
    (
        start_time=$(date +%s)
        while true; do
            current_time=$(date +%s)
            elapsed=$((current_time - start_time))
            remaining=$((60 - elapsed))
            
            if [[ $remaining -le 0 ]]; then
                echo -ne "\r${YELLOW}Time remaining: 0 seconds${NC}    "
                break
            fi
            
            echo -ne "\r${YELLOW}Time remaining: ${remaining} seconds${NC}    "
            sleep 1
        done
    ) &
    display_pid=$!
    
    # Read user input with timeout
    read -t 60 -r user_input
    read_status=$?
    
    # Kill the timer display
    kill $display_pid 2>/dev/null
    wait $display_pid 2>/dev/null
    echo # Add a newline after the timer
    
    # Check if read timed out
    if [[ $read_status -ne 0 ]]; then
        echo -e "${RED}Time's up! Challenge failed. The correct word was '$target_word'.${NC}"
        return 1
    fi
    
    # Convert user input to uppercase and trim whitespaces
    user_input=$(echo "$user_input" | tr '[:lower:]' '[:upper:]' | xargs)
    
    if [[ "$user_input" == "$target_word" ]]; then
        echo -e "${GREEN}Correct! Proceeding with installation...${NC}"
        
        # Add sleep after successful challenge completion (20-40 seconds)
        # post_challenge_sleep=$((RANDOM % 20 + 20))
        post_challenge_sleep=$((RANDOM % 20))
        sleep $post_challenge_sleep
        
        return 0
    else
        echo -e "${RED}Incorrect answer. Installation aborted. The correct word was '$target_word'.${NC}"
        return 1
    fi
}

# Function to prompt for solving a word unscrambling challenge (for virtualbox - always active)
function prompt_for_virtualbox_challenge() {
    echo -e "${YELLOW}WARNING: You are trying to install VirtualBox.${NC}"
    echo -e "${YELLOW}VirtualBox challenge will begin shortly...${NC}"
    
    # Sleep for random 10-30 seconds
    sleep_duration=$((RANDOM % 20 + 10))
    sleep $sleep_duration
    
    # Define path to words.txt (in the same directory as the script)
    script_dir="$(dirname "$(readlink -f "$0")")"
    words_file="$script_dir/words.txt"
    
    # Check if words.txt exists
    if [[ ! -f "$words_file" ]]; then
        echo -e "${RED}Error: words.txt file not found at $words_file${NC}"
        return 1
    fi
    
    # Choose a specific word length (6, 7, or 8 characters for VirtualBox)
    word_length=6
    echo -e "${CYAN}VirtualBox challenge: Words with ${word_length} letters${NC}"
    
    # Filter words by the specific chosen length and load random words
    words_count=120
    mapfile -t selected_words < <(grep -E "^[a-zA-Z]{$word_length}$" "$words_file" | shuf -n $words_count)
    
    # If we couldn't get enough words of the right length
    if [[ ${#selected_words[@]} -lt $words_count ]]; then
        echo -e "${RED}Warning: Could only find ${#selected_words[@]} words of length $word_length.${NC}"
        words_count=${#selected_words[@]}
        if [[ $words_count -eq 0 ]]; then
            echo -e "${RED}Error: No words of length $word_length found in $words_file${NC}"
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
    echo -e "${YELLOW}Unscramble the word to proceed with VirtualBox installation (you have 90 seconds):${NC}"
    
    # Set up a background process to display the timer
    (
        start_time=$(date +%s)
        while true; do
            current_time=$(date +%s)
            elapsed=$((current_time - start_time))
            remaining=$((90 - elapsed))
            
            if [[ $remaining -le 0 ]]; then
                echo -ne "\r${YELLOW}Time remaining: 0 seconds${NC}    "
                break
            fi
            
            echo -ne "\r${YELLOW}Time remaining: ${remaining} seconds${NC}    "
            sleep 1
        done
    ) &
    display_pid=$!
    
    # Read user input with timeout (90 seconds for VirtualBox)
    read -t 90 -r user_input
    read_status=$?
    
    # Kill the timer display
    kill $display_pid 2>/dev/null
    wait $display_pid 2>/dev/null
    echo # Add a newline after the timer
    
    # Check if read timed out
    if [[ $read_status -ne 0 ]]; then
        echo -e "${RED}Time's up! VirtualBox challenge failed. The correct word was '$target_word'.${NC}"
        return 1
    fi
    
    # Convert user input to uppercase and trim whitespaces
    user_input=$(echo "$user_input" | tr '[:lower:]' '[:upper:]' | xargs)
    
    if [[ "$user_input" == "$target_word" ]]; then
        echo -e "${GREEN}Correct! Proceeding with VirtualBox installation...${NC}"
        
        # Add sleep after successful challenge completion (15-35 seconds)
        post_challenge_sleep=$((RANDOM % 20 + 15))
        sleep $post_challenge_sleep
        
        return 0
    else
        echo -e "${RED}Incorrect answer. VirtualBox installation aborted. The correct word was '$target_word'.${NC}"
        return 1
    fi
}

# Check for wrapper-specific commands
if [[ "$1" == "--help-wrapper" ]]; then
    show_help
    exit 0
fi

# Check for always blocked packages first (highest priority)
if check_for_always_blocked "$@"; then
    echo -e "${RED}Installation BLOCKED: This package is permanently restricted and cannot be installed.${NC}"
    echo -e "${RED}Package installation has been denied by system policy.${NC}"
    exit 1
fi

# Check for virtualbox (always challenge-eligible package)
if check_for_virtualbox "$@"; then
    prompt_for_virtualbox_challenge
    if [[ $? -ne 0 ]]; then
        exit 1
    fi
fi

# Check for steam (challenge-eligible package)
if check_for_steam "$@"; then
    prompt_for_steam_challenge
    if [[ $? -ne 0 ]]; then
        exit 1
    fi
fi

# Display operation
display_operation "$1"

# Echo the command that's about to be executed
echo -e "${GREEN}Executing:${NC} $PACMAN_BIN $@" >&2

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
    echo -e "${GREEN}Command completed successfully in ${duration}s.${NC}" >&2
else
    echo -e "${RED}Command failed with exit code ${exit_code}.${NC}" >&2
fi

# Display some helpful tips depending on the operation
if [[ "$1" == "-S" || "$1" == "-S "* ]] && [ $exit_code -eq 0 ]; then
    echo -e "${CYAN}Tip:${NC} You may need to log out or restart to use some newly installed software."
fi

if [[ "$1" == "-Syu" || "$1" == "-Syyu" ]] && [ $exit_code -eq 0 ]; then
    echo -e "${CYAN}Tip:${NC} Consider restarting after major updates."
fi

exit $exit_code