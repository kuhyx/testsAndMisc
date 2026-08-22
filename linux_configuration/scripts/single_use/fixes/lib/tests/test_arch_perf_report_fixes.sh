#!/usr/bin/env bash
# Tests for lib/arch_perf_report.sh: apply_safe_fixes and print_summary.
# Split from test_arch_perf_report.sh for the 250-line cap.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=arch_perf_harness.sh
. "${SCRIPT_DIR}/arch_perf_harness.sh"

# shellcheck source=../arch_perf_report.sh
. "${FIXES_DIR}/lib/arch_perf_report.sh"

# --- apply_safe_fixes -------------------------------------------------------

# Off by default: the flag guards every mutation.
arch_reset
APPLY_SAFE_FIXES="false"
apply_safe_fixes >"${TEST_TMPDIR}/out" 2>&1
out="$(cat "${TEST_TMPDIR}/out")"
_t_eq "" "$out" "apply_safe_fixes: does nothing unless APPLY_SAFE_FIXES is true"
_t_eq "" "$(_t_calls)" "apply_safe_fixes: runs no command when disabled"

# fstrim.timer already enabled, no tlp/ppd conflict, small journal: nothing
# to do, but the pass still announces itself.
arch_reset
APPLY_SAFE_FIXES="true"
_t_stub systemctl 'exit 0'
_t_stub journalctl 'echo "Archived and active journals take up 120.0M in the file system."'
apply_safe_fixes >"${TEST_TMPDIR}/out" 2>&1
out="$(cat "${TEST_TMPDIR}/out")"
_t_contains "$out" "Applying safe fixes" "apply_safe_fixes: announces the pass"
_t_lacks "$(_t_calls)" "systemctl enable --now fstrim.timer" \
	"apply_safe_fixes: does not re-enable an already-enabled fstrim.timer"
_t_lacks "$(_t_calls)" "journalctl --vacuum-size" \
	"apply_safe_fixes: does not vacuum a journal measured in megabytes"

# fstrim.timer disabled: it gets enabled.
arch_reset
APPLY_SAFE_FIXES="true"
_t_stub_stdin systemctl <<'STUB_BODY'
if [[ "$1" == "is-enabled" && "$2" == "fstrim.timer" ]]; then
	exit 1
fi
exit 0
STUB_BODY
_t_stub journalctl 'echo "120.0M"'
apply_safe_fixes >"${TEST_TMPDIR}/out" 2>&1
out="$(cat "${TEST_TMPDIR}/out")"
_t_contains "$(_t_calls)" "systemctl enable --now fstrim.timer" \
	"apply_safe_fixes: enables a disabled fstrim.timer"
_t_contains "$(_t_actions)" "Enabled and started fstrim.timer" \
	"apply_safe_fixes: records enabling fstrim.timer as an action"

# tlp and power-profiles-daemon both enabled: tlp is disabled to break the
# conflict.
arch_reset
APPLY_SAFE_FIXES="true"
_t_stub systemctl 'exit 0'
_t_stub journalctl 'echo "120.0M"'
apply_safe_fixes >"${TEST_TMPDIR}/out" 2>&1
out="$(cat "${TEST_TMPDIR}/out")"
_t_contains "$(_t_calls)" "systemctl disable --now tlp.service" \
	"apply_safe_fixes: disables tlp.service when it conflicts with ppd"
_t_contains "$(_t_actions)" "Disabled tlp.service" \
	"apply_safe_fixes: records disabling tlp.service as an action"

# A multi-gigabyte journal gets vacuumed. This only fires because the size
# regex now tolerates journalctl's spaceless "4.2G" output.
arch_reset
APPLY_SAFE_FIXES="true"
_t_stub systemctl 'exit 0'
_t_stub journalctl 'echo "Archived and active journals take up 4.2G in the file system."'
apply_safe_fixes >"${TEST_TMPDIR}/out" 2>&1
out="$(cat "${TEST_TMPDIR}/out")"
_t_contains "$(_t_calls)" "journalctl --vacuum-size=300M" \
	"apply_safe_fixes: vacuums a multi-gigabyte journal"
_t_contains "$(_t_actions)" "Vacuumed systemd journal to 300M" \
	"apply_safe_fixes: records the vacuum as an action"

# --- print_summary ----------------------------------------------------------

arch_reset
out="$(print_summary 2>&1)"
_t_contains "$out" "Arch Performance Diagnostics" "print_summary: prints the banner"
_t_contains "$out" "Report: ${REPORT_FILE}" "print_summary: names the report file"
_t_contains "$out" "No high-confidence bottlenecks detected" \
	"print_summary: reports a clean run when there are no findings"
_t_contains "$out" "systemd-analyze blame" \
	"print_summary: suggests the deep-analysis commands"

arch_reset
add_finding "first problem" >/dev/null
add_finding "second problem" >/dev/null
out="$(print_summary 2>&1)"
_t_contains "$out" "Likely issues found (2)" \
	"print_summary: counts the findings it lists"
_t_contains "$out" "- first problem" "print_summary: lists the first finding"
_t_contains "$out" "- second problem" "print_summary: lists the second finding"
_t_lacks "$out" "No high-confidence bottlenecks" \
	"print_summary: does not claim a clean run when findings exist"

arch_reset
add_action "do the thing" >/dev/null
out="$(print_summary 2>&1)"
_t_contains "$out" "Actions/recommendations:" \
	"print_summary: prints the actions section when actions exist"
_t_contains "$out" "- do the thing" "print_summary: lists the recorded action"

echo
echo "arch_perf_report (fixes/summary): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
