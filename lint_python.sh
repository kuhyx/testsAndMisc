#!/usr/bin/env bash
# ==============================================================================
# Python Linting Script - Run ALL linters with aggressive settings
# ==============================================================================
# Usage:
#   ./lint_python.sh              # Lint all Python files
#   ./lint_python.sh --fix        # Lint and auto-fix where possible
#   ./lint_python.sh <file.py>    # Lint specific file
#   ./lint_python.sh --quick      # Quick lint (ruff + mypy only)
#   ./lint_python.sh --report     # Generate detailed reports
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
PYTHON_PATHS=(
    "PYTHON"
    "articles"
    "poker-modifier-app"
    "tests"
)
EXCLUDE_PATHS=(
    ".venv"
    "__pycache__"
    ".git"
    "Bash/ffmpeg-build"
    ".pytest_cache"
    ".ruff_cache"
    ".mypy_cache"
)

# Build exclude pattern for find
EXCLUDE_PATTERN=""
for path in "${EXCLUDE_PATHS[@]}"; do
    EXCLUDE_PATTERN="${EXCLUDE_PATTERN} -path '*/${path}/*' -prune -o"
done

# Parse arguments
FIX_MODE=false
QUICK_MODE=false
REPORT_MODE=false
TARGET_FILES=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix|-f)
            FIX_MODE=true
            shift
            ;;
        --quick|-q)
            QUICK_MODE=true
            shift
            ;;
        --report|-r)
            REPORT_MODE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [FILES...]"
            echo ""
            echo "Options:"
            echo "  --fix, -f      Auto-fix issues where possible"
            echo "  --quick, -q    Quick mode (ruff + mypy only)"
            echo "  --report, -r   Generate detailed reports to ./lint-reports/"
            echo "  --verbose, -v  Show verbose output"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Lint all Python files"
            echo "  $0 --fix              # Lint and auto-fix"
            echo "  $0 PYTHON/            # Lint specific directory"
            echo "  $0 --quick --fix      # Quick lint with auto-fix"
            exit 0
            ;;
        *)
            TARGET_FILES="${TARGET_FILES} $1"
            shift
            ;;
    esac
done

# If no target specified, use default paths
if [[ -z "${TARGET_FILES}" ]]; then
    TARGET_FILES="${PYTHON_PATHS[*]}"
fi

# Create reports directory if needed
if [[ "${REPORT_MODE}" == true ]]; then
    mkdir -p "${PROJECT_ROOT}/lint-reports"
fi

# Track overall status
OVERALL_STATUS=0
FAILED_TOOLS=()

# ==============================================================================
# Helper functions
# ==============================================================================

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"
}

print_subheader() {
    echo ""
    echo -e "${CYAN}──────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}──────────────────────────────────────────────────────────────${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

run_tool() {
    local tool_name="$1"
    local tool_cmd="$2"
    local report_file="${PROJECT_ROOT}/lint-reports/${tool_name}.txt"

    print_subheader "Running ${tool_name}..."

    if [[ "${REPORT_MODE}" == true ]]; then
        if eval "${tool_cmd}" 2>&1 | tee "${report_file}"; then
            print_success "${tool_name} passed"
            return 0
        else
            print_error "${tool_name} found issues (see ${report_file})"
            FAILED_TOOLS+=("${tool_name}")
            return 1
        fi
    else
        if eval "${tool_cmd}"; then
            print_success "${tool_name} passed"
            return 0
        else
            print_error "${tool_name} found issues"
            FAILED_TOOLS+=("${tool_name}")
            return 1
        fi
    fi
}

check_tool() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        print_warning "$1 not found, skipping..."
        return 1
    fi
}

# ==============================================================================
# Main linting process
# ==============================================================================

print_header "Python Linting Suite - Aggressive Mode"
echo ""
print_info "Target: ${TARGET_FILES}"
print_info "Fix mode: ${FIX_MODE}"
print_info "Quick mode: ${QUICK_MODE}"
print_info "Report mode: ${REPORT_MODE}"

cd "${PROJECT_ROOT}"

# ==============================================================================
# RUFF - Primary linter and formatter
# ==============================================================================
if check_tool ruff; then
    if [[ "${FIX_MODE}" == true ]]; then
        run_tool "ruff-lint" "ruff check --fix --show-fixes ${TARGET_FILES}" || OVERALL_STATUS=1
        run_tool "ruff-format" "ruff format ${TARGET_FILES}" || OVERALL_STATUS=1
    else
        run_tool "ruff-lint" "ruff check ${TARGET_FILES}" || OVERALL_STATUS=1
        run_tool "ruff-format-check" "ruff format --check ${TARGET_FILES}" || OVERALL_STATUS=1
    fi
fi

# ==============================================================================
# MYPY - Static type checking
# ==============================================================================
if check_tool mypy; then
    run_tool "mypy" "mypy --strict --ignore-missing-imports ${TARGET_FILES}" || OVERALL_STATUS=1
fi

