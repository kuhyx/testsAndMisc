#!/bin/bash

# ============================================================================
# setup_dwm.sh — download, configure (i3-like), build & install suckless dwm
# ============================================================================
# Installs dwm ALONGSIDE the existing i3 setup. i3 is never touched; dwm shows
# up as a separate session you can boot into (see switch-wm).
#
# SOURCE OF TRUTH: every customisation lives as a real, version-controlled file
# under  linux_configuration/dwm/  and is COPIED onto a fresh upstream clone:
#   dwm/config.h            -> the i3-like config (keys, colours, rules)
#   dwm/pointer-confine.c   -> XFixes cursor-lock helper for fullscreen gaming
#   dwm/bin/*               -> dwm-session, dwmstatus, dwm-rebuild, switch-wm,
#                              pconfine-auto
#   dwm/patches/*.patch     -> human-readable form of the two dwm.c changes that
#                              this script applies with perl (focus-on-click +
#                              fullscreen pointer-confine)
#
# Bleeding edge: upstream master is cloned and `git reset --hard`'d on every run;
# our files are copied/applied on top, so `git pull && rebuild` keeps working.
# Edit the files in dwm/ and re-run this script to apply a permanent change.
# ============================================================================

set -euo pipefail

readonly SRC_DIR="${HOME}/.local/src/dwm"
readonly DWM_REPO="https://git.suckless.org/dwm"
readonly XSESSION="/usr/share/xsessions/dwm.desktop"
readonly BIN_SESSION="/usr/local/bin/dwm-session"
readonly BIN_STATUS="/usr/local/bin/dwmstatus"
readonly BIN_REBUILD="/usr/local/bin/dwm-rebuild"
readonly BIN_SWITCH="/usr/local/bin/switch-wm"
readonly BIN_CONFINE="/usr/local/bin/pointer-confine"
readonly BIN_CONFINE_AUTO="/usr/local/bin/pconfine-auto"

# Repo dir holding our versioned dwm source (resolved from this script's path,
# so it works regardless of the caller's CWD): features/ -> ... -> dwm/.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
REPO_DWM_DIR="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)/dwm"
readonly REPO_DWM_DIR

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!! \033[0m %s\n' "$*" >&2; }

# ---------------------------------------------------------------------------
# 0. Confirm the versioned dwm source files are present in the repo before we
#    touch anything. Fail fast and clearly if the checkout is incomplete.
# ---------------------------------------------------------------------------
validate_repo_files() {
    local f missing=()
    local need=(
        "config.h"
        "pointer-confine.c"
        "bin/dwm-session"
        "bin/dwmstatus"
        "bin/dwm-rebuild"
        "bin/switch-wm"
        "bin/pconfine-auto"
    )
    for f in "${need[@]}"; do
        [[ -f "${REPO_DWM_DIR}/${f}" ]] || missing+=("${REPO_DWM_DIR}/${f}")
    done
    if ((${#missing[@]})); then
        warn "Missing required dwm source files (is the repo checkout complete?):"
        printf '    %s\n' "${missing[@]}" >&2
        exit 1
    fi
    log "dwm source files present in repo: $REPO_DWM_DIR"
}

# ---------------------------------------------------------------------------
# 1. Dependencies — DETECT ONLY, never auto-install.
#    This system's `pacman` is a digital-wellbeing wrapper that deadlocks when
#    driven non-interactively (stdin /dev/null + the /etc/hosts guard hooks
#    re-enter pacman and futex-deadlock on db.lck). So we never run `pacman -S`
#    from here. We only do a single read-only `pacman -Qq` (no db lock, no
#    transaction hooks) to check what's present, and tell the user to install
#    anything missing themselves, interactively, the way the wrapper expects.
# ---------------------------------------------------------------------------
install_deps() {
    log "Checking dependencies (read-only; the pacman wrapper is NOT invoked for installs)…"
    local required=(libx11 libxft libxinerama gcc make dmenu terminator)
    local optional=(xorg-xsetroot)   # status bar only — dwm runs fine without it
    local installed missing_req=() missing_opt=() p
    installed="$(pacman -Qq 2>/dev/null)" || installed=""

    for p in "${required[@]}"; do
        grep -qxF "$p" <<<"$installed" || missing_req+=("$p")
    done
    for p in "${optional[@]}"; do
        grep -qxF "$p" <<<"$installed" || missing_opt+=("$p")
    done

    if ((${#missing_req[@]})); then
        warn "Missing REQUIRED packages: ${missing_req[*]}"
        warn "Install them yourself (interactively), then re-run this script:"
        warn "    sudo pacman -S ${missing_req[*]}"
        exit 1
    fi
    if ((${#missing_opt[@]})); then
        warn "Optional status-bar package missing: ${missing_opt[*]} — dwm will still run."
        warn "For the status bar, install it later in your terminal:"
        warn "    sudo pacman -S ${missing_opt[*]}"
    fi
    log "All required dependencies present."
}

# ---------------------------------------------------------------------------
# 2. Fetch the LATEST dwm source (bleeding edge — always upstream master HEAD)
#    into a persistent, user-owned location so it can be re-edited and
#    recompiled at will. On re-run we hard-reset to origin/master to pull in
#    upstream changes; our config.h is untracked, so the reset never touches it.
# ---------------------------------------------------------------------------
fetch_dwm() {
    if [[ -d "$SRC_DIR/.git" ]]; then
        log "Updating dwm to the latest upstream master (bleeding edge)…"
        git -C "$SRC_DIR" fetch --quiet origin
        # config.h is untracked, so a hard reset of tracked files preserves it.
        git -C "$SRC_DIR" reset --hard --quiet origin/master
    else
        log "Cloning the latest dwm master into $SRC_DIR…"
        mkdir -p "$(dirname "$SRC_DIR")"
        git clone --quiet "$DWM_REPO" "$SRC_DIR"
    fi
    log "dwm source now at commit $(git -C "$SRC_DIR" rev-parse --short HEAD) ($(git -C "$SRC_DIR" log -1 --format=%cd --date=short))"
}

# shellcheck source=lib/dwm_config.sh
source "$SCRIPT_DIR/lib/dwm_config.sh"

main() {
    validate_repo_files
    install_deps
    fetch_dwm
    install_config
    heal_config
    apply_focusonclick
    apply_fullscreen_confine_hook
    build_install
    build_pointer_confine
    write_session_files
    verify
    print_summary
}

main "$@"
