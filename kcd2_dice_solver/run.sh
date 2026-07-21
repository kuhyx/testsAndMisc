#!/bin/bash

# ============================================================================
# Installs dependencies (Node via nvm, pnpm via corepack, then npm packages)
# and starts the KCD2 Dice Solver dev server.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly NODE_MIN_MAJOR=22
readonly NVM_DIR="${NVM_DIR:-$HOME/.nvm}"

ensure_node() {
    if command -v node >/dev/null 2>&1; then
        local major
        major="$(node --version | sed -E 's/^v([0-9]+).*/\1/')"
        if (( major >= NODE_MIN_MAJOR )); then
            return
        fi
        echo "Node $(node --version) is older than required v${NODE_MIN_MAJOR}; installing a newer version via nvm..."
    else
        echo "Node not found; installing via nvm..."
    fi

    if [[ ! -s "${NVM_DIR}/nvm.sh" ]]; then
        echo "Error: nvm not found at ${NVM_DIR}/nvm.sh; install nvm first." >&2
        exit 1
    fi
    # shellcheck source=/dev/null
    source "${NVM_DIR}/nvm.sh"
    nvm install --lts
    nvm use --lts
}

ensure_pnpm() {
    if command -v pnpm >/dev/null 2>&1; then
        return
    fi
    echo "pnpm not found; enabling via corepack..."
    corepack enable
    corepack prepare pnpm@latest --activate
}

main() {
    # nvm.sh may not be sourced yet in a fresh shell, so load it before the
    # version check even if `node` already resolves from a different source.
    if [[ -s "${NVM_DIR}/nvm.sh" ]]; then
        # shellcheck source=/dev/null
        source "${NVM_DIR}/nvm.sh"
    fi

    ensure_node
    ensure_pnpm

    cd "$SCRIPT_DIR"
    echo "Installing dependencies..."
    pnpm install

    echo "Starting dev server (http://localhost:5174)..."
    exec pnpm dev
}

main "$@"
