#!/bin/bash
# Wrapper script for anki_generator that ensures argostranslate is available
#
# Usage: ./run_anki_generator.sh [anki_generator args...]
# Example: ./run_anki_generator.sh --file text.txt --length 20 --from pl --to en

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Use /tmp for venv to avoid home directory quota issues
VENV_DIR="/tmp/.venv_argos_$(id -u)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Convert relative file paths to absolute before changing directories
resolve_file_paths() {
    local args=()
    local i=0
    while [[ $i -lt ${#ORIGINAL_ARGS[@]} ]]; do
        local arg="${ORIGINAL_ARGS[$i]}"
        if [[ "$arg" == "--file" || "$arg" == "-f" ]]; then
            args+=("$arg")
            ((i++))
            if [[ $i -lt ${#ORIGINAL_ARGS[@]} ]]; then
                local file="${ORIGINAL_ARGS[$i]}"
                # Convert relative path to absolute
                if [[ -f "$file" ]]; then
                    file="$(cd "$(dirname "$file")" && pwd)/$(basename "$file")"
                fi
                args+=("$file")
            fi
        else
            args+=("$arg")
        fi
        ((i++))
    done
    echo "${args[@]}"
}

# Store original args before any directory changes
ORIGINAL_ARGS=("$@")

# Check if argostranslate is available
check_argos() {
    python -c "import argostranslate" 2>/dev/null
}

# Try to install argostranslate using pipx (system-wide)
try_pipx_install() {
    if command -v pipx &>/dev/null; then
        log_info "Trying pipx install argostranslate..."
        if pipx install argostranslate 2>/dev/null; then
            log_info "argostranslate installed via pipx"
            return 0
        fi
    fi
    return 1
}

# Create/use a virtualenv for argostranslate
setup_venv() {
    # Use /tmp for pip cache to avoid home directory quota issues
    export PIP_CACHE_DIR="/tmp/.pip_cache_$(id -u)"
    mkdir -p "$PIP_CACHE_DIR"
    
    if [[ ! -d "$VENV_DIR" ]]; then
        log_info "Creating virtual environment at $VENV_DIR..."
        python -m venv "$VENV_DIR"
    fi
    
    # Activate venv
    source "$VENV_DIR/bin/activate"
    
    # Install argostranslate if not present
    if ! python -c "import argostranslate" 2>/dev/null; then
        log_info "Installing argostranslate in virtualenv (this may take a few minutes)..."
        # Use CPU-only PyTorch to reduce download size significantly (~200MB vs ~900MB)
        # Use --no-cache-dir to avoid any cache writes to home directory
        pip install --progress-bar on --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
        pip install --progress-bar on --no-cache-dir argostranslate
    fi
    
    # Install langdetect for auto language detection
    if ! python -c "import langdetect" 2>/dev/null; then
        log_info "Installing langdetect for auto language detection..."
        pip install --progress-bar on --no-cache-dir langdetect
    fi
    
    # Also ensure other dependencies are available
    if [[ -f "${SCRIPT_DIR}/../../requirements.txt" ]]; then
        pip install --progress-bar on --no-cache-dir -r "${SCRIPT_DIR}/../../requirements.txt" 2>/dev/null || true
    fi
    
    log_info "Using virtualenv: $VENV_DIR"
}

# Main logic
main() {
    # Resolve file paths to absolute before changing directories
    local resolved_args
    resolved_args=$(resolve_file_paths)
    
    # If --no-translate is passed, we don't need argostranslate
    if [[ " $* " =~ " --no-translate " ]] || [[ " $* " =~ " -n " ]]; then
        log_info "Running without translation (--no-translate)"
        cd "$(dirname "$SCRIPT_DIR")" && cd ..
        python -m python_pkg.word_frequency.anki_generator $resolved_args
        exit $?
    fi
    
    # Check if argostranslate is already available
    if check_argos; then
        log_info "argostranslate is available"
        cd "$(dirname "$SCRIPT_DIR")" && cd ..
        python -m python_pkg.word_frequency.anki_generator $resolved_args
        exit $?
    fi
    
    log_warn "argostranslate not found in system Python"
    
    # Try pipx first (cleaner system-wide installation)
    if try_pipx_install && check_argos; then
        cd "$(dirname "$SCRIPT_DIR")" && cd ..
        python -m python_pkg.word_frequency.anki_generator $resolved_args
        exit $?
    fi
    
    # Fall back to virtualenv
    log_info "Setting up virtualenv with argostranslate..."
    setup_venv
    
    # Run in venv context
    cd "$(dirname "$SCRIPT_DIR")" && cd ..
    python -m python_pkg.word_frequency.anki_generator $resolved_args
}

main "$@"
