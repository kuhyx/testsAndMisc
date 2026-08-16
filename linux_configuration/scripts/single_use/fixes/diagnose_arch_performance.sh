#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../../lib/common.sh
source "$SCRIPT_DIR/../../lib/common.sh"

REPORT_DIR="${HOME}/.local/state/system-diagnostics"
REPORT_FILE="$REPORT_DIR/arch-performance-$(date +%Y%m%d_%H%M%S).log"
APPLY_SAFE_FIXES=false
INSTALL_TOOLS=false

declare -a FINDINGS=()
declare -a ACTIONS=()

usage() {
	cat <<'EOF'
diagnose_arch_performance.sh - Diagnose common causes of Arch Linux slowness/instability

Usage:
  diagnose_arch_performance.sh [OPTIONS]

Options:
  --apply-safe-fixes   Apply conservative fixes (requires sudo)
  --install-tools      Install optional diagnostics packages (requires sudo)
  -h, --help           Show help

Safe fixes applied when --apply-safe-fixes is used:
  - Enable/start fstrim.timer if missing
  - Resolve TLP vs power-profiles-daemon conflict (keeps power-profiles-daemon)
  - Vacuum journal logs if they exceed 1GiB

Notes:
  - Script does not reboot automatically.
  - Some checks are informational and provide next-step commands.
EOF
}

parse_args() {
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--apply-safe-fixes)
			APPLY_SAFE_FIXES=true
			shift
			;;
		--install-tools)
			INSTALL_TOOLS=true
			shift
			;;
		-h | --help)
			usage
			exit 0
			;;
		*)
			log_error "Unknown option: $1"
			usage
			exit 2
			;;
		esac
	done
}

add_finding() {
	FINDINGS+=("$1")
	log_warn "$1"
}

add_action() {
	ACTIONS+=("$1")
	log_info "$1"
}

run_and_log() {
	local header="$1"
	shift
	{
		echo
		echo "=== $header ==="
		"$@" 2>&1 || true
	} >>"$REPORT_FILE"
}

check_root_if_needed() {
	if [[ $APPLY_SAFE_FIXES == "true" || $INSTALL_TOOLS == "true" ]]; then
		require_root "$@"
	fi
}

install_optional_tools() {
	if [[ $INSTALL_TOOLS != "true" ]]; then
		return
	fi

	local packages=(lm_sensors smartmontools nvtop iotop powertop)
	log_info "Installing optional diagnostic packages: ${packages[*]}"
	pacman -S --needed --noconfirm "${packages[@]}"
}

# shellcheck source=lib/arch_perf_probes.sh
source "$SCRIPT_DIR/lib/arch_perf_probes.sh"
# shellcheck source=lib/arch_perf_report.sh
source "$SCRIPT_DIR/lib/arch_perf_report.sh"

main() {
	parse_args "$@"
	check_root_if_needed "$@"

	mkdir -p "$REPORT_DIR"
	log_info "Writing diagnostic report to: $REPORT_FILE"

	collect_basics
	install_optional_tools
	check_cpu_governor
	check_thermal_state
	check_power_services
	check_storage_health
	check_memory_pressure
	check_gpu_state
	check_journal_size
	apply_safe_fixes
	print_summary
}

main "$@"
