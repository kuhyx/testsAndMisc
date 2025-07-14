# Lint script for imageViewer project
#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}==>${NC} ${1}"
}

print_success() {
    echo -e "${GREEN}✓${NC} ${1}"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} ${1}"
}

print_error() {
    echo -e "${RED}✗${NC} ${1}"
}

# Check if required tools are installed
check_tools() {
    print_step "Checking required tools..."
    
    local missing_tools=()
    
    if ! command -v clang-tidy &> /dev/null; then
        missing_tools+=("clang-tidy")
    fi
    
    if ! command -v cppcheck &> /dev/null; then
        missing_tools+=("cppcheck")
    fi
    
    if ! command -v clang-format &> /dev/null; then
        missing_tools+=("clang-format")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_step "Installing missing tools..."
        
        # Check if we're on Arch Linux
        if command -v pacman &> /dev/null; then
            sudo pacman -S --needed clang cppcheck
        elif command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y clang-tidy cppcheck clang-format
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y clang-tools-extra cppcheck clang
        else
            print_error "Please install the following tools manually: ${missing_tools[*]}"
            exit 1
        fi
    fi
    
    print_success "All required tools are available"
}

# Run clang-tidy
run_clang_tidy() {
    print_step "Running clang-tidy analysis..."
    
    if [ -f ".clang-tidy" ]; then
        clang-tidy main.c -- -I/usr/include/SDL2 -D_REENTRANT 2>/dev/null || {
            print_warning "clang-tidy found issues (see output above)"
        }
    else
        print_warning ".clang-tidy config not found, using default settings"
        clang-tidy main.c -- -I/usr/include/SDL2 -D_REENTRANT 2>/dev/null || {
            print_warning "clang-tidy found issues (see output above)"
        }
    fi
    
    print_success "clang-tidy analysis completed"
}

# Run cppcheck
run_cppcheck() {
    print_step "Running cppcheck analysis..."
    
    cppcheck --enable=all --check-level=exhaustive --suppress=missingIncludeSystem \
            --quiet --std=c23 main.c || {
        print_warning "cppcheck found issues (see output above)"
    }
    
    print_success "cppcheck analysis completed"
}

# Check code formatting
check_formatting() {
    print_step "Checking code formatting..."
    
    if [ -f ".clang-format" ]; then
        if clang-format --dry-run --Werror main.c 2>/dev/null; then
            print_success "Code formatting is correct"
        else
            print_warning "Code formatting issues found"
            echo "Run 'clang-format -i main.c' to fix formatting"
        fi
    else
        print_warning ".clang-format config not found, skipping format check"
    fi
}

# Run basic compile check
compile_check() {
    print_step "Running compile check..."
    
    # Try to compile with extra warnings
    if gcc -Wall -Wextra -Wpedantic -std=c99 -O2 \
           $(pkg-config --cflags sdl2 2>/dev/null || echo "-I/usr/include/SDL2") \
           -c main.c -o /tmp/main.o 2>/dev/null; then
        print_success "Compile check passed"
        rm -f /tmp/main.o
    else
        print_error "Compile check failed"
        print_step "Trying compile with detailed errors..."
        gcc -Wall -Wextra -Wpedantic -std=c99 -O2 \
            $(pkg-config --cflags sdl2 2>/dev/null || echo "-I/usr/include/SDL2") \
            -c main.c -o /tmp/main.o
    fi
}

# Check for common C issues
check_common_issues() {
    print_step "Checking for common C issues..."
    
    local issues=0
    
    # Check for TODO/FIXME comments
    if grep -n "TODO\|FIXME\|XXX\|HACK" main.c 2>/dev/null; then
        print_warning "Found TODO/FIXME comments"
        issues=$((issues + 1))
    fi
    
    # Check for potential buffer overflows
    if grep -n "strcpy\|strcat\|sprintf\|gets" main.c 2>/dev/null; then
        print_warning "Found potentially unsafe string functions"
        issues=$((issues + 1))
    fi
    
    # Check for magic numbers (basic check)
    if grep -E "\b[0-9]{3,}\b" main.c | grep -v "printf\|#define" 2>/dev/null; then
        print_warning "Found potential magic numbers"
        issues=$((issues + 1))
    fi
    
    if [ $issues -eq 0 ]; then
        print_success "No common issues found"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}C Language Linter for imageViewer Project${NC}"
    echo "=========================================="
    echo
    
    # Check if we're in the right directory
    if [ ! -f "main.c" ]; then
        print_error "main.c not found. Please run this script from the imageViewer directory."
        exit 1
    fi
    
    check_tools
    echo
    
    compile_check
    echo
    
    run_clang_tidy
    echo
    
    run_cppcheck
    echo
    
    check_formatting
    echo
    
    check_common_issues
    echo
    
    print_success "Linting completed!"
    echo
    echo -e "${BLUE}Available commands:${NC}"
    echo "  ./lint.sh                 - Run all checks"
    echo "  clang-format -i main.c    - Fix formatting"
    echo "  clang-tidy main.c --fix   - Apply clang-tidy fixes"
}

# Run main function
main "$@"
