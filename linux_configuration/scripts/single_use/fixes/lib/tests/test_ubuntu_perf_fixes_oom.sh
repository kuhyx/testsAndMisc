#!/usr/bin/env bash
# lib/tests/test_ubuntu_perf_fixes_oom.sh — tests for ubuntu_perf_fixes.sh's
# fix_earlyoom and fix_failed_sssd.
#
# Split from test_ubuntu_perf_fixes.sh to hold every file under the 250-line
# cap.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=ubuntu_perf_harness.sh
. "${SCRIPT_DIR}/ubuntu_perf_harness.sh"

# shellcheck source=../ubuntu_perf_fixes.sh
. "${FIXES_DIR}/lib/ubuntu_perf_fixes.sh"

printf '\n-- fix_earlyoom --\n'

# Case 1: earlyoom already running -> skip.
ubuntu_reset
_t_stub systemctl 'exit 0'
_t_run fix_earlyoom
_t_eq "0" "$?" "fix_earlyoom: returns 0 when already running"
_t_contains "$out" "already running" "fix_earlyoom: reports the skip"
_t_eq "" "$(_t_undo)" "fix_earlyoom: records no undo when skipping"

# Case 2: not running and not installed -> installed, configured, enabled.
ubuntu_reset
_t_stub systemctl 'exit 1'
_t_stub dpkg 'exit 1'
_t_run fix_earlyoom
_t_contains "$out" "Installing earlyoom" "fix_earlyoom: says it is installing"
calls="$(_t_calls)"
_t_contains "$calls" "apt-get install -y earlyoom" "fix_earlyoom: installs the package"
conf="$(cat "${EARLYOOM_CONF_FILE}")"
_t_contains "$conf" 'EARLYOOM_ARGS="-r 5 -s 10 -n' "fix_earlyoom: writes the thresholds"
_t_contains "$conf" "prefer" "fix_earlyoom: prefers killing browsers"
_t_contains "$calls" "enable --now earlyoom.service" "fix_earlyoom: enables the unit"
undo="$(_t_undo)"
_t_contains "$undo" "disable --now earlyoom.service" "fix_earlyoom: undo disables the unit"
_t_contains "$undo" "apt-get remove -y earlyoom" "fix_earlyoom: undo removes the package"

# Case 3: already installed but not running -> configured without a reinstall.
ubuntu_reset
_t_stub systemctl 'exit 1'
_t_stub_stdin dpkg <<'STUB'
echo "ii  earlyoom  1.7-1  amd64  Early OOM daemon"
exit 0
STUB
_t_run fix_earlyoom
_t_lacks "$out" "Installing earlyoom" "fix_earlyoom: does not reinstall an installed package"
_t_lacks "$(_t_calls)" "apt-get install" "fix_earlyoom: skips apt-get when already present"
_t_contains "$(_t_calls)" "enable --now earlyoom.service" \
	"fix_earlyoom: still enables the unit"

# Case 4: an existing config is backed up before being overwritten.
ubuntu_reset
_t_stub systemctl 'exit 1'
_t_stub dpkg 'exit 1'
printf 'OLD CONFIG\n' >"${EARLYOOM_CONF_FILE}"
_t_run fix_earlyoom
_t_eq "OLD CONFIG" "$(cat "${EARLYOOM_CONF_FILE}.bak")" \
	"fix_earlyoom: backs up the previous config"
_t_contains "$(cat "${EARLYOOM_CONF_FILE}")" "EARLYOOM_ARGS" \
	"fix_earlyoom: writes the new config over it"

printf '\n-- fix_failed_sssd --\n'

# Case 5: nothing failed -> skip without masking anything.
ubuntu_reset
_t_stub systemctl 'exit 1'
_t_run fix_failed_sssd
_t_eq "0" "$?" "fix_failed_sssd: returns 0 when nothing has failed"
_t_contains "$out" "No failed SSSD units" "fix_failed_sssd: reports the skip"
_t_lacks "$(_t_calls)" "mask" "fix_failed_sssd: masks nothing when nothing failed"
_t_eq "" "$(_t_undo)" "fix_failed_sssd: records no undo when skipping"

# Case 6: every unit failed -> all five masked, each with its own undo.
ubuntu_reset
_t_stub systemctl 'exit 0'
_t_run fix_failed_sssd
calls="$(_t_calls)"
_t_contains "$calls" "mask sssd-pac.service" "fix_failed_sssd: masks the pac service"
_t_contains "$calls" "mask sssd-pam.socket" "fix_failed_sssd: masks the pam socket"
_t_contains "$calls" "stop sssd-nss.socket" "fix_failed_sssd: stops before masking"
_t_contains "$calls" "reset-failed" "fix_failed_sssd: clears the failed state afterwards"
undo="$(_t_undo)"
_t_contains "$undo" "systemctl unmask sssd-pac.service" "fix_failed_sssd: undo unmasks each unit"
_t_eq "5" "$(grep -c 'systemctl unmask' <<<"$undo")" \
	"fix_failed_sssd: records one unmask per masked unit"

# Case 7: only ONE unit failed -> only that one is masked. This is the arm the
# detection loop's `break` makes easy to get wrong: the loop stops at the first
# failure, but the masking loop must still re-check each unit individually.
ubuntu_reset
_t_stub_stdin systemctl <<'STUB'
if [[ $1 == is-failed ]]; then
	[[ $2 == sssd-pam.socket ]] && exit 0
	exit 1
fi
exit 0
STUB
_t_run fix_failed_sssd
calls="$(_t_calls)"
_t_contains "$calls" "mask sssd-pam.socket" "fix_failed_sssd: masks the one failed unit"
_t_lacks "$calls" "mask sssd-pac.service" "fix_failed_sssd: leaves the healthy units alone"
_t_eq "1" "$(grep -c 'systemctl unmask' <<<"$(_t_undo)")" \
	"fix_failed_sssd: records exactly one unmask"

printf '\nubuntu_perf_fixes (oom/sssd): %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
