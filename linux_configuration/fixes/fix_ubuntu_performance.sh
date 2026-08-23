#!/usr/bin/env bash

# Fix common Ubuntu performance issues on Lenovo Legion laptop with NVIDIA GPU
#
# System: Ubuntu 24.04, AMD Ryzen 7 4800H, RTX 2060 Mobile, 32GB RAM, NVMe SSD
#
# Issues addressed:
# 1. NetworkManager-wait-online.service → adds ~6.7s to every boot for no benefit
# 2. vm.swappiness=60 → too aggressive for 32GB RAM + NVMe, wastes I/O on swap
# 3. NVIDIA persistence mode off → GPU re-initializes on every nvidia operation
# 4. No earlyoom → system can hard-freeze under memory pressure (OOM killer too slow)
# 5. Failed SSSD systemd units → retry loops waste CPU, journal space
# 6. Journal potentially bloated → wastes disk I/O
# 7. No VFS/dirty page tuning → suboptimal for dev workloads on NVMe
#
# Every change creates an entry in the undo script for easy reversal.
#
# Usage:
#   sudo ./fix_ubuntu_performance.sh                # Apply all fixes
#   sudo ./fix_ubuntu_performance.sh --dry-run      # Show what would be done
#   sudo ./fix_ubuntu_performance.sh --undo          # Reverse all changes
#   sudo ./fix_ubuntu_performance.sh -h              # Show help
#
# Safe to re-run: all fixes are idempotent.

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

parse_interactive_args "$@"
shift "$COMMON_ARGS_SHIFT"

DRY_RUN=false
UNDO_MODE=false
for arg in "$@"; do
	case "$arg" in
	--dry-run)
		DRY_RUN=true
		;;
	--undo)
		UNDO_MODE=true
		;;
	-h | --help)
		cat <<'EOF'
fix_ubuntu_performance.sh - Fix common Ubuntu laptop performance issues

Usage: fix_ubuntu_performance.sh [OPTIONS]

Options:
  --dry-run          Show what would be done without making changes
  --undo             Reverse all changes (uses generated undo script)
  -i, --interactive  Prompt before each fix
  -h, --help         Show this help message

Fixes applied:
  1. Disable NetworkManager-wait-online.service (saves ~6.7s boot)
  2. Tune vm.swappiness to 10 + vm.vfs_cache_pressure to 50 + dirty page tuning
  3. Enable NVIDIA persistence mode via systemd
  4. Install earlyoom (prevents OOM hard-freezes)
  5. Mask failed SSSD socket/service units (stop retry waste)
  6. Vacuum systemd journal + set 300M cap
  7. Set NVMe I/O scheduler to kyber (if available, else none)

All fixes are idempotent and safe to re-run.
Run with --undo to reverse all changes.
EOF
		exit 0
		;;
	esac
done

require_root "$@"

UNDO_SCRIPT="/root/undo_ubuntu_performance_$(date +%Y%m%d_%H%M%S).sh"
FIXES_APPLIED=0
FIXES_SKIPPED=0

# ---------------------------------------------------------------------------
# Create undo script header
# ---------------------------------------------------------------------------
init_undo_script() {
	cat >"$UNDO_SCRIPT" <<'UNDOHEADER'
#!/usr/bin/env bash
# Auto-generated undo script for fix_ubuntu_performance.sh
# Run with: sudo bash /root/undo_ubuntu_performance_*.sh
set -euo pipefail

echo "Reversing Ubuntu performance optimizations..."
echo ""
UNDOHEADER
	chmod 700 "$UNDO_SCRIPT"
}

add_undo() {
	echo "$1" >>"$UNDO_SCRIPT"
}

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
# Fix 1: Disable NetworkManager-wait-online.service
# ===================================================================
fix_nm_wait_online() {
	if ! systemctl is-enabled NetworkManager-wait-online.service >/dev/null 2>&1; then
		log_ok "NetworkManager-wait-online is already disabled — skipping."
		return 0
	fi

	systemctl disable NetworkManager-wait-online.service

	add_undo "# Undo: Re-enable NetworkManager-wait-online"
	add_undo "systemctl enable NetworkManager-wait-online.service"
	add_undo ""
	return 0
}

# shellcheck source=lib/ubuntu_perf_fixes.sh
source "$SCRIPT_DIR/lib/ubuntu_perf_fixes.sh"
# shellcheck source=lib/ubuntu_perf_more.sh
source "$SCRIPT_DIR/lib/ubuntu_perf_more.sh"

main() {
	if [[ $UNDO_MODE == "true" ]]; then
		run_undo
	fi

	if [[ $DRY_RUN == "false" ]]; then
		init_undo_script
	fi

	print_setup_header "Ubuntu Performance Optimization (Legion Laptop)"

	apply_fix \
		"Fix 1/7: Disable NetworkManager-wait-online.service (~6.7s boot saving)" \
		fix_nm_wait_online

	apply_fix \
		"Fix 2/7: Tune sysctl (swappiness=10, vfs_cache_pressure=50, dirty page tuning)" \
		fix_sysctl_tuning

	apply_fix \
		"Fix 3/7: Enable NVIDIA persistence mode (faster GPU operations)" \
		fix_nvidia_persistence

	apply_fix \
		"Fix 4/7: Install earlyoom (prevent OOM hard-freezes)" \
		fix_earlyoom

	apply_fix \
		"Fix 5/7: Mask failed SSSD units (stop retry waste)" \
		fix_failed_sssd

	apply_fix \
		"Fix 6/7: Vacuum journal logs + set permanent 300M size cap" \
		fix_journal

	apply_fix \
		"Fix 7/7: Disable snap repair timer (reduce background work)" \
		fix_snap_startup

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
		echo ""
		log_ok "Undo script saved to: $UNDO_SCRIPT"
		log_info "To reverse ALL changes: sudo bash $UNDO_SCRIPT"
	fi

	echo ""
	log_info "Reboot recommended for full effect."
	log_info "After reboot, verify with: systemd-analyze && nvidia-smi -q | grep Persistence"
}

main
