#!/usr/bin/env bash

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

RED="\033[31m"
YELLOW="\033[33m"
BLUE="\033[34m"
RESET="\033[0m"

info() {
  printf "%b[%s]%b %s\n" "$BLUE" "$SCRIPT_NAME" "$RESET" "$*"
}

warn() {
  printf "%b[%s]%b %s\n" "$YELLOW" "$SCRIPT_NAME" "$RESET" "$*" >&2
}

error() {
  printf "%b[%s]%b %s\n" "$RED" "$SCRIPT_NAME" "$RESET" "$*" >&2
}

require_command() {
  local cmd="$1"
  local package_hint="${2:-}"

  if ! command -v "$cmd" > /dev/null 2>&1; then
    if [[ -n $package_hint ]]; then
      error "Missing command '$cmd'. Try installing the package: $package_hint"
    else
      error "Missing command '$cmd'."
    fi
    exit 1
  fi
}

ensure_pacman_packages() {
  local packages=("python" "git" "curl" "jq" "code")
  local missing=()
  for pkg in "${packages[@]}"; do
    if ! pacman -Qi "$pkg" > /dev/null 2>&1; then
      missing+=("$pkg")
    fi
  done

  if ((${#missing[@]} > 0)); then
    info "Installing required packages with pacman: ${missing[*]}"
    sudo pacman -S --needed --noconfirm "${missing[@]}"
  else
    info "All required pacman packages are already installed."
  fi
}

install_uv() {
  if command -v uv > /dev/null 2>&1; then
    info "uv is already installed."
    return
  fi

  info "Installing uv toolchain manager via official installer."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  local local_bin="$HOME/.local/bin"
  if [[ :$PATH: != *":$local_bin:"* ]]; then
    warn "Adding $local_bin to PATH in ~/.profile and ~/.zshrc. Open a new shell to apply."
    printf "\nexport PATH=\"\$HOME/.local/bin:\$PATH\"\n" >> "$HOME/.profile"
    printf "\nexport PATH=\"\$HOME/.local/bin:\$PATH\"\n" >> "$HOME/.zshrc"
  fi
}

ensure_unity_hub() {
  if command -v unityhub > /dev/null 2>&1; then
    info "Unity Hub already installed."
    return
  fi

  if command -v yay > /dev/null 2>&1; then
    info "Installing Unity Hub from AUR using yay."
    yay -S --needed --noconfirm unityhub
  elif command -v flatpak > /dev/null 2>&1; then
    warn "Unity Hub not found. Attempting Flatpak installation."
    flatpak install -y com.unity.UnityHub || warn "Flatpak installation failed. Install Unity Hub manually via https://unity.com/download"
  else
    warn "Unity Hub not found and neither yay nor flatpak is available. Install Unity Hub manually from https://unity.com/download."
  fi
}

sync_unity_mcp_repo() {
  local data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
  local unity_mcp_root="$data_home/UnityMCP"
  local repo_dir="$unity_mcp_root/unity-mcp-repo"
  local server_link="$unity_mcp_root/UnityMcpServer"
  local candidates=(
    "UnityMcpServer"
    "UnityMcpBridge/UnityMcpServer"
    "UnityMcpBridge/UnityMcpServer~"
  )
  local server_subdir=""

  mkdir -p "$unity_mcp_root"

  if [[ -d "$repo_dir/.git" ]]; then
    info "Updating existing unity-mcp repository."
    git -C "$repo_dir" pull --ff-only
  else
    info "Cloning unity-mcp repository."
    rm -rf "$repo_dir"
    git clone --depth=1 https://github.com/CoplayDev/unity-mcp.git "$repo_dir"
  fi

  for candidate in "${candidates[@]}"; do
    if [[ -d "$repo_dir/$candidate/src" ]]; then
      server_subdir="$candidate"
      break
    fi
  done

  if [[ -z $server_subdir ]]; then
    error "UnityMcpServer src directory not found. Checked candidates: ${candidates[*]}"
    error "Repository layout may have changed. Inspect $repo_dir for the new server location."
    exit 1
  fi

  ln -sfn "$repo_dir/$server_subdir" "$server_link"
  info "UnityMcpServer synchronized at $server_link (source: $server_subdir)"
}

configure_vscode_mcp() {
  local data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
  local server_src="$data_home/UnityMCP/UnityMcpServer/src"
  local mcp_config_dir="$HOME/.config/Code/User"
  local mcp_config="$mcp_config_dir/mcp.json"
  local tmp

  if [[ ! -d $server_src ]]; then
    error "Server source directory $server_src is missing."
    exit 1
  fi

  mkdir -p "$mcp_config_dir"

  if [[ ! -f $mcp_config ]]; then
    info "Creating new VS Code MCP configuration at $mcp_config"
    echo '{}' > "$mcp_config"
  else
    info "Updating existing VS Code MCP configuration at $mcp_config"
  fi

  tmp="$(mktemp)"

  if ! jq '.' "$mcp_config" > /dev/null 2>&1; then
    error "Existing $mcp_config is not valid JSON. Please fix it before running this script again."
    exit 1
  fi

  jq \
    --arg path "$server_src" \
    '(.servers //= {}) |
         .servers.unityMCP = {
                 command: "uv",
                 args: ["--directory", $path, "run", "server.py"],
                 type: "stdio"
         }' \
    "$mcp_config" > "$tmp"

  mv "$tmp" "$mcp_config"
  info "VS Code MCP server configuration updated for UnityMCP."
}

verify_python_version() {

  require_command python "python"
  local version
  version="$(
    python - << 'PY'
import sys
print("%d.%d.%d" % sys.version_info[:3])
PY
  )"
  local major minor
  IFS='.' read -r major minor _ <<< "$version"
  if ((major < 3 || (major == 3 && minor < 12))); then
    error "Python 3.12+ is required. Detected version $version. Upgrade python before continuing."
    exit 1
  fi
  info "Python version $version satisfies requirement (>= 3.12)."
}

print_next_steps() {
  cat << 'EOT'

Next steps:
	1. Launch Unity Hub and install a Unity Editor version 2021.3 LTS or newer.
	2. Open your Unity project and add the MCP for Unity Bridge package via:
			 Window > Package Manager > + > Add package from git URL...
			 https://github.com/CoplayDev/unity-mcp.git?path=/UnityMcpBridge
	3. In Unity, open Window > MCP for Unity and run Auto-Setup. Confirm the status shows Connected ✓.
	4. Open Visual Studio Code. The MCP server entry "unityMCP" is now configured. Reload if prompted.
	5. In VS Code, open the MCP client (e.g., Copilot / Claude Code) and issue a request such as "Create a tic-tac-toe game in 3D". The Unity MCP server should respond by operating inside your Unity project.

Optional (Roslyn strict validation):
	- Install NuGetForUnity and add Microsoft.CodeAnalysis + SQLitePCLRaw packages, then define USE_ROSLYN, OR
	- Manually place Roslyn DLLs into Assets/Plugins and add USE_ROSLYN to Scripting Define Symbols.

Troubleshooting tips:
	- If VS Code cannot launch the server, ensure `uv` is on PATH and that ~/.local/bin is exported in your shell.
	- To run the server manually: `uv --directory ~/.local/share/UnityMCP/UnityMcpServer/src run server.py`
	- Verify the directory path in ~/.config/Code/User/mcp.json matches your installation.

EOT
}

main() {
  if [[ ! -f /etc/arch-release ]]; then
    error "This script is intended for Arch Linux."
    exit 1
  fi

  info "Ensuring base dependencies are installed."
  require_command sudo "sudo"
  require_command pacman "pacman"
  ensure_pacman_packages
  verify_python_version
  install_uv
  ensure_unity_hub
  sync_unity_mcp_repo
  configure_vscode_mcp
  print_next_steps
  info "Setup complete. Follow the next steps above to finish configuration inside Unity."
}

main "$@"
