#!/usr/bin/env bash

# Optimize Arch Linux desktop for maximum performance on high-end hardware
#
# Tuning areas:
#  1. CPU scheduler — performance governor on all cores
#  2. I/O scheduler — optimal scheduler per drive type (none for NVMe, mq-deadline for SATA SSD)
#  3. Memory / swap — lower swappiness, tune dirty page writeback for responsiveness
#  4. Kernel network — TCP BBR, fastopen, larger buffers
#  5. Filesystem — fstrim timer, noatime advisory
#  6. NVIDIA GPU — max performance level via persistence mode
#  7. Kernel mitigations — option to disable CPU vulnerability mitigations for extra speed
#  8. Boot speed — disable unnecessary wait-online services
#  9. Journal housekeeping — cap at 300M
# 10. Process scheduler — install ananicy-cpp for automatic nice/ionice/scheduling
#
# Usage:
#   ./optimize_arch_desktop.sh                  # Apply safe optimizations
#   ./optimize_arch_desktop.sh --dry-run        # Show what would be done
#   ./optimize_arch_desktop.sh --interactive    # Prompt before each tweak
#   ./optimize_arch_desktop.sh --aggressive     # Include CPU mitigation disable (risk: security)
#   ./optimize_arch_desktop.sh -h               # Show help
#
# All tweaks are idempotent and safe to re-run.
# Some kernel parameter changes require a reboot to take full effect.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../../lib/common.sh
source "$SCRIPT_DIR/../../lib/common.sh"

parse_interactive_args "$@"
shift "$COMMON_ARGS_SHIFT"

DRY_RUN=false
AGGRESSIVE=false

for arg in "$@"; do
	case "$arg" in
	--dry-run)
		DRY_RUN=true
		;;
	--aggressive)
		AGGRESSIVE=true
		;;
	-h | --help)
		cat <<'EOF'
optimize_arch_desktop.sh - Squeeze maximum performance from an Arch Linux desktop

Usage: optimize_arch_desktop.sh [OPTIONS]

Options:
  --dry-run          Show what would be done without making changes
  --aggressive       Also disable CPU vulnerability mitigations (trades security for speed)
  -i, --interactive  Prompt before each optimization
  -h, --help         Show this help message

Optimizations applied:
   1. Set CPU governor to performance on all cores
   2. Set optimal I/O scheduler per drive (none/mq-deadline)
   3. Tune vm.swappiness, dirty ratios, vfs_cache_pressure via sysctl
   4. Enable TCP BBR congestion control + fastopen + buffer tuning
   5. Enable fstrim.timer for SSD TRIM maintenance
   6. Set NVIDIA GPU to max performance level (persistence mode)
   7. [--aggressive] Disable CPU vulnerability mitigations
   8. Disable NetworkManager-wait-online.service for faster boot
   9. Vacuum & cap systemd journal at 300M
  10. Install/enable ananicy-cpp for automatic process prioritization

All optimizations are idempotent. Re-run safely at any time.
EOF
		exit 0
		;;
	esac
done

require_root "$@"

print_setup_header "Arch Linux Desktop Performance Optimizer"

TWEAKS_APPLIED=0
TWEAKS_SKIPPED=0

# ---------------------------------------------------------------------------
# Helper: apply or preview a tweak
# ---------------------------------------------------------------------------
apply_tweak() {
	local description="$1"
	shift

	echo ""
	log_info "$description"

	if [[ $DRY_RUN == "true" ]]; then
		echo "  [dry-run] Would run: $*"
		return 0
	fi

	if [[ $INTERACTIVE_MODE == "true" ]]; then
		if ! ask_yes_no "  Apply this optimization?"; then
			log_warn "Skipped."
			((TWEAKS_SKIPPED++)) || true
			return 0
		fi
	fi

	if "$@"; then
		log_ok "Done."
		((TWEAKS_APPLIED++)) || true
	else
		log_error "Failed (non-fatal, continuing)."
	fi
}

# shellcheck source=lib/arch_cpu.sh
source "$SCRIPT_DIR/lib/arch_cpu.sh"
# shellcheck source=lib/arch_sysctl.sh
source "$SCRIPT_DIR/lib/arch_sysctl.sh"
# shellcheck source=lib/arch_hardware.sh
source "$SCRIPT_DIR/lib/arch_hardware.sh"

main() {
	apply_tweak \
		"Tweak  1/10: Set CPU governor to performance on all cores" \
		tweak_cpu_governor

	apply_tweak \
		"Tweak  2/10: Optimize I/O scheduler per drive type" \
		tweak_io_scheduler

	apply_tweak \
		"Tweak  3/10: Tune VM/memory sysctl for desktop responsiveness" \
		tweak_vm_sysctl

	apply_tweak \
		"Tweak  4/10: Enable TCP BBR + fastopen + larger buffers" \
		tweak_network_sysctl

	apply_tweak \
		"Tweak  5/10: Enable fstrim.timer for SSD TRIM maintenance" \
		tweak_fstrim

	apply_tweak \
		"Tweak  6/10: NVIDIA GPU persistence mode + max performance" \
		tweak_nvidia_gpu

	apply_tweak \
		"Tweak  7/10: CPU vulnerability mitigations (--aggressive only)" \
		tweak_mitigations

	apply_tweak \
		"Tweak  8/10: Disable NetworkManager-wait-online (faster boot)" \
		tweak_nm_wait_online

	apply_tweak \
		"Tweak  9/10: Vacuum & cap systemd journal at 300M" \
		tweak_journal

	apply_tweak \
		"Tweak 10/10: Enable ananicy-cpp process prioritization" \
		tweak_ananicy

	# ---------------------------------------------------------------
	# Summary
	# ---------------------------------------------------------------
	echo ""
	echo "=============================="
	echo " Desktop Optimization Summary"
	echo "=============================="

	if [[ $DRY_RUN == "true" ]]; then
		log_info "Dry-run mode — no changes were made."
	else
		log_ok "Optimizations applied: $TWEAKS_APPLIED"
		if [[ $TWEAKS_SKIPPED -gt 0 ]]; then
			log_warn "Optimizations skipped: $TWEAKS_SKIPPED"
		fi
	fi

	echo ""

	# Advisory: check for noatime
	local root_mount_opts
	root_mount_opts=$(findmnt -n -o OPTIONS / 2>/dev/null || true)
	if [[ -n $root_mount_opts ]] && ! echo "$root_mount_opts" | grep -q 'noatime'; then
		log_info "Tip: Your root filesystem does not use 'noatime'."
		log_info "  Adding 'noatime' to /etc/fstab can reduce unnecessary disk writes."
		log_info "  (Change 'relatime' or 'atime' to 'noatime' in /etc/fstab, then reboot)"
	fi

	if [[ $AGGRESSIVE == "true" ]]; then
		log_warn "Aggressive mode was used — mitigations=off trades security for speed."
	fi

	echo ""
	log_info "Reboot recommended for kernel parameter and boot loader changes to take effect."
	log_info "Verify after reboot with: diagnose_arch_performance.sh"
}

main
