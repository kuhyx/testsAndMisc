#!/usr/bin/env bash
# lib/tests/test_arch_cpu.sh — tests for arch_cpu.sh.
#
# Both functions read hardware state from sysfs and write persistence rules,
# so every case builds a fake sysfs tree under $CPU_SYSFS_ROOT /
# $BLOCK_SYSFS_ROOT first. That is what lets a case present hardware this
# host does not have -- a rotational disk, or a core that is not already on
# the performance governor.
#
# Calls go through _t_run rather than `out="$(...)"`: command substitution
# forks a subshell, and kcov does not register a lib whose first execution
# happens inside one.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=arch_desktop_harness.sh
. "${SCRIPT_DIR}/arch_desktop_harness.sh"

# shellcheck source=../arch_cpu.sh
. "${FIXES_DIR}/lib/arch_cpu.sh"

printf '\n-- tweak_cpu_governor --\n'

# Case 1: no governor files at all (a VM, or a kernel without cpufreq).
arch_desktop_reset
_t_run tweak_cpu_governor
_t_eq "0" "$?" "tweak_cpu_governor: returns 0 with no governor files"
_t_contains "$out" "No CPU governor sysfs files found" \
	"tweak_cpu_governor: warns when cpufreq is absent"
_t_eq "" "$(_t_udev 60-cpu-governor-performance.rules)" \
	"tweak_cpu_governor: writes no udev rule when there is nothing to tune"

# Case 2: every core already on performance -> skip without writing.
arch_desktop_reset
_t_make_cpu 4 performance
_t_run tweak_cpu_governor
_t_contains "$out" "already on 'performance' governor" \
	"tweak_cpu_governor: reports the skip when all cores are tuned"
_t_eq "" "$(_t_udev 60-cpu-governor-performance.rules)" \
	"tweak_cpu_governor: writes no udev rule when skipping"

# Case 3: cores on powersave -> every core is switched and the rule written.
arch_desktop_reset
_t_make_cpu 3 powersave
# _t_hide keeps $FAKE_BIN on PATH, so the default stub has to go first or
# has_cmd still finds cpupower and the "not installed" branch never runs.
_t_unstub cpupower
_t_hide cpupower
_t_run tweak_cpu_governor
_t_eq "performance" "$(cat "${CPU_SYSFS_ROOT}/cpu0/cpufreq/scaling_governor")" \
	"tweak_cpu_governor: switches cpu0 to performance"
_t_eq "performance" "$(cat "${CPU_SYSFS_ROOT}/cpu2/cpufreq/scaling_governor")" \
	"tweak_cpu_governor: switches the last core too"
_t_contains "$(_t_udev 60-cpu-governor-performance.rules)" "scaling_governor" \
	"tweak_cpu_governor: writes the persistence udev rule"
_t_eq "" "$(cat "${CPUPOWER_CONF_FILE}" 2>/dev/null || true)" \
	"tweak_cpu_governor: writes no cpupower config when cpupower is absent"
_t_full_path

# Case 4: only SOME cores need changing -- the mixed case, which the
# all_performance loop must break out of on the first mismatch.
arch_desktop_reset
_t_make_cpu 2 performance
mkdir -p "${CPU_SYSFS_ROOT}/cpu2/cpufreq"
printf 'powersave\n' >"${CPU_SYSFS_ROOT}/cpu2/cpufreq/scaling_governor"
_t_unstub cpupower
_t_hide cpupower
_t_run tweak_cpu_governor
_t_eq "performance" "$(cat "${CPU_SYSFS_ROOT}/cpu2/cpufreq/scaling_governor")" \
	"tweak_cpu_governor: switches the one core that lagged"
_t_lacks "$out" "already on 'performance'" \
	"tweak_cpu_governor: does not claim a skip when one core differed"
_t_full_path

# Case 5: cpupower present and unconfigured -> config written and unit enabled.
arch_desktop_reset
_t_make_cpu 1 powersave
_t_stub cpupower 'exit 0'
_t_run tweak_cpu_governor
_t_contains "$(cat "${CPUPOWER_CONF_FILE}")" "governor='performance'" \
	"tweak_cpu_governor: writes the cpupower default"
