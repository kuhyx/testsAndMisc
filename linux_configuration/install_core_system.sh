#!/bin/bash
# Unified installer for all personal Linux system modules.
#
# This installer is CROSS-REPO: several modules were extracted into sibling
# repos. A missing sibling is cloned automatically (see require_extracted_repo);
# a clone that fails is a loud module failure, never a silent skip.
#
# CORE modules (always installed):
#   0. Guard library (guardctl) – github.com/kuhyx/utils (~/utils/guard-lib)
#   1. Workout screen locker    – github.com/kuhyx/screen-locker (~/screen-locker)
#   2. Hosts blocking setup     – github.com/kuhyx/hosts-blocker (~/hosts-blocker)
#   3. Midnight shutdown timer  – github.com/kuhyx/digital-wellbeing
#
# SECONDARY modules (prompted unless --all / --none given):
#   4. Steam backlog enforcer   – github.com/kuhyx/steam-backlog-enforcer
#   5. Pacman wrapper           – github.com/kuhyx/digital-wellbeing (~/digital-wellbeing)
#   6. i3 configuration         – i3/
#   7. Compulsive opening block – block_compulsive_opening.sh
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
LINUX_CONFIG="$SCRIPT_DIR"
# Locates repos extracted out of this monorepo (hosts-blocker, ...).
# shellcheck source=lib/extracted_repos.sh
source "$LINUX_CONFIG/lib/extracted_repos.sh"

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
SECONDARY_MODE="ask" # ask | all | none

for arg in "$@"; do
	case "$arg" in
	--all) SECONDARY_MODE="all" ;;
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

# install_module_from_repo <repo-name> <what> <script-rel-path> [args...]
# Runs an installer that lives in a sibling repo extracted out of this monorepo.
#
# This installer is cross-repo: screen-locker, steam-backlog-enforcer and
# guard-lib (inside utils) are separate checkouts now. require_extracted_repo
# clones a missing one, so a bare machine still gets a working install from the
# single documented command. If the clone fails, or the repo is present but the
# script inside it is not, that is a hard failure -- the module lands in the
# Failed() summary rather than being silently skipped, which is the failure mode
# that let these two defects survive unnoticed.
#
# ROOT_MODE selects how the script is invoked:
#   auto  - run as-is; the script elevates itself if it needs to (default)
#   sudo  - run under sudo; for scripts that require root but do NOT self-elevate
#           (guard-lib's install.sh hard-exits as non-root instead of re-execing)
# Never blanket-sudo: screen-locker installs a systemd *user* service into
# $HOME/.config/systemd/user, so running it as root would install it for /root.
install_module_from_repo() {
	local repo="$1" what="$2" rel="$3" root_mode="${ROOT_MODE:-auto}"
	shift 3
	local dir script
	dir="$(require_extracted_repo "$repo" "$what")" || return 1
	script="$dir/$rel"
	if [[ ! -f $script ]]; then
		printf 'ERROR: %s: expected installer not found at %s\n' "$what" "$script" >&2
		return 1
	fi
	if [[ $root_mode == "sudo" && $EUID -ne 0 ]]; then
		sudo bash "$script" "$@"
	else
		bash "$script" "$@"
	fi
}

# install_root_module <repo> <what> <script-rel-path> [args...]
# As install_module_from_repo, for installers that require root but do not
# elevate themselves. A separate function rather than an env prefix because
# `env VAR=x fn` does not work -- these are shell functions, not binaries.
install_root_module() {
	ROOT_MODE=sudo install_module_from_repo "$@"
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

# guard-lib provides guardctl, which the hosts guards and the shutdown timer
# both hard-depend on. It must land BEFORE them: setup_midnight_shutdown.sh
# dies with "guardctl not found on PATH" otherwise, which used to make the
# midnight-shutdown module fail on every fresh machine.
#
# guard-lib is not its own repo -- it is a subdirectory of github.com/kuhyx/utils,
# so the handle is "utils". Asking for "guard-lib" would resolve to ~/guard-lib
# and derive a clone URL that does not exist.
run_installer "Guard library (guardctl)" \
	install_root_module utils "Guard library" guard-lib/install.sh

run_installer "Workout screen locker" \
	install_module_from_repo screen-locker "Workout screen locker" install_systemd.sh

run_installer "Hosts blocking" \
	install_module_from_repo hosts-blocker "Hosts blocking" install.sh

run_installer "Midnight shutdown timer" \
	install_module_from_repo digital-wellbeing "Midnight shutdown timer" setup_midnight_shutdown.sh

# ═══════════════════════════════════════════════════════════════════════════════
# SECONDARY MODULES (prompted unless --all / --none)
# ═══════════════════════════════════════════════════════════════════════════════
printf '\n%s\n' "$(bold "Secondary modules (${SECONDARY_MODE})…")"

ask_install "Steam backlog enforcer" \
	install_module_from_repo steam-backlog-enforcer "Steam backlog enforcer" install.sh

ask_install "Pacman wrapper" \
	install_module_from_repo digital-wellbeing "Pacman wrapper" pacman/install_pacman_wrapper.sh

ask_install "i3 configuration" \
	bash "$LINUX_CONFIG/i3/install.sh"

ask_install "Compulsive opening blockade" \
	install_root_module digital-wellbeing "Compulsive opening blockade" block_compulsive_opening.sh install

# ═══════════════════════════════════════════════════════════════════════════════
print_summary
