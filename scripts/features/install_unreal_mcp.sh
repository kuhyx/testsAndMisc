#!/bin/bash
# Install Unreal MCP and connect it to VS Code (via Continue MCP) on Arch Linux
# - Installs deps: git, jq, uv, python
# - Clones https://github.com/chongdashu/unreal-mcp
# - Creates a launcher: ~/.local/bin/unreal-mcp-server
# - Configures VS Code Continue MCP: ~/.continue/config.json
# - Optional: copies UnrealMCP plugin into a specified .uproject's Plugins/

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

# ---------- User/paths ----------
if [[ -n ${SUDO_USER:-} ]]; then
  ACTUAL_USER="$SUDO_USER"
  USER_HOME="/home/$SUDO_USER"
else
  ACTUAL_USER="$USER"
  USER_HOME="$HOME"
fi

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

# ---------- Git clone/update ----------
setup_repo() {
  mkdir -p "$INSTALL_ROOT"
  if [[ ! -d "$REPO_DIR/.git" ]]; then
    log "Cloning unreal-mcp into $REPO_DIR"
    if require_cmd git; then
      git clone "$REPO_URL" "$REPO_DIR"
    else
      fail "git is required but not found after install"
    fi
  else
    log "Repo exists at $REPO_DIR"
    if [[ $FORCE_UPDATE == true ]]; then
      log "Updating repo with --force-update"
      git -C "$REPO_DIR" fetch origin
      git -C "$REPO_DIR" reset --hard origin/main
      git -C "$REPO_DIR" pull --rebase --autostash
    else
      log "Pulling latest changes"
      git -C "$REPO_DIR" pull --rebase --autostash
    fi
  fi

  # Ensure ownership for the real user when script ran via sudo
  if [[ $EUID -eq 0 ]]; then
    chown -R "$ACTUAL_USER:$ACTUAL_USER" "$INSTALL_ROOT"
  fi
}

# ---------- Launcher ----------
install_launcher() {
  local bin_dir="$USER_HOME/.local/bin"
  local python_dir="$REPO_DIR/Python"
  local launcher="$bin_dir/unreal-mcp-server"
  mkdir -p "$bin_dir"
  cat > "$launcher" << EOF
#!/bin/bash
set -euo pipefail
exec uv --directory "$python_dir" run unreal_mcp_server.py "${1:-}" < /dev/null
EOF
  chmod +x "$launcher"
  if [[ $EUID -eq 0 ]]; then chown "$ACTUAL_USER:$ACTUAL_USER" "$launcher"; fi
  log "Installed launcher: $launcher"
}

