#!/usr/bin/env bash
# Check that all Python files are under python_pkg/.
# Exceptions: linux_configuration/, phone_focus_mode/, Bash/,
#             and vendored/generated directories.
# Used as a pre-commit hook; receives staged file paths as arguments.

set -uo pipefail

errors=()

for file in "$@"; do
    # Only check .py files
    [[ "$file" != *.py ]] && continue

    # Skip files already under python_pkg/
    [[ "$file" == python_pkg/* ]] && continue

    # Skip allowed directories (non-Python projects with some Python scripts)
    case "$file" in
        linux_configuration/*|phone_focus_mode/*|scripts/*|meta/scripts/*) continue ;;
    esac

    # Skip vendored/generated directories
    skip=0
    for part in /.venv/ /venv/ /__pycache__/ /build/ /dist/ /node_modules/ /.git/; do
        case "/$file" in
            *"$part"*) skip=1; break ;;
        esac
    done
    [[ $skip -eq 1 ]] && continue

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
