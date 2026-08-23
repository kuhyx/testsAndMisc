#!/bin/bash
# Install Unreal MCP and connect it to VS Code (via Continue MCP) on Arch Linux
# - Installs deps: git, jq, uv, python
# - Clones https://github.com/chongdashu/unreal-mcp
# - Creates a launcher: ~/.local/bin/unreal-mcp-server
# - Configures VS Code Continue MCP: ~/.continue/config.json
# - Optional: copies UnrealMCP plugin into a specified .uproject's Plugins/

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

# Source common library for shared functions
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

# ---------- User/paths ----------
set_actual_user_vars

INSTALL_ROOT_DEFAULT="$USER_HOME/.local/share/unreal-mcp"
INSTALL_ROOT="$INSTALL_ROOT_DEFAULT"
REPO_URL="https://github.com/chongdashu/unreal-mcp.git"
REPO_DIR="" # will be set after INSTALL_ROOT known

PROJECT_UPROJECT=""     # optional: path to .uproject
RESOLVED_PROJECT_DIR="" # directory containing the resolved .uproject
CONFIGURE_CONTINUE=true
CONFIGURE_VSCODE_USER=true
FORCE_UPDATE=false

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
fail() {
  echo "[ERROR] $*" >&2
  exit 1
}

usage() {
  cat << EOF
Usage: $SCRIPT_NAME [options]

Options:
  --install-dir DIR        Install root for repo (default: $INSTALL_ROOT_DEFAULT)
  --project PATH           Path to your Unreal project (.uproject file) or a directory containing one
                           Copies UnrealMCP plugin into this Unreal project
  --no-continue            Skip configuring VS Code Continue MCP
  --no-vscode              Skip adding MCP server to VS Code user profile via --add-mcp
  --force-update           If repo exists, fetch and reset to origin/main
  -h, --help               Show this help

Examples:
  $SCRIPT_NAME --project ~/UnrealProjects/MyGame/MyGame.uproject
  $SCRIPT_NAME --install-dir "$USER_HOME/dev/unreal-mcp"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir)
      shift
      [[ $# -gt 0 ]] || fail "--install-dir requires a value"
      INSTALL_ROOT="$1"
      ;;
    --project)
      shift
      [[ $# -gt 0 ]] || fail "--project requires a path to .uproject"
      PROJECT_UPROJECT="$1"
      ;;
    --no-continue)
      CONFIGURE_CONTINUE=false
      ;;
    --no-vscode)
      CONFIGURE_VSCODE_USER=false
      ;;
    --force-update)
      FORCE_UPDATE=true
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
  shift
done

REPO_DIR="$INSTALL_ROOT/unreal-mcp"

# ---------- Dependencies ----------
require_cmd() { command -v "$1" > /dev/null 2>&1; }

ensure_packages_arch() {
  # Install with pacman using sudo when needed; keep idempotent with --needed
  local pkgs=(git jq uv python rsync)
  local to_install=()
  for p in "${pkgs[@]}"; do
    if ! pacman -Qi "$p" > /dev/null 2>&1; then
      to_install+=("$p")
    fi
  done
  if [[ ${#to_install[@]} -gt 0 ]]; then
    log "Installing packages: ${to_install[*]}"
    if [[ $EUID -eq 0 ]]; then
      pacman -S --noconfirm --needed "${to_install[@]}"
    else
      sudo pacman -S --noconfirm --needed "${to_install[@]}"
    fi
  else
    log "All required packages already installed"
  fi
}

check_python_version() {
  if require_cmd python; then
    local v
    v=$(python -V 2>&1 | awk '{print $2}')
  elif require_cmd python3; then
    local v
    v=$(python3 -V 2>&1 | awk '{print $2}')
  else
    log "python not found; pacman install will provide it"
    return 0
  fi
  # Require >= 3.12 (Unreal MCP docs)
  local major minor
  major=$(echo "$v" | cut -d. -f1)
  minor=$(echo "$v" | cut -d. -f2)
  if ((major < 3 || (major == 3 && minor < 12))); then
    log "Python $v detected; installing newer python via pacman"
    if [[ $EUID -eq 0 ]]; then
      pacman -S --noconfirm --needed python
    else
      sudo pacman -S --noconfirm --needed python
    fi
  fi
}

# shellcheck source=lib/unreal_mcp_repo.sh
source "$SCRIPT_DIR/lib/unreal_mcp_repo.sh"

main() {
  log "Installing prerequisites (Arch Linux)"
  ensure_packages_arch
  check_python_version
  setup_repo
  install_launcher
  configure_continue
  install_plugin_into_project
  configure_vscode_user_mcp
  print_summary
}

main "$@"
