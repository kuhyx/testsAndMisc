#!/usr/bin/env bash
# Tests for lib/arch_perf_probes.sh: check_thermal_state, check_power_services,
# check_storage_health and check_memory_pressure.
# Split from test_arch_perf_probes.sh for the 250-line cap.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=arch_perf_harness.sh
. "${SCRIPT_DIR}/arch_perf_harness.sh"

# shellcheck source=../arch_perf_probes.sh
. "${FIXES_DIR}/lib/arch_perf_probes.sh"

# --- check_thermal_state ----------------------------------------------------

# sensors present and dmesg clean: the section is logged, nothing flagged.
arch_reset
_t_stub sensors 'echo "Core 0: +45.0C"'
_t_stub dmesg 'echo "usb 1-1: new high-speed USB device"'
check_thermal_state
_t_contains "$(_t_report)" "=== Temperatures (sensors) ===" \
	"check_thermal_state: logs the sensors output when sensors is installed"
_t_eq "" "$(_t_findings)" "check_thermal_state: flags nothing when dmesg is clean"

# Throttling messages in dmesg are flagged and excerpted into the report.
arch_reset
_t_stub sensors 'echo "Core 0: +95.0C"'
_t_stub dmesg 'echo "CPU2: Core temperature above threshold, cpu clock throttled"'
check_thermal_state
_t_contains "$(_t_findings)" "thermal/throttling related messages" \
	"check_thermal_state: flags throttling messages in the kernel log"
_t_contains "$(_t_report)" "=== Thermal/Throttling dmesg excerpts ===" \
	"check_thermal_state: excerpts the throttling lines into the report"

# sensors absent: an action recommending lm_sensors. The host may have a real
# sensors binary, so _t_hide takes it off PATH.
arch_reset
_t_unstub sensors
_t_hide sensors
_t_stub dmesg 'echo "nothing interesting"'
check_thermal_state
_t_full_path
_t_contains "$(_t_actions)" "Install lm_sensors" \
	"check_thermal_state: recommends lm_sensors when sensors is missing"

# --- check_power_services ---------------------------------------------------

# Both daemons enabled: the classic conflict.
arch_reset
_t_stub systemctl 'exit 0'
check_power_services
_t_contains "$(_t_report)" "Power services: tlp=true, power-profiles-daemon=true" \
	"check_power_services: records both daemons as enabled"
_t_contains "$(_t_findings)" "Both TLP and power-profiles-daemon are enabled" \
	"check_power_services: flags the TLP/ppd conflict"

# Neither enabled: an action, not a finding.
arch_reset
_t_stub systemctl 'exit 1'
check_power_services
_t_contains "$(_t_report)" "Power services: tlp=false, power-profiles-daemon=false" \
	"check_power_services: records both daemons as disabled"
_t_contains "$(_t_actions)" "No power management daemon is enabled" \
	"check_power_services: recommends enabling a power daemon when none is"
_t_eq "" "$(_t_findings)" "check_power_services: flags nothing when neither daemon runs"

# Exactly one enabled is the healthy case: neither finding nor action.
arch_reset
_t_stub_stdin systemctl <<'STUB_BODY'
[[ "$*" == *"power-profiles-daemon"* ]] && exit 0
exit 1
STUB_BODY
check_power_services
_t_contains "$(_t_report)" "tlp=false, power-profiles-daemon=true" \
	"check_power_services: records a single enabled daemon"
_t_eq "" "$(_t_findings)" "check_power_services: flags nothing when only one daemon is enabled"
_t_eq "" "$(_t_actions)" "check_power_services: recommends nothing when one daemon is enabled"

# --- check_storage_health ---------------------------------------------------

arch_reset
_t_stub lsblk 'echo "nvme0n1  Samsung 990  0  1T  disk"'
_t_stub fstrim 'echo "/: 12 GiB (trimmed)"'
_t_stub systemctl 'exit 0'
_t_stub smartctl 'echo "SMART overall-health self-assessment test result: PASSED"'
_t_stub findmnt 'echo "/dev/nvme0n1p2"'
check_storage_health
_t_contains "$(_t_report)" "=== Block Devices ===" \
	"check_storage_health: logs the block device list"
