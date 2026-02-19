#!/usr/bin/env bash
# Post-clone setup script for testsAndMisc repository.
# Run once after cloning: ./setup.sh

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

printf 'Configuring git hooks path...\n'
git config core.hooksPath linux_configuration/.githooks
printf '  ✓ core.hooksPath set to linux_configuration/.githooks\n'

printf 'Setup complete.\n'
