#!/usr/bin/env bash
# Sets up Microsoft's APT repository and installs the latest VS Code Insiders.
# Re-running this script is safe — it will update to the newest version.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)." >&2
    exit 1
fi

echo "==> Installing prerequisites..."
apt-get update -qq
apt-get install -y -qq wget gpg apt-transport-https

KEYRING=/usr/share/keyrings/microsoft-archive-keyring.gpg
SOURCES_LIST=/etc/apt/sources.list.d/vscode.list

echo "==> Adding Microsoft GPG key..."
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o "$KEYRING" --yes

echo "==> Adding VS Code repository..."
echo "deb [arch=amd64,arm64,armhf signed-by=${KEYRING}] https://packages.microsoft.com/repos/code stable main" \
    > "$SOURCES_LIST"

echo "==> Updating package lists..."
apt-get update -qq

echo "==> Installing code-insiders..."
apt-get install -y code-insiders

echo "==> Done. Installed version:"
code-insiders --version 2>/dev/null || echo "(run 'code-insiders --version' to verify)"
