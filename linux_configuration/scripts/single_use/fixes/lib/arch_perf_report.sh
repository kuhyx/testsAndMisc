#!/bin/bash
# GPU and journal probes, the safe-fix pass and the report summary.
#
# Sourced by diagnose_arch_performance.sh; split out to keep
# arch_perf_probes.sh under the 250-line cap. Sourced rather than run, so
# it inherits the caller's strict mode and the variables above the source.

check_gpu_state() {
	if has_cmd nvidia-smi; then
		run_and_log "NVIDIA State" nvidia-smi
		local pstate util power
		pstate=$(nvidia-smi --query-gpu=pstate --format=csv,noheader 2>/dev/null | head -n 1 | xargs || true)
		util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -n 1 | xargs || true)
		power=$(nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits 2>/dev/null | head -n 1 | xargs || true)

		{
			echo "NVIDIA pstate: ${pstate:-unknown}"
			echo "NVIDIA util: ${util:-unknown}%"
			echo "NVIDIA power: ${power:-unknown}W"
		} >>"$REPORT_FILE"

		if [[ ${pstate:-} == "P0" && ${util:-100} -le 5 ]]; then
			add_finding "NVIDIA GPU is in P0 high-performance state while mostly idle; this can increase heat and trigger thermal limits."
			add_action "If laptop has hybrid graphics, prefer iGPU mode for desktop workloads and use dGPU on demand."
		fi
	else
		run_and_log "PCI VGA Devices" lspci -nnk | grep -A3 -Ei 'vga|3d|display'
	fi
}

check_journal_size() {
	local journal_line
	journal_line=$(journalctl --disk-usage 2>/dev/null || true)
	echo "Journal usage: ${journal_line:-unknown}" >>"$REPORT_FILE"

	if [[ $journal_line =~ ([0-9]+\.?[0-9]*)\ (G|M) ]]; then
		local value unit
		value="${BASH_REMATCH[1]}"
		unit="${BASH_REMATCH[2]}"
		if [[ $unit == "G" ]]; then
			add_finding "Systemd journal is large (${value}G); excessive logs can waste I/O and disk space."
		fi
	fi
}

apply_safe_fixes() {
	if [[ $APPLY_SAFE_FIXES != "true" ]]; then
		return
	fi

	log_info "Applying safe fixes..."

	if ! systemctl is-enabled fstrim.timer >/dev/null 2>&1; then
		systemctl enable --now fstrim.timer
		add_action "Enabled and started fstrim.timer."
	fi

	if systemctl is-enabled tlp.service >/dev/null 2>&1 && systemctl is-enabled power-profiles-daemon.service >/dev/null 2>&1; then
		systemctl disable --now tlp.service
		add_action "Disabled tlp.service to avoid conflict with power-profiles-daemon."
	fi

	local journal_line
	journal_line=$(journalctl --disk-usage 2>/dev/null || true)
	if [[ $journal_line =~ ([0-9]+\.?[0-9]*)\ G ]]; then
		journalctl --vacuum-size=300M
		add_action "Vacuumed systemd journal to 300M."
	fi
}

print_summary() {
	echo
	echo "=============================="
	echo " Arch Performance Diagnostics"
	echo "=============================="
	echo "Report: $REPORT_FILE"
	echo

	if [[ ${#FINDINGS[@]} -eq 0 ]]; then
		log_ok "No high-confidence bottlenecks detected by automated checks."
	else
		log_warn "Likely issues found (${#FINDINGS[@]}):"
		local item
		for item in "${FINDINGS[@]}"; do
			echo "  - $item"
		done
	fi

	if [[ ${#ACTIONS[@]} -gt 0 ]]; then
		echo
		log_info "Actions/recommendations:"
		local action
		for action in "${ACTIONS[@]}"; do
			echo "  - $action"
		done
	fi

	echo
	echo "Recommended next command for deep per-process analysis:"
	echo "  sudo iotop -oPa"
	echo "  top"
	echo "  systemd-analyze blame"
}
