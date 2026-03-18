#!/usr/bin/env bash
# Check that all Python files are under python_pkg/.
# Exceptions: linux_configuration/, pomodoro_app/, sonic_pi/, Bash/,
#             and vendored/generated directories.
# Used as a pre-commit hook; receives staged file paths as arguments.

set -uo pipefail

# Directories allowed to contain Python files outside python_pkg/
ALLOWED_DIRS="linux_configuration/|pomodoro_app/|sonic_pi/"

errors=()

for file in "$@"; do
    # Only check .py files
    [[ "$file" != *.py ]] && continue

    # Skip files already under python_pkg/
    [[ "$file" == python_pkg/* ]] && continue

    # Skip allowed directories (non-Python projects with some Python scripts)
    if echo "$file" | grep -qE "^($ALLOWED_DIRS)"; then
        continue
    fi

    # Skip vendored/generated directories
    if echo "$file" | grep -qE '(^|/)(\.venv|venv|__pycache__|build|dist|node_modules|\.git)/'; then
        continue
    fi

    errors+=("$file")
done

if [[ ${#errors[@]} -gt 0 ]]; then
    echo "ERROR: Python files must be under python_pkg/."
    echo "The following files are in the wrong location:"
    for err in "${errors[@]}"; do
        echo "  $err"
    done
    echo ""
    echo "Move them with: git mv <file> python_pkg/<file>"
    exit 1
fi