# ---------- VS Code: Continue MCP config ----------
configure_continue() {
  if [[ $CONFIGURE_CONTINUE != true ]]; then
    log "Skipping Continue config (--no-continue)"
    return 0
  fi

  local cont_dir="$USER_HOME/.continue"
  local cont_cfg="$cont_dir/config.json"
  local python_dir="$REPO_DIR/Python"
  mkdir -p "$cont_dir"

  # Base JSON when no config exists
  local tmp_file
  tmp_file="$(mktemp)"
  if [[ ! -f $cont_cfg ]]; then
    cat > "$tmp_file" << JSON
{
  "mcpServers": {
    "unrealMCP": {
      "command": "uv",
      "args": ["--directory", "$python_dir", "run", "unreal_mcp_server.py"]
    }
  }
}
JSON
    mv "$tmp_file" "$cont_cfg"
  else
    # Merge using jq: ensure .mcpServers exists, then set/overwrite unrealMCP
    if ! require_cmd jq; then
      fail "jq is required to merge ~/.continue/config.json"
    fi
    jq --arg dir "$python_dir" '
      .mcpServers = (.mcpServers // {}) |
      .mcpServers.unrealMCP = {
        command: "uv",
        args: ["--directory", $dir, "run", "unreal_mcp_server.py"]
      }
    ' "$cont_cfg" > "$tmp_file" && mv "$tmp_file" "$cont_cfg"
  fi

  if [[ $EUID -eq 0 ]]; then chown "$ACTUAL_USER:$ACTUAL_USER" "$cont_cfg"; fi
  log "Configured Continue MCP at: $cont_cfg"
}

# ---------- VS Code user MCP (native) ----------
configure_vscode_user_mcp() {
  if [[ $CONFIGURE_VSCODE_USER != true ]]; then
    log "Skipping VS Code user MCP config (--no-vscode)"
    return 0
  fi

  if ! require_cmd jq; then
    fail "jq is required to compose VS Code --add-mcp JSON and to parse profiles"
  fi

  local python_dir="$REPO_DIR/Python"
  local json
  json=$(jq -n --arg dir "$python_dir" '{name:"unrealMCP", command:"uv", args:["--directory", $dir, "run", "unreal_mcp_server.py"]}')

  # Handle multiple VS Code variants if present
  local candidates=(code code-insiders codium)
  local found_any=false
  for cli in "${candidates[@]}"; do
    if ! command -v "$cli" > /dev/null 2>&1; then
      continue
    fi
    found_any=true
    log "Registering MCP server in VS Code user profile via: $cli --add-mcp"
    if "$cli" --add-mcp "$json" > "/tmp/${cli}-add-mcp.log" 2>&1; then
      log "[$cli] user profile: unrealMCP added/updated"
    else
      sed -n '1,200p' "/tmp/${cli}-add-mcp.log" || true
      fail "[$cli] --add-mcp failed for user profile. Ensure your VS Code supports MCP or rerun with --no-vscode."
    fi

    # Detect profiles with 'unreal' (case-insensitive) and add there too
    local data_dir=""
    case "$cli" in
      code)
        data_dir="$USER_HOME/.config/Code"
        ;;
      code-insiders)
        data_dir="$USER_HOME/.config/Code - Insiders"
        ;;
      codium)
        data_dir="$USER_HOME/.config/VSCodium"
        ;;
    esac
    local profiles_json="$data_dir/User/profiles/profiles.json"
    if [[ -f $profiles_json ]]; then
      # Extract profile names matching /unreal/i
      mapfile -t unreal_profiles < <(jq -r '.profiles // [] | .[] | .name // empty | select(test("unreal"; "i"))' "$profiles_json")
      if [[ ${#unreal_profiles[@]} -gt 0 ]]; then
        log "[$cli] Found profiles with 'unreal': ${unreal_profiles[*]}"
        local name
        for name in "${unreal_profiles[@]}"; do
          log "[$cli] Adding unrealMCP to profile: $name"
          if "$cli" --profile "$name" --add-mcp "$json" > "/tmp/${cli}-add-mcp-${name// /_}.log" 2>&1; then
            log "[$cli] profile '$name': unrealMCP added/updated"
          else
            sed -n '1,200p' "/tmp/${cli}-add-mcp-${name// /_}.log" || true
            fail "[$cli] --add-mcp failed for profile '$name'."
          fi
        done
      else
        log "[$cli] No VS Code profiles with 'unreal' in name"
      fi
    else
      log "[$cli] Profiles file not found: $profiles_json (skipping profile-specific adds)"
    fi
  done

  if [[ $found_any == false ]]; then
    fail "VS Code CLI not found (code/code-insiders/codium). Install VS Code and ensure 'code' CLI is available, or run with --no-vscode to skip."
  fi
}

# ---------- Unreal Plugin copy (optional) ----------
install_plugin_into_project() {
  [[ -n $PROJECT_UPROJECT ]] || return 0
  local upath="$PROJECT_UPROJECT"
  if [[ -d $upath ]]; then
    # Resolve .uproject in the provided directory
    mapfile -t _uprojects < <(find "$upath" -maxdepth 1 -type f -name "*.uproject" 2> /dev/null || true)
    if [[ ${#_uprojects[@]} -eq 0 ]]; then
      fail "--project directory '$upath' contains no .uproject files"
    elif [[ ${#_uprojects[@]} -gt 1 ]]; then
      printf '[ERROR] Multiple .uproject files found in %s:\n' "$upath" >&2
      printf '  - %s\n' "${_uprojects[@]}" >&2
      fail "Please pass the specific .uproject path to --project"
    else
      upath="${_uprojects[0]}"
      log "Resolved .uproject: $upath"
    fi
  elif [[ -f $upath ]]; then
    true
  else
    fail "--project path does not exist: $upath"
  fi
  if [[ ${upath##*.} != "uproject" ]]; then
    fail "--project must point to a .uproject file (got: $upath)"
  fi
  local proj_dir
  proj_dir="$(cd "$(dirname "$upath")" && pwd)"
  RESOLVED_PROJECT_DIR="$proj_dir"
  local src_plugin="$REPO_DIR/MCPGameProject/Plugins/UnrealMCP"
  local dst_plugin="$proj_dir/Plugins/UnrealMCP"
  if [[ ! -d $src_plugin ]]; then
    fail "Source plugin not found at $src_plugin (did repo layout change?)"
  fi
  mkdir -p "$proj_dir/Plugins"
  log "Copying UnrealMCP plugin to project: $dst_plugin"
  rsync -a --delete "$src_plugin/" "$dst_plugin/"
  # Set ownership back to actual user if run as root
  if [[ $EUID -eq 0 ]]; then chown -R "$ACTUAL_USER:$ACTUAL_USER" "$proj_dir/Plugins"; fi
  log "Plugin installed. Enable it from Unreal Editor (Edit > Plugins) if needed."
}

# ---------- Summary ----------
print_summary() {
  local python_dir="$REPO_DIR/Python"
  local plugin_dest="N/A"
  if [[ -n $RESOLVED_PROJECT_DIR ]]; then
    plugin_dest="$RESOLVED_PROJECT_DIR/Plugins/UnrealMCP"
  fi
  cat << EOF
============================================
Unreal MCP setup complete
============================================

Repo:        $REPO_DIR
Python dir:  $python_dir
Launcher:    $USER_HOME/.local/bin/unreal-mcp-server

VS Code (Continue) MCP configured: ${CONFIGURE_CONTINUE}
  - File: $USER_HOME/.continue/config.json
  - Server ID: unrealMCP

VS Code (User profile) MCP configured: ${CONFIGURE_VSCODE_USER}
  - Command used: code --add-mcp '{"name":"unrealMCP", "command":"uv", "args":["--directory","$python_dir","run","unreal_mcp_server.py"]}'

Optional usage:
  - Run server manually: unreal-mcp-server
  - In VS Code with Continue installed, the unrealMCP server will auto-start when needed.

Unreal plugin:
  - Source: MCPGameProject/Plugins/UnrealMCP
  - If you provided --project, the plugin was copied to: $plugin_dest
  - In the Unreal Editor: Edit > Plugins > search "UnrealMCP" and enable. Restart when prompted.

Notes:
  - Ensure you have Unreal Engine 5.5+ installed.
  - The Python server listens to the Unreal plugin on TCP port 55557 by default.
  - For other MCP clients (Claude Desktop, Cursor, Windsurf), copy the JSON snippet from the repo README to their config locations.
EOF
}

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
