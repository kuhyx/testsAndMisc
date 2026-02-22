#!/usr/bin/env bash
# Check that every directory containing C/C++ source files has a Makefile and run.sh.
# Used as a pre-commit hook; receives staged file paths as arguments.

set -uo pipefail

errors=()
declare -A checked_dirs

for file in "$@"; do
    dir=$(dirname "$file")

    # Skip build directories and CMake artefact trees
    if echo "$dir" | grep -qE '(^|/)build(/|$)'; then
        continue
    fi

    # Skip if already checked this directory
    [[ -v checked_dirs["$dir"] ]] && continue
    checked_dirs["$dir"]=1

    # Check for Makefile (case-insensitive: Makefile or makefile)
    if ! compgen -G "$dir/[Mm]akefile" > /dev/null 2>&1; then
        errors+=("MISSING Makefile in: $dir")
    fi

    # Check for run.sh
    if [[ ! -f "$dir/run.sh" ]]; then
        errors+=("MISSING run.sh in: $dir")
    fi
done

if [[ ${#errors[@]} -gt 0 ]]; then
    printf 'C/C++ build file check failed:\n'
    printf '  %s\n' "${errors[@]}"
    printf '\nEvery directory with .c/.cpp files must have a Makefile and run.sh.\n'
    exit 1
fi

exit 0
