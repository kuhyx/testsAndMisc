#!/bin/bash

# ============================================================================
# Install dependencies for the network diagnostics scripts and link them onto
# PATH.
#
# Runtime deps : curl, awk, coreutils (all base on Arch — checked, not installed)
# Test deps    : bats (extra/bats) — needed only to run the .bats suite
#
# Idempotent: safe to re-run. Existing symlinks are refreshed, already-present
# packages are skipped by pacman --needed.
# ============================================================================

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
readonly BIN_DIR="${HOME}/.local/bin"
readonly SCRIPTS=(line-speed-probe.sh steam-download-duty.sh)

require_runtime_tools() {
    # These ship with base/base-devel on Arch. Fail loudly rather than trying to
    # install a broken base system.
    local missing=()
    local tool
    for tool in curl awk; do
        command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
    done
    if (( ${#missing[@]} > 0 )); then
        printf 'Error: missing required tools: %s\n' "${missing[*]}" >&2
        exit 1
    fi
}

install_test_deps() {
    if command -v bats >/dev/null 2>&1; then
        printf 'bats already installed (%s)\n' "$(bats --version)"
        return
    fi
    printf 'Installing bats (test dependency)...\n'
    sudo pacman -S --noconfirm --needed bats
}

link_scripts() {
    mkdir -p "$BIN_DIR"
    local s
    for s in "${SCRIPTS[@]}"; do
        ln -sfn "${SCRIPT_DIR}/${s}" "${BIN_DIR}/${s}"
        printf 'linked %s -> %s\n' "${BIN_DIR}/${s}" "${SCRIPT_DIR}/${s}"
    done
}

main() {
    require_runtime_tools
    install_test_deps
    link_scripts
    printf '\nDone. Run the tests with:\n'
    printf '  bats %s/../../tests/test_network_diagnostics.bats\n' "$SCRIPT_DIR"
}

main "$@"
