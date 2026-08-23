#!/usr/bin/env bash

# Fix common Arch Linux performance issues on laptops with NVIDIA hybrid graphics
#
# Issues addressed:
# 1. NVIDIA xorg RenderAccel disabled → forces software rendering, Xorg eats 30%+ CPU
# 2. CPU governor stuck on powersave → AMD Ryzen throttled despite AC power
# 3. No power management daemon → inconsistent CPU/GPU power state management
# 4. Systemd journal bloated (>1GiB) → wastes disk I/O
# 5. NetworkManager-wait-online.service → adds ~6s to every boot for no benefit
# 6. media-organizer.service broken → wrong script path & user, fails every boot
#
# Usage:
#   ./fix_arch_performance.sh                  # Apply all fixes
#   ./fix_arch_performance.sh --dry-run        # Show what would be done
#   ./fix_arch_performance.sh --interactive    # Prompt before each fix
#   ./fix_arch_performance.sh -h               # Show help
#
# Safe to re-run: all fixes are idempotent.
# Requires reboot/re-login for xorg changes to take effect.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

parse_interactive_args "$@"
shift "$COMMON_ARGS_SHIFT"

DRY_RUN=false
for arg in "$@"; do
	case "$arg" in
	--dry-run)
		DRY_RUN=true
		;;
	-h | --help)
		cat <<'EOF'
fix_arch_performance.sh - Fix common Arch Linux laptop performance issues

Usage: fix_arch_performance.sh [OPTIONS]

Options:
  --dry-run          Show what would be done without making changes
  -i, --interactive  Prompt before each fix
  -h, --help         Show this help message

Fixes applied:
  1. Enable NVIDIA hardware acceleration (RenderAccel true)
  2. Install/enable power-profiles-daemon, set performance profile
  3. Vacuum systemd journal to 300M, cap future size
  4. Disable NetworkManager-wait-online.service (saves ~6s boot)
  5. Fix media-organizer.service (correct path and user)

All fixes are idempotent and safe to re-run.
Xorg fixes require reboot/re-login to take effect.
EOF
		exit 0
		;;
	esac
done

require_root "$@"

print_setup_header "Arch Linux Performance Fix"

FIXES_APPLIED=0
FIXES_SKIPPED=0

# ---------------------------------------------------------------------------
# Helper: run or print a fix depending on --dry-run / --interactive
# ---------------------------------------------------------------------------
apply_fix() {
	local description="$1"
	shift

	echo ""
	log_info "$description"

	if [[ $DRY_RUN == "true" ]]; then
		echo "  [dry-run] Would run: $*"
		return 0
	fi

	if [[ $INTERACTIVE_MODE == "true" ]]; then
		if ! ask_yes_no "  Apply this fix?"; then
			log_warn "Skipped."
			((FIXES_SKIPPED++)) || true
			return 0
		fi
	fi

	if "$@"; then
		log_ok "Done."
		((FIXES_APPLIED++)) || true
	else
		log_error "Failed (non-fatal, continuing)."
	fi
}

# ===================================================================
# Fix 1: NVIDIA RenderAccel
# ===================================================================
fix_nvidia_render_accel() {
	local conf="/etc/X11/xorg.conf.d/20-nvidia.conf"

	# Check if RenderAccel is already correct
	if [[ -f $conf ]] && grep -qi 'RenderAccel.*true' "$conf"; then
		log_ok "NVIDIA RenderAccel is already enabled — skipping."
		return 0
	fi

	mkdir -p /etc/X11/xorg.conf.d

	# Back up the current config if it exists and has the bad setting
	if [[ -f $conf ]]; then
		cp "$conf" "${conf}.bak.$(date +%Y%m%d_%H%M%S)"
	fi

	cat >"$conf" <<'XORGEOF'
# NVIDIA configuration - hardware acceleration enabled
# Disabling RenderAccel forces Xorg into software rendering,
# causing 30%+ CPU usage on desktop. Keep this set to "true".
Section "Device"
    Identifier "NVIDIA Card"
    Driver "nvidia"
    Option "RenderAccel" "true"
EndSection
XORGEOF

	# Clean up old backups left by nvidia_troubleshoot.sh
	rm -f /etc/X11/xorg.conf.d/20-nvidia.conf.backup.* 2>/dev/null || true
	return 0
}

# ===================================================================
# Fix 2: Power management daemon + performance profile
# ===================================================================
fix_power_management() {
	# Install power-profiles-daemon if missing
	if ! pacman -Qi power-profiles-daemon >/dev/null 2>&1; then
		log_info "Installing power-profiles-daemon..."
		pacman -S --needed --noconfirm power-profiles-daemon
	fi

	# Enable and start the service
	if ! systemctl is-enabled power-profiles-daemon.service >/dev/null 2>&1; then
		systemctl enable --now power-profiles-daemon.service
	elif ! systemctl is-active power-profiles-daemon.service >/dev/null 2>&1; then
		systemctl start power-profiles-daemon.service
	fi

	# Resolve TLP conflict if both are enabled
	if systemctl is-enabled tlp.service >/dev/null 2>&1; then
		log_warn "TLP conflicts with power-profiles-daemon — disabling TLP."
		systemctl disable --now tlp.service
	fi

	# Set performance profile (appropriate when plugged in with strong hardware)
	sleep 1
	if has_cmd powerprofilesctl; then
		powerprofilesctl set performance
		log_info "Power profile set to: $(powerprofilesctl get)"
	fi

	return 0
}

# shellcheck source=lib/arch_perf_fixes.sh
source "$SCRIPT_DIR/lib/arch_perf_fixes.sh"

main() {
	apply_fix \
		"Fix 1/5: Enable NVIDIA hardware acceleration (RenderAccel → true)" \
		fix_nvidia_render_accel

	apply_fix \
		"Fix 2/5: Install/enable power-profiles-daemon + set performance profile" \
		fix_power_management

	apply_fix \
		"Fix 3/5: Vacuum journal logs + set permanent 300M size cap" \
		fix_journal

	apply_fix \
		"Fix 4/5: Disable NetworkManager-wait-online.service (~6s boot saving)" \
		fix_nm_wait_online

	apply_fix \
		"Fix 5/5: Fix media-organizer.service (correct path and user)" \
		fix_media_organizer

	# ---------------------------------------------------------------
	# Summary
	# ---------------------------------------------------------------
	echo ""
	echo "=============================="
	echo " Performance Fix Summary"
	echo "=============================="

	if [[ $DRY_RUN == "true" ]]; then
		log_info "Dry-run mode — no changes were made."
	else
		log_ok "Fixes applied: $FIXES_APPLIED"
		if [[ $FIXES_SKIPPED -gt 0 ]]; then
			log_warn "Fixes skipped: $FIXES_SKIPPED"
		fi
	fi

	echo ""
	log_info "Reboot or re-login for xorg changes (Fix 1) to take effect."
	log_info "After reboot, verify with: diagnose_arch_performance.sh"
}

main
