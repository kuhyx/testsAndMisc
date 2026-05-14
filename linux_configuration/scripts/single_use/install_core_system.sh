#!/bin/bash
# Unified installer for all personal Linux system modules.
#
# CORE modules (always installed):
#   1. Workout screen locker    – python_pkg/screen_locker/
#   2. Hosts blocking setup     – linux_configuration/scripts/periodic_background/hosts/
#   3. Midnight shutdown timer  – setup_midnight_shutdown.sh
#
# SECONDARY modules (prompted unless --all / --none given):
#   4. Steam backlog enforcer   – python_pkg/steam_backlog_enforcer/
#   5. Pacman wrapper           – periodic_background/digital_wellbeing/pacman/
#   6. i3 configuration         – periodic_background/i3-configuration/
#   7. Compulsive opening block – block_compulsive_opening.sh
#   8. Focus-mode daemon        – install_focus_mode_daemon.sh
#
# Usage:
#   ./install_core_system.sh [--all | --none]
#
# Flags:
#   --all   Install all secondary modules without prompting
#   --none  Skip all secondary modules
#   -h      Show this help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINUX_CONFIG="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPO_ROOT="$(cd "$LINUX_CONFIG/.." && pwd)"

# ── Colour helpers ───────────────────────────────────────────────────────────
bold() { printf '\e[1m%s\e[0m' "$*"; }
green() { printf '\e[1;32m%s\e[0m' "$*"; }
yellow() { printf '\e[1;33m%s\e[0m' "$*"; }
red() { printf '\e[1;31m%s\e[0m' "$*"; }

header() { printf '\n%s\n%s\n' "$(bold "=== $1 ===")" "$(printf '=%.0s' {1..50})"; }
ok() { printf '%s %s\n' "$(green "✓")" "$*"; }
skip() { printf '%s %s\n' "$(yellow "–")" "$*"; }
fail() { printf '%s %s\n' "$(red "✗")" "$*"; }

# ── Argument parsing ─────────────────────────────────────────────────────────
SECONDARY_MODE="ask"  # ask | all | none

for arg in "$@"; do
    case "$arg" in
    --all)  SECONDARY_MODE="all" ;;
    --none) SECONDARY_MODE="none" ;;
    -h | --help)
        sed -n '2,/^$/p' "$0"
        exit 0
        ;;
    *)
        printf 'Unknown option: %s\n' "$arg" >&2
        exit 1
        ;;
    esac
done

# ── Result tracking ──────────────────────────────────────────────────────────
declare -a INSTALLED=()
declare -a SKIPPED=()
declare -a FAILED=()

run_installer() {
    local name="$1"
    shift
    header "$name"
    if "$@"; then
        ok "$name installed"
        INSTALLED+=("$name")
    else
        fail "$name failed (exit $?)"
        FAILED+=("$name")
    fi
}

ask_install() {
    # ask_install <name> <command...>
    # Prompts user; respects SECONDARY_MODE override.
    local name="$1"
    shift

    if [[ $SECONDARY_MODE == "none" ]]; then
        skip "$name (--none)"
        SKIPPED+=("$name")
        return
    fi

    if [[ $SECONDARY_MODE == "all" ]]; then
        run_installer "$name" "$@"
        return
    fi

    # interactive
    local answer
    printf '\nInstall %s? [y/N] ' "$(bold "$name")"
    read -r answer
    if [[ "${answer,,}" == "y" ]]; then
        run_installer "$name" "$@"
    else
        skip "$name"
        SKIPPED+=("$name")
    fi
}

# ── Summary ──────────────────────────────────────────────────────────────────
print_summary() {
    printf '\n%s\n' "$(bold "========== INSTALL SUMMARY ==========")"
    if [[ ${#INSTALLED[@]} -gt 0 ]]; then
        printf '%s\n' "$(green "Installed (${#INSTALLED[@]}):")"
        for m in "${INSTALLED[@]}"; do printf '  %s %s\n' "$(green "✓")" "$m"; done
    fi
    if [[ ${#SKIPPED[@]} -gt 0 ]]; then
        printf '%s\n' "$(yellow "Skipped (${#SKIPPED[@]}):")"
        for m in "${SKIPPED[@]}"; do printf '  %s %s\n' "$(yellow "–")" "$m"; done
    fi
    if [[ ${#FAILED[@]} -gt 0 ]]; then
        printf '%s\n' "$(red "Failed (${#FAILED[@]}):")"
        for m in "${FAILED[@]}"; do printf '  %s %s\n' "$(red "✗")" "$m"; done
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# CORE MODULES (always installed)
# ═══════════════════════════════════════════════════════════════════════════════
printf '\n%s\n' "$(bold "Installing CORE modules…")"

run_installer "Workout screen locker" \
    bash "$REPO_ROOT/python_pkg/screen_locker/install_systemd.sh"

run_installer "Hosts blocking" \
    bash "$LINUX_CONFIG/scripts/periodic_background/hosts/install.sh"

run_installer "Midnight shutdown timer" \
    bash "$LINUX_CONFIG/scripts/periodic_background/digital_wellbeing/setup_midnight_shutdown.sh"

# ═══════════════════════════════════════════════════════════════════════════════
# SECONDARY MODULES (prompted unless --all / --none)
# ═══════════════════════════════════════════════════════════════════════════════
printf '\n%s\n' "$(bold "Secondary modules (${SECONDARY_MODE})…")"

ask_install "Steam backlog enforcer" \
    bash "$REPO_ROOT/python_pkg/steam_backlog_enforcer/install.sh"

ask_install "Pacman wrapper" \
    bash "$LINUX_CONFIG/scripts/periodic_background/digital_wellbeing/pacman/install_pacman_wrapper.sh"

ask_install "i3 configuration" \
    bash "$LINUX_CONFIG/scripts/periodic_background/i3-configuration/install.sh"

ask_install "Compulsive opening blockade" \
    sudo bash "$LINUX_CONFIG/scripts/periodic_background/digital_wellbeing/block_compulsive_opening.sh" install

ask_install "Focus-mode daemon" \
    bash "$LINUX_CONFIG/scripts/periodic_background/digital_wellbeing/install_focus_mode_daemon.sh" install

# ═══════════════════════════════════════════════════════════════════════════════
print_summary