_t_contains "$(_t_calls)" "systemctl enable cpupower.service" \
	"tweak_cpu_governor: enables the cpupower unit"

# Case 6: cpupower present and ALREADY configured -> left alone, not re-enabled.
arch_desktop_reset
_t_make_cpu 1 powersave
_t_stub cpupower 'exit 0'
printf "governor='performance'\n" >"${CPUPOWER_CONF_FILE}"
_t_run tweak_cpu_governor
_t_lacks "$(_t_calls)" "systemctl enable cpupower.service" \
	"tweak_cpu_governor: does not re-enable when already configured"

printf '\n-- tweak_io_scheduler --\n'

# Case 7: no block devices -> the udev rule is still written, and the
# "already optimal" line reports that nothing changed.
arch_desktop_reset
_t_run tweak_io_scheduler
_t_eq "0" "$?" "tweak_io_scheduler: returns 0 with no block devices"
_t_contains "$out" "All I/O schedulers already optimal" \
	"tweak_io_scheduler: reports nothing changed"
_t_contains "$(_t_udev 60-io-scheduler.rules)" "mq-deadline" \
	"tweak_io_scheduler: writes the persistence udev rule regardless"

# Case 8: an NVMe drive wants 'none'.
arch_desktop_reset
_t_make_block nvme0n1 0 '[mq-deadline] none'
_t_run tweak_io_scheduler
_t_eq "none" "$(_t_sched nvme0n1)" "tweak_io_scheduler: sets NVMe to none"
_t_contains "$out" "scheduler changed from 'mq-deadline' to 'none'" \
	"tweak_io_scheduler: logs the NVMe change"

# Case 9: a SATA SSD (rotational=0) wants mq-deadline.
arch_desktop_reset
_t_make_block sda 0 '[none] mq-deadline bfq'
_t_run tweak_io_scheduler
_t_eq "mq-deadline" "$(_t_sched sda)" "tweak_io_scheduler: sets SSD to mq-deadline"

# Case 10: a spinning disk (rotational=1) wants bfq.
arch_desktop_reset
_t_make_block sdb 1 '[mq-deadline] bfq none'
_t_run tweak_io_scheduler
_t_eq "bfq" "$(_t_sched sdb)" "tweak_io_scheduler: sets HDD to bfq"

# Case 11: a device already on its target is left alone.
arch_desktop_reset
_t_make_block nvme1n1 0 'mq-deadline [none]'
_t_run tweak_io_scheduler
_t_contains "$out" "already using 'none' scheduler" \
	"tweak_io_scheduler: reports an already-optimal device"
_t_contains "$out" "All I/O schedulers already optimal" \
	"tweak_io_scheduler: counts it as no change"

# Case 12: several devices of different kinds in one pass.
arch_desktop_reset
_t_make_block nvme0n1 0 '[mq-deadline] none'
_t_make_block sda 0 '[bfq] mq-deadline'
_t_make_block sdb 1 '[mq-deadline] bfq'
_t_run tweak_io_scheduler
_t_eq "none" "$(_t_sched nvme0n1)" "tweak_io_scheduler: NVMe handled in a mixed pass"
_t_eq "mq-deadline" "$(_t_sched sda)" "tweak_io_scheduler: SSD handled in a mixed pass"
_t_eq "bfq" "$(_t_sched sdb)" "tweak_io_scheduler: HDD handled in a mixed pass"

# Case 13: a directory without a queue/scheduler file is skipped, not fatal.
arch_desktop_reset
mkdir -p "${BLOCK_SYSFS_ROOT}/sdc"
_t_run tweak_io_scheduler
_t_eq "0" "$?" "tweak_io_scheduler: skips a device with no scheduler file"

# Case 14: an existing udev rule is not overwritten.
arch_desktop_reset
printf 'CUSTOM RULE\n' >"${UDEV_RULES_DIR}/60-io-scheduler.rules"
_t_run tweak_io_scheduler
_t_eq "CUSTOM RULE" "$(_t_udev 60-io-scheduler.rules)" \
	"tweak_io_scheduler: leaves an existing udev rule alone"

printf '\narch_cpu: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
