#!/usr/bin/env bash

# Configure Thorium/Chromium to auto-allow unityhub:// deep links from Unity login origins.
# This avoids missed external-protocol prompts and helps Unity Hub receive the token after web login.
#
# Features:
# - Install a system policy file (requires sudo) with AutoLaunchProtocolsFromOrigins for unityhub
# - Optionally set Thorium as default browser
# - Optionally restart Thorium
# - Non-destructive: does not edit your Thorium profile Preferences
#
# Usage:
#   bash Bash/fix_thorium_unity.sh --policy           # Install policy (sudo)
#   bash Bash/fix_thorium_unity.sh --set-default      # Set default browser to Thorium
#   bash Bash/fix_thorium_unity.sh --restart          # Restart Thorium
#   bash Bash/fix_thorium_unity.sh --policy --restart # Install policy and restart browser

set -euo pipefail
IFS=$'\n\t'

GREEN="\033[1;32m"; YELLOW="\033[1;33m"; RED="\033[1;31m"; BLUE="\033[1;34m"; NC="\033[0m"
log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERR ]${NC} $*" 1>&2; }

DO_POLICY=false
SET_DEFAULT=false
DO_RESTART=false

usage() {
  cat <<EOF
fix_thorium_unity.sh - Auto-allow unityhub:// from Unity origins in Thorium/Chromium

Options:
  --policy        Install a managed policy to auto-launch unityhub from:
                  - https://id.unity.com
                  - https://login.unity.com
                  - https://unity.com
                  Requires sudo (writes to /etc/*/policies/managed/).
  --set-default   Set thorium-browser.desktop as the default browser
  --restart       Kill and restart Thorium
  -h, --help      Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --policy) DO_POLICY=true; shift ;;
    --set-default) SET_DEFAULT=true; shift ;;
    --restart) DO_RESTART=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) log_error "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

ensure_sudo() {
  if ! command -v sudo >/dev/null 2>&1; then
    log_error "sudo not found; cannot install system policy. Use --set-default or run from root."
    exit 1
  fi
}

install_policy() {
  ensure_sudo
  # Candidate policy directories (most common for Chromium forks)
  local candidates=(
    "/etc/thorium-browser/policies/managed"      # Thorium
    "/etc/chromium/policies/managed"             # Chromium
    "/etc/opt/chrome/policies/managed"           # Google Chrome
  )
  local wrote_any=false
  for target in "${candidates[@]}"; do
    log_info "Installing policy into: $target"
    sudo mkdir -p "$target"
    local policy_file="$target/unityhub-policy.json"
    sudo tee "$policy_file" >/dev/null <<'JSON'
{
  "AutoLaunchProtocolsFromOrigins": [
    { "protocol": "unityhub", "origin": "https://id.unity.com", "allow": true },
    { "protocol": "unityhub", "origin": "https://login.unity.com", "allow": true },
    { "protocol": "unityhub", "origin": "https://unity.com", "allow": true },
    { "protocol": "unity", "origin": "https://id.unity.com", "allow": true },
    { "protocol": "unity", "origin": "https://login.unity.com", "allow": true },
    { "protocol": "unity", "origin": "https://unity.com", "allow": true }
  ]
}
JSON
    # Some Chromium builds cache policies; no explicit reload on Linux. Restarting browser suffices.
    log_ok "Policy written: $policy_file"
    wrote_any=true
  done
  if [[ "$wrote_any" != true ]]; then
    log_warn "Policy may not have been written. No candidate directories processed."
  fi
}

set_default_browser() {
  if command -v xdg-settings >/dev/null 2>&1; then
    # Prefer the upstream desktop id if it exists
    local desktop="thorium-browser.desktop"
    if [[ ! -f "/usr/share/applications/$desktop" && -f "$HOME/.local/share/applications/$desktop" ]]; then
      : # keep desktop as is
    elif [[ ! -f "/usr/share/applications/$desktop" && ! -f "$HOME/.local/share/applications/$desktop" ]]; then
      log_warn "thorium-browser.desktop not found; leaving default browser unchanged."
      return
    fi
    log_info "Setting default browser to $desktop"
    xdg-settings set default-web-browser "$desktop" || log_warn "Failed to set default browser via xdg-settings"
    log_ok "Default browser set to: $(xdg-settings get default-web-browser 2>/dev/null || echo "$desktop")"
  else
    log_warn "xdg-settings not found; cannot set default browser automatically."
  fi
}

restart_thorium() {
  # Kill Thorium processes and start fresh
  log_info "Restarting Thorium..."
  pkill -9 -f 'thorium-browser' 2>/dev/null || true
  # Also kill unityhub-bin's embedded Chromium if any leftover (harmless)
  pkill -9 -f 'unityhub-bin' 2>/dev/null || true
  # Start Thorium detached if available
  if command -v thorium-browser >/dev/null 2>&1; then
    nohup thorium-browser >/dev/null 2>&1 & disown || true
  fi
  log_ok "Thorium restart attempted."
}

main() {
  $DO_POLICY && install_policy
  $SET_DEFAULT && set_default_browser
  $DO_RESTART && restart_thorium

  cat <<'NEXT'
---
Next steps:
- Open Unity Hub, click Sign in, complete in Thorium; when prompted, allow the unityhub link to open the app.
- If Thorium still does not prompt, the installed policy will auto-allow from Unity origins on next restart.
- You can also trigger a test link: xdg-open 'unityhub://v1/editor-signin'
---
NEXT
}

main "$@"