# Quick mode exits here
if [[ "${QUICK_MODE}" == true ]]; then
    print_header "Quick Lint Complete"
    if [[ ${#FAILED_TOOLS[@]} -gt 0 ]]; then
        print_error "Failed tools: ${FAILED_TOOLS[*]}"
        exit 1
    else
        print_success "All quick checks passed!"
        exit 0
    fi
fi

# ==============================================================================
# PYLINT - Comprehensive linting
# ==============================================================================
if check_tool pylint; then
    run_tool "pylint" "pylint --rcfile=pyproject.toml --jobs=0 --fail-under=0 ${TARGET_FILES}" || OVERALL_STATUS=1
fi

# ==============================================================================
# BANDIT - Security linting
# ==============================================================================
if check_tool bandit; then
    run_tool "bandit" "bandit -c pyproject.toml -r ${TARGET_FILES} --severity-level low --confidence-level low" || OVERALL_STATUS=1
fi

# ==============================================================================
# VULTURE - Dead code detection
# ==============================================================================
if check_tool vulture; then
    run_tool "vulture" "vulture --min-confidence 80 ${TARGET_FILES}" || OVERALL_STATUS=1
fi

# ==============================================================================
# FLAKE8 - Traditional linter
# ==============================================================================
if check_tool flake8; then
    run_tool "flake8" "flake8 --max-line-length=88 --extend-ignore=E203,W503 --max-complexity=10 ${TARGET_FILES}" || OVERALL_STATUS=1
fi

# ==============================================================================
# PYCODESTYLE - PEP 8 style checker
# ==============================================================================
if check_tool pycodestyle; then
    run_tool "pycodestyle" "pycodestyle --max-line-length=88 --ignore=E203,W503 ${TARGET_FILES}" || OVERALL_STATUS=1
fi

# ==============================================================================
# PYDOCSTYLE - Docstring style checker
# ==============================================================================
if check_tool pydocstyle; then
    run_tool "pydocstyle" "pydocstyle --convention=google ${TARGET_FILES}" || OVERALL_STATUS=1
fi

# ==============================================================================
# RADON - Complexity metrics
# ==============================================================================
if check_tool radon; then
    print_subheader "Running radon (complexity analysis)..."
    echo ""
    echo -e "${MAGENTA}Cyclomatic Complexity:${NC}"
    radon cc -a -s ${TARGET_FILES} || true
    echo ""
    echo -e "${MAGENTA}Maintainability Index:${NC}"
    radon mi -s ${TARGET_FILES} || true

    if [[ "${REPORT_MODE}" == true ]]; then
        radon cc -a -s ${TARGET_FILES} > "${PROJECT_ROOT}/lint-reports/radon-cc.txt" 2>&1 || true
        radon mi -s ${TARGET_FILES} > "${PROJECT_ROOT}/lint-reports/radon-mi.txt" 2>&1 || true
    fi
fi

# ==============================================================================
# INTERROGATE - Docstring coverage
# ==============================================================================
if check_tool interrogate; then
    run_tool "interrogate" "interrogate -v --fail-under=0 ${TARGET_FILES}" || OVERALL_STATUS=1
fi

# ==============================================================================
# PYRIGHT - Microsoft's type checker (optional, very strict)
# ==============================================================================
if check_tool pyright; then
    run_tool "pyright" "pyright ${TARGET_FILES}" || OVERALL_STATUS=1
fi

# ==============================================================================
# AUTOFLAKE - Unused imports/variables (fix mode only)
# ==============================================================================
if [[ "${FIX_MODE}" == true ]] && check_tool autoflake; then
    print_subheader "Running autoflake (removing unused imports)..."
    find ${TARGET_FILES} -name "*.py" -type f -exec autoflake --in-place --remove-all-unused-imports --remove-unused-variables {} \;
    print_success "autoflake completed"
fi

# ==============================================================================
# PYUPGRADE - Upgrade Python syntax (fix mode only)
# ==============================================================================
if [[ "${FIX_MODE}" == true ]] && check_tool pyupgrade; then
    print_subheader "Running pyupgrade (upgrading syntax to Python 3.10+)..."
    find ${TARGET_FILES} -name "*.py" -type f -exec pyupgrade --py310-plus {} \;
    print_success "pyupgrade completed"
fi

# ==============================================================================
# CODESPELL - Spell checking
# ==============================================================================
if check_tool codespell; then
    if [[ "${FIX_MODE}" == true ]]; then
        run_tool "codespell" "codespell -w --skip='*.json,*.lock,.git,__pycache__,.venv' ${TARGET_FILES}" || OVERALL_STATUS=1
    else
        run_tool "codespell" "codespell --skip='*.json,*.lock,.git,__pycache__,.venv' ${TARGET_FILES}" || OVERALL_STATUS=1
    fi
fi

# ==============================================================================
# Summary
# ==============================================================================
print_header "Linting Summary"
echo ""

if [[ ${#FAILED_TOOLS[@]} -gt 0 ]]; then
    print_error "The following tools reported issues:"
    for tool in "${FAILED_TOOLS[@]}"; do
        echo "  - ${tool}"
    done
    echo ""
    if [[ "${REPORT_MODE}" == true ]]; then
        print_info "Detailed reports saved to: ${PROJECT_ROOT}/lint-reports/"
    fi
    print_info "Run with --fix to auto-fix issues where possible"
    exit 1
else
    print_success "All linting checks passed!"
    exit 0
fi
