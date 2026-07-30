#!/bin/bash

# ============================================================================
# Install boot-repair and its pacman gate hooks.
# ============================================================================
#
# Installs:
#   /usr/local/sbin/boot-repair                          the repair tool
#   /etc/pacman.d/hooks/05-boot-mounted-guard.hook       pre-transaction gate
#   /etc/pacman.d/hooks/99-boot-autorepair.hook          post-transaction fix
#
# boot-repair must live on the ROOT filesystem: by definition the ESP is
# unreachable when it is needed.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
readonly SCRIPT_DIR
readonly SBIN_DEST="/usr/local/sbin/boot-repair"
readonly HOOK_DIR="/etc/pacman.d/hooks"

if [[ $EUID -ne 0 ]]; then
	echo "This installer needs root; re-running with sudo..."
	exec sudo "$0" "$@"
fi

echo "=== boot-repair installer ==="

# 1. Dependencies. Everything used is in `base`, so this is a verification
#    rather than an install — but it must fail loudly if something is absent,
#    since the tool's whole point is working when the system is broken.
echo "[1/4] Checking required tools..."
missing=()
for tool in findmnt depmod modprobe tar install awk sed grep find sort; do
	command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
if [[ ${#missing[@]} -gt 0 ]]; then
	echo "  Missing: ${missing[*]}"
	echo "  Installing base utilities..."
	pacman -S --needed --noconfirm util-linux kmod tar coreutils gawk sed grep findutils
fi
# mkinitcpio is required to rebuild the initramfs.
if ! command -v mkinitcpio >/dev/null 2>&1; then
	echo "  Installing mkinitcpio..."
	pacman -S --needed --noconfirm mkinitcpio
fi
echo "  All required tools present."

# 2. The script itself.
echo "[2/4] Installing $SBIN_DEST..."
install -Dm755 "$SCRIPT_DIR/boot-repair" "$SBIN_DEST"
echo "  Installed."

# 3. Pacman hooks.
echo "[3/4] Installing pacman hooks into $HOOK_DIR..."
mkdir -p "$HOOK_DIR"
for hook in "$SCRIPT_DIR"/hooks/*.hook; do
	install -Dm644 "$hook" "$HOOK_DIR/$(basename "$hook")"
	echo "  $(basename "$hook")"
done

# 4. Prove the installed copy runs. A recovery tool that was never executed is
#    not installed, it is merely copied.
echo "[4/4] Verifying the installed copy..."
if "$SBIN_DEST" --dry-run; then
	echo "  boot-repair reports the system is consistent."
else
	echo "  boot-repair found problems (see above). Repair with: sudo $SBIN_DEST"
fi

echo "=== Installation complete ==="
echo
echo "Usage:"
echo "  sudo boot-repair              # repair now"
echo "  sudo boot-repair --dry-run    # report only"
echo
echo "In emergency mode the root filesystem is already mounted, so:"
echo "  $SBIN_DEST"
