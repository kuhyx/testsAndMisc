#!/usr/bin/env bash
# Tests for lib/arch_perf_probes.sh: collect_basics and check_cpu_governor.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=arch_perf_harness.sh
. "${SCRIPT_DIR}/arch_perf_harness.sh"

# shellcheck source=../arch_perf_probes.sh
. "${FIXES_DIR}/lib/arch_perf_probes.sh"

# --- collect_basics ---------------------------------------------------------

# A quiet machine: every section is logged, and nothing is flagged.
arch_reset
_t_stub uname 'echo "Linux kuhy-pc 7.1.9-arch1-1"'
_t_stub uptime 'echo " 12:00:00 up 2:00,  1 user,  load average: 0.10, 0.20, 0.30"'
_t_stub free 'echo "Mem: 32Gi 8Gi 24Gi"'
_t_stub swapon 'exit 0'
_t_stub lscpu 'echo "CPU(s): 16"'
_t_stub df 'echo "/dev/nvme0n1p2  100G  40G  60G  40% /"'
_t_stub systemd-analyze 'echo "Startup finished in 3.2s"'
_t_stub systemctl 'exit 0'
_t_stub journalctl 'exit 0'
_t_stub getconf 'echo 16'
_t_stub ps 'echo "  PID COMMAND         %CPU %MEM"'
collect_basics
report="$(_t_report)"
_t_contains "$report" "=== Kernel ===" "collect_basics: logs the kernel section"
_t_contains "$report" "=== Uptime ===" "collect_basics: logs the uptime section"
_t_contains "$report" "=== Memory ===" "collect_basics: logs the memory section"
_t_contains "$report" "=== Boot Time ===" "collect_basics: logs the boot time section"
_t_contains "$report" "=== Failed Units ===" "collect_basics: logs the failed units section"
_t_contains "$report" "=== Top CPU Processes ===" \
	"collect_basics: logs the top CPU processes snapshot"
_t_eq "" "$(_t_findings)" "collect_basics: flags nothing on a quiet machine"

# Failed units, frequent ACPI errors and a busy Xorg are each flagged.
arch_reset
_t_stub getconf 'echo 16'
_t_stub_stdin systemctl <<'STUB_BODY'
if [[ "$*" == *"--failed --no-legend"* ]]; then
	echo "foo.service loaded failed failed Foo"
	echo "bar.service loaded failed failed Bar"
fi
exit 0
STUB_BODY
_t_stub_stdin journalctl <<'STUB_BODY'
for _ in 1 2 3 4 5 6; do
	echo "kernel: ACPI Error: something went wrong"
done
exit 0
STUB_BODY
_t_stub_stdin ps <<'STUB_BODY'
if [[ "$*" == *"-C Xorg"* ]]; then
	echo " 45.0"
	exit 0
fi
echo "  PID COMMAND         %CPU %MEM"
STUB_BODY
collect_basics
findings="$(_t_findings)"
_t_contains "$findings" "systemd units are failed (2)" \
	"collect_basics: flags failed systemd units and counts them"
_t_contains "$findings" "ACPI errors detected" \
	"collect_basics: flags frequent ACPI errors"
_t_contains "$findings" "Xorg is using high CPU (45%)" \
	"collect_basics: flags a CPU-hungry Xorg"

# A load average at or above the thread count is flagged. /proc/loadavg is
# read directly by the lib, so the case is driven by a low CPU count instead.
arch_reset
_t_stub getconf 'echo 1'
_t_stub systemctl 'exit 0'
_t_stub journalctl 'exit 0'
_t_stub ps 'echo none'
collect_basics
if [[ $(awk '{print int($1)}' /proc/loadavg) -ge 1 ]]; then
	_t_contains "$(_t_findings)" "load average is at/above CPU thread count" \
		"collect_basics: flags a load average at or above the thread count"
else
	_t_pass "collect_basics: SKIP load case (this host's 1-minute load is below 1)"
fi

# --- check_cpu_governor -----------------------------------------------------

# The lib runs `find /sys/devices/system/cpu`, a real path with no override,
# so `find` is stubbed to control which governor files it reports.
arch_reset
mkdir -p "${TEST_TMPDIR}/gov"
echo "performance" >"${TEST_TMPDIR}/gov/cpu0"
echo "performance" >"${TEST_TMPDIR}/gov/cpu1"
printf '%s\n%s\n' "${TEST_TMPDIR}/gov/cpu0" "${TEST_TMPDIR}/gov/cpu1" >"${DEV}/gov_list"
_t_stub_cat find gov_list
check_cpu_governor
_t_contains "$(_t_report)" "CPU governor summary: performance:2" \
	"check_cpu_governor: summarises the governors in use"
_t_eq "" "$(_t_findings)" "check_cpu_governor: flags nothing when every core is on performance"

# A core left on powersave is the condition the probe exists for.
arch_reset
echo "powersave" >"${TEST_TMPDIR}/gov/cpu1"
_t_stub_cat find gov_list
check_cpu_governor
_t_contains "$(_t_findings)" "governor includes 'powersave'" \
	"check_cpu_governor: flags a core left on the powersave governor"

# No governor files at all: an action, not a finding, and no hang.
arch_reset
: >"${DEV}/gov_list"
_t_stub_cat find gov_list
check_cpu_governor
_t_contains "$(_t_actions)" "CPU governor files not found" \
	"check_cpu_governor: records an action when no governor files exist"
_t_eq "" "$(_t_findings)" "check_cpu_governor: records no finding when governors are unsupported"

echo
echo "arch_perf_probes (basics/governor): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
