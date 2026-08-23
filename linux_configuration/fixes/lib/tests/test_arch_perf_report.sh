#!/usr/bin/env bash
# Tests for lib/arch_perf_report.sh: check_gpu_state, check_journal_size,
# apply_safe_fixes and print_summary.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=arch_perf_harness.sh
. "${SCRIPT_DIR}/arch_perf_harness.sh"

# shellcheck source=../arch_perf_report.sh
. "${FIXES_DIR}/lib/arch_perf_report.sh"

# --- check_gpu_state --------------------------------------------------------

# No nvidia-smi: falls back to listing PCI display devices. The host may have
# a real nvidia-smi, so _t_hide takes it off PATH outright.
arch_reset
_t_unstub nvidia-smi
_t_hide nvidia-smi
_t_stub lspci 'echo "01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GA104"'
check_gpu_state
_t_full_path
_t_contains "$(_t_report)" "=== PCI VGA Devices ===" \
	"check_gpu_state: logs PCI display devices when nvidia-smi is absent"
_t_eq "" "$(_t_findings)" "check_gpu_state: records no finding without nvidia-smi"

# An idle GPU pinned in P0 is the condition the check exists for.
arch_reset
_t_stub_stdin nvidia-smi <<'STUB_BODY'
case "$1" in
--query-gpu=pstate) echo P0 ;;
--query-gpu=utilization.gpu) echo 2 ;;
--query-gpu=power.draw) echo 31.5 ;;
*) echo "full nvidia-smi output" ;;
esac
STUB_BODY
check_gpu_state
_t_contains "$(_t_report)" "NVIDIA pstate: P0" \
	"check_gpu_state: records the reported pstate"
_t_contains "$(_t_report)" "NVIDIA util: 2%" \
	"check_gpu_state: records the reported utilisation"
_t_contains "$(_t_report)" "NVIDIA power: 31.5W" \
	"check_gpu_state: records the reported power draw"
_t_contains "$(_t_findings)" "P0 high-performance state while mostly idle" \
	"check_gpu_state: flags a GPU idling in P0"
_t_contains "$(_t_actions)" "prefer iGPU mode" \
	"check_gpu_state: recommends the iGPU for desktop workloads"

# A busy GPU in P0 is normal and must NOT be flagged.
arch_reset
_t_stub_stdin nvidia-smi <<'STUB_BODY'
case "$1" in
--query-gpu=pstate) echo P0 ;;
--query-gpu=utilization.gpu) echo 87 ;;
--query-gpu=power.draw) echo 210 ;;
*) echo "out" ;;
esac
STUB_BODY
check_gpu_state
_t_eq "" "$(_t_findings)" "check_gpu_state: does not flag a P0 GPU that is actually busy"

# An idle GPU in a low-power state is also fine.
arch_reset
_t_stub_stdin nvidia-smi <<'STUB_BODY'
case "$1" in
--query-gpu=pstate) echo P8 ;;
--query-gpu=utilization.gpu) echo 0 ;;
--query-gpu=power.draw) echo 9 ;;
*) echo "out" ;;
esac
STUB_BODY
check_gpu_state
_t_eq "" "$(_t_findings)" "check_gpu_state: does not flag an idle GPU in a low-power state"

# nvidia-smi present but answering nothing: the report records "unknown".
arch_reset
_t_stub nvidia-smi 'exit 0'
check_gpu_state
_t_contains "$(_t_report)" "NVIDIA pstate: unknown" \
	"check_gpu_state: records 'unknown' when nvidia-smi returns nothing"

# --- check_journal_size -----------------------------------------------------

arch_reset
_t_stub journalctl 'echo "Archived and active journals take up 4.2G in the file system."'
check_journal_size
_t_contains "$(_t_report)" "Journal usage:" "check_journal_size: records journal usage"
_t_contains "$(_t_findings)" "journal is large (4.2G)" \
	"check_journal_size: flags a multi-gigabyte journal"

# The real journalctl format, with NO space before the unit -- this is what
# the machine actually prints, and requiring a space made the check dead.
arch_reset
_t_stub journalctl 'echo "Archived and active journals take up 240.0M in the file system."'
check_journal_size
_t_eq "" "$(_t_findings)" "check_journal_size: does not flag a journal measured in megabytes"
_t_contains "$(_t_report)" "240.0M" \
	"check_journal_size: records the megabyte figure verbatim"

# A space-separated figure must keep working too.
arch_reset
_t_stub journalctl 'echo "Archived and active journals take up 6.1 G in the file system."'
check_journal_size
_t_contains "$(_t_findings)" "journal is large (6.1G)" \
	"check_journal_size: still flags a space-separated gigabyte figure"

arch_reset
_t_stub journalctl 'exit 1'
check_journal_size
_t_contains "$(_t_report)" "Journal usage: unknown" \
	"check_journal_size: records 'unknown' when journalctl fails"
_t_eq "" "$(_t_findings)" "check_journal_size: records no finding when journalctl fails"

echo
echo "arch_perf_report (probes): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
