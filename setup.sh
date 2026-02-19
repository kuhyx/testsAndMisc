#!/usr/bin/env bash
# Post-clone setup script for testsAndMisc repository.
# Run once after cloning: ./setup.sh

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

printf 'Configuring git hooks path...\n'
git config core.hooksPath linux_configuration/.githooks
printf '  ✓ core.hooksPath set to linux_configuration/.githooks\n'

# Check for C/C++ and shell lint tools (used by pre-commit hooks)
MISSING=()
for cmd in clang-format cppcheck flawfinder shellcheck node npx; do
	command -v "$cmd" >/dev/null 2>&1 || MISSING+=("$cmd")
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
	printf '\n⚠ Missing tools for pre-commit hooks: %s\n' "${MISSING[*]}"
	if command -v pacman >/dev/null 2>&1; then
		printf '  Install with: sudo pacman -S --needed %s\n' "${MISSING[*]}"
	elif command -v apt-get >/dev/null 2>&1; then
		printf '  Install with: sudo apt-get install %s\n' "${MISSING[*]}"
	else
		printf '  Please install: %s\n' "${MISSING[*]}"
	fi
else
	printf '  ✓ All lint tools available\n'
fi

printf '\nSetup complete.\n'