_t_contains "$(_t_report)" "=== fstrim dry-run ===" \
	"check_storage_health: logs the fstrim dry run when fstrim is present"
_t_contains "$(_t_actions)" "fstrim.timer is enabled" \
	"check_storage_health: records an enabled fstrim.timer as good"
_t_eq "" "$(_t_findings)" "check_storage_health: flags nothing on a healthy disk"

# fstrim.timer disabled is a finding; smartctl missing is an action.
arch_reset
_t_stub lsblk 'echo "sda  disk"'
_t_stub systemctl 'exit 1'
_t_unstub smartctl
_t_hide smartctl fstrim
check_storage_health
_t_full_path
_t_contains "$(_t_findings)" "fstrim.timer is not enabled" \
	"check_storage_health: flags a disabled fstrim.timer"
_t_contains "$(_t_actions)" "Install smartmontools" \
	"check_storage_health: recommends smartmontools when smartctl is missing"

# --- check_memory_pressure --------------------------------------------------

# /proc/meminfo is read directly by the lib and cannot be redirected, so this
# asserts on the shape of the result rather than on fabricated numbers.
arch_reset
check_memory_pressure
report="$(_t_report)"
if grep -q '^SwapTotal: *0 ' /proc/meminfo; then
	_t_lacks "$report" "Swap usage:" \
		"check_memory_pressure: reports no swap usage when the host has no swap"
else
	_t_contains "$report" "Swap usage:" \
		"check_memory_pressure: records swap usage when the host has swap"
fi
if [[ -f /proc/pressure/memory ]]; then
	_t_contains "$report" "=== Memory PSI ===" \
		"check_memory_pressure: logs the kernel memory pressure counters"
else
	_t_lacks "$report" "=== Memory PSI ===" \
		"check_memory_pressure: omits the PSI section when the kernel lacks it"
fi

# The high-swap branch: swap heavily used while RAM is still available. The
# lib reads the absolute /proc/meminfo, but every read goes through `awk`, so
# stubbing awk supplies controlled figures without touching /proc. The stub
# answers on the pattern the lib greps for, and defers to the real awk for
# any other call (check_thermal_state and collect_basics use it too).
arch_reset
_t_stub_stdin awk <<'STUB_BODY'
case "$1" in
*MemTotal*) echo 32000000 ;;
*MemAvailable*) echo 20000000 ;;
*SwapTotal*) echo 8000000 ;;
*SwapFree*) echo 2000000 ;;
*) exec /usr/bin/awk "$@" ;;
esac
STUB_BODY
check_memory_pressure
_t_contains "$(_t_report)" "Swap usage: 75%" \
	"check_memory_pressure: computes the swap usage percentage"
_t_contains "$(_t_findings)" "High swap usage while RAM is still available" \
	"check_memory_pressure: flags heavy swapping while RAM is free"
_t_contains "$(_t_actions)" "lowering swappiness" \
	"check_memory_pressure: recommends lowering swappiness"

# Heavy swap use with RAM genuinely exhausted is NOT the stutter signature,
# so it must not be flagged.
arch_reset
_t_stub_stdin awk <<'STUB_BODY'
case "$1" in
*MemTotal*) echo 32000000 ;;
*MemAvailable*) echo 500000 ;;
*SwapTotal*) echo 8000000 ;;
*SwapFree*) echo 2000000 ;;
*) exec /usr/bin/awk "$@" ;;
esac
STUB_BODY
check_memory_pressure
_t_contains "$(_t_report)" "Swap usage: 75%" \
	"check_memory_pressure: still records the percentage when RAM is exhausted"
_t_eq "" "$(_t_findings)" \
	"check_memory_pressure: does not flag swapping when RAM is genuinely full"

# A machine with no swap at all skips the whole swap section.
arch_reset
_t_stub_stdin awk <<'STUB_BODY'
case "$1" in
*MemTotal*) echo 32000000 ;;
*MemAvailable*) echo 20000000 ;;
*SwapTotal*) echo 0 ;;
*SwapFree*) echo 0 ;;
*) exec /usr/bin/awk "$@" ;;
esac
STUB_BODY
check_memory_pressure
_t_lacks "$(_t_report)" "Swap usage:" \
	"check_memory_pressure: reports no swap usage on a swapless machine"

echo
echo "arch_perf_probes (health): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
