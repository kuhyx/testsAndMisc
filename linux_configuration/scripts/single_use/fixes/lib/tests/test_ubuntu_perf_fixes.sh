#!/usr/bin/env bash
# lib/tests/test_ubuntu_perf_fixes.sh — tests for ubuntu_perf_fixes.sh's
# fix_sysctl_tuning and fix_nvidia_persistence.
#
# fix_earlyoom and fix_failed_sssd live in test_ubuntu_perf_fixes_oom.sh,
# split out to hold every file under the 250-line cap.
#
# Calls go through _t_run rather than `out="$(...)"`: command substitution
# forks a subshell, and kcov does not register a lib whose first execution
# happens inside one.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=ubuntu_perf_harness.sh
. "${SCRIPT_DIR}/ubuntu_perf_harness.sh"

# shellcheck source=../ubuntu_perf_fixes.sh
. "${FIXES_DIR}/lib/ubuntu_perf_fixes.sh"

printf '\n-- fix_sysctl_tuning --\n'

# Case 1: the drop-in already exists -> skip without touching anything.
ubuntu_reset
: >"${SYSCTL_DROPIN_DIR}/99-performance-tuning.conf"
_t_run fix_sysctl_tuning
_t_eq "0" "$?" "fix_sysctl_tuning: returns 0 when already applied"
_t_contains "$out" "already applied" "fix_sysctl_tuning: reports the skip"
_t_eq "" "$(_t_undo)" "fix_sysctl_tuning: records no undo when skipping"
_t_lacks "$(_t_calls)" "sysctl --system" "fix_sysctl_tuning: does not reload when skipping"

# Case 2: a fresh machine -> drop-in written, reloaded, undo recorded with the
# values that were live BEFORE the change.
ubuntu_reset
_t_stub_stdin sysctl <<'STUB'
case "$2" in
vm.swappiness) echo 60 ;;
vm.vfs_cache_pressure) echo 100 ;;
vm.dirty_ratio) echo 20 ;;
vm.dirty_background_ratio) echo 10 ;;
esac
exit 0
STUB
_t_run fix_sysctl_tuning
dropin="$(_t_sysctl_file)"
_t_contains "$dropin" "vm.swappiness = 10" "fix_sysctl_tuning: writes swappiness"
_t_contains "$dropin" "vm.vfs_cache_pressure = 50" "fix_sysctl_tuning: writes cache pressure"
_t_contains "$dropin" "vm.dirty_ratio = 15" "fix_sysctl_tuning: writes the dirty ratio"
_t_contains "$(_t_calls)" "sysctl --system" "fix_sysctl_tuning: applies immediately"
undo="$(_t_undo)"
_t_contains "$undo" "rm -f /etc/sysctl.d/99-performance-tuning.conf" \
	"fix_sysctl_tuning: the undo removes the real drop-in, not the sandbox one"
_t_contains "$undo" "vm.swappiness=60" "fix_sysctl_tuning: undo restores the prior swappiness"
_t_contains "$undo" "vm.dirty_ratio=20" "fix_sysctl_tuning: undo restores the prior dirty ratio"

# Case 3: sysctl cannot report the current values -> documented defaults are
# used for the undo rather than an empty string, which would produce an undo
# script that sets nothing.
ubuntu_reset
_t_stub sysctl 'exit 1'
_t_run fix_sysctl_tuning
undo="$(_t_undo)"
_t_contains "$undo" "vm.swappiness=60" "fix_sysctl_tuning: falls back to the default swappiness"
_t_contains "$undo" "vm.vfs_cache_pressure=100" "fix_sysctl_tuning: falls back for cache pressure"
_t_contains "$undo" "vm.dirty_background_ratio=10" \
	"fix_sysctl_tuning: falls back for the background ratio"

printf '\n-- fix_nvidia_persistence --\n'

# Case 4: persistence mode already enabled -> skip.
ubuntu_reset
_t_stub_stdin nvidia-smi <<'STUB'
[[ $1 == -q ]] && { echo "    Persistence Mode              : Enabled"; exit 0; }
exit 0
STUB
_t_run fix_nvidia_persistence
_t_eq "0" "$?" "fix_nvidia_persistence: returns 0 when persistence is on"
_t_contains "$out" "already enabled" "fix_nvidia_persistence: reports the skip"
_t_eq "" "$(_t_undo)" "fix_nvidia_persistence: records no undo when skipping"

# Case 5: the helper service already exists AND is enabled, but persistence is
# off this boot -> start it, do not rewrite the unit.
ubuntu_reset
_t_stub nvidia-smi 'exit 0'
printf 'EXISTING UNIT\n' >"${SYSTEMD_UNIT_DIR}/nvidia-persistence-mode.service"
_t_run fix_nvidia_persistence
_t_contains "$out" "helper already configured" \
	"fix_nvidia_persistence: reports the helper is set up"
_t_contains "$(_t_calls)" "start nvidia-persistence-mode.service" \
	"fix_nvidia_persistence: starts the helper for this boot"
_t_eq "EXISTING UNIT" "$(_t_unit nvidia-persistence-mode.service)" \
	"fix_nvidia_persistence: does not rewrite an existing unit"

# Case 6: nvidia-persistenced present -> the helper unit is created, enabled,
# and the undo removes it.
ubuntu_reset
_t_stub nvidia-smi 'exit 0'
_t_stub nvidia-persistenced 'exit 0'
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-enabled ]] && exit 1
exit 0
STUB
_t_run fix_nvidia_persistence
unit="$(_t_unit nvidia-persistence-mode.service)"
_t_contains "$unit" "Description=Enable NVIDIA Persistence Mode" \
	"fix_nvidia_persistence: writes the helper unit"
_t_contains "$unit" "Requires=nvidia-persistenced.service" \
	"fix_nvidia_persistence: the helper requires the daemon"
calls="$(_t_calls)"
_t_contains "$calls" "start nvidia-persistenced.service" \
	"fix_nvidia_persistence: makes sure the daemon is running first"
_t_contains "$calls" "daemon-reload" "fix_nvidia_persistence: reloads systemd"
_t_contains "$calls" "enable --now nvidia-persistence-mode.service" \
	"fix_nvidia_persistence: enables the helper"
_t_contains "$(_t_undo)" "rm -f /etc/systemd/system/nvidia-persistence-mode.service" \
	"fix_nvidia_persistence: undo removes the real helper unit"

# Case 7: no nvidia-persistenced -> fall back to the standalone service.
ubuntu_reset
_t_stub nvidia-smi 'exit 0'
_t_unstub nvidia-persistenced
_t_hide nvidia-persistenced
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-enabled ]] && exit 1
exit 0
STUB
_t_run fix_nvidia_persistence
unit="$(_t_unit nvidia-persistence.service)"
_t_contains "$unit" "Description=NVIDIA Persistence Mode" \
	"fix_nvidia_persistence: writes the fallback unit"
_t_contains "$unit" "Requires=nvidia.target" \
	"fix_nvidia_persistence: the fallback requires nvidia.target, not the daemon"
_t_contains "$(_t_calls)" "enable --now nvidia-persistence.service" \
	"fix_nvidia_persistence: enables the fallback service"
_t_contains "$(_t_undo)" "rm -f /etc/systemd/system/nvidia-persistence.service" \
	"fix_nvidia_persistence: undo removes the real fallback unit"
_t_eq "" "$(_t_unit nvidia-persistence-mode.service)" \
	"fix_nvidia_persistence: writes no helper unit without the daemon"
_t_full_path

printf '\nubuntu_perf_fixes (sysctl/nvidia): %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
