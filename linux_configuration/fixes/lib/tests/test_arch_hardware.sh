#!/usr/bin/env bash
# lib/tests/test_arch_hardware.sh — arch_hardware (fstrim/nvidia) — tests for tweak_fstrim and tweak_nvidia_gpu.
#
# Split from the mitigation/journal/ananicy cases in
# test_arch_hardware_boot.sh to hold every file under the 250-line cap.
# fstrim.timer, an NVIDIA card, a boot loader, a journal size. Every case
# therefore stubs the probe and, where the lib writes, points it at the
# throwaway tmpdir through the harness's overrides.
#
# Calls go through _t_run rather than `out="$(...)"`: command substitution
# forks a subshell, and kcov does not register a lib whose first execution
# happens inside one.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=arch_desktop_harness.sh
. "${SCRIPT_DIR}/arch_desktop_harness.sh"

# shellcheck source=../arch_hardware.sh
. "${FIXES_DIR}/lib/arch_hardware.sh"

printf '\n-- tweak_fstrim --\n'

# Case 1: already enabled -> skip.
arch_desktop_reset
_t_stub systemctl 'exit 0'
_t_run tweak_fstrim
_t_eq "0" "$?" "tweak_fstrim: returns 0 when already enabled"
_t_contains "$out" "already enabled" "tweak_fstrim: reports the skip"
_t_lacks "$(_t_calls)" "systemctl enable --now fstrim.timer" \
	"tweak_fstrim: does not re-enable"

# Case 2: not enabled -> enable it.
arch_desktop_reset
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-enabled ]] && exit 1
exit 0
STUB
_t_run tweak_fstrim
_t_contains "$(_t_calls)" "systemctl enable --now fstrim.timer" \
	"tweak_fstrim: enables the timer when it is off"

printf '\n-- tweak_nvidia_gpu --\n'

# Case 3: no NVIDIA card at all.
arch_desktop_reset
_t_unstub nvidia-smi
_t_hide nvidia-smi
_t_run tweak_nvidia_gpu
_t_eq "0" "$?" "tweak_nvidia_gpu: returns 0 without nvidia-smi"
_t_contains "$out" "nvidia-smi not found" "tweak_nvidia_gpu: reports the skip"
_t_full_path

# Case 4: persistence mode already on -> not re-enabled, but the unit is
# still installed.
arch_desktop_reset
_t_stub_stdin nvidia-smi <<'STUB'
[[ $1 == --query-gpu=persistence_mode ]] && { echo "Enabled"; exit 0; }
exit 0
STUB
_t_unstub nvidia-persistenced
_t_hide nvidia-persistenced
_t_run tweak_nvidia_gpu
_t_contains "$out" "already enabled" "tweak_nvidia_gpu: reports persistence already on"
_t_lacks "$(_t_calls)" "nvidia-smi -pm 1" "tweak_nvidia_gpu: does not re-enable persistence"
_t_contains "$(cat "${SYSTEMD_UNIT_DIR}/nvidia-performance.service")" \
	"ExecStart=/usr/bin/nvidia-smi -pm 1" "tweak_nvidia_gpu: writes the unit"
_t_contains "$(_t_calls)" "systemctl daemon-reload" "tweak_nvidia_gpu: reloads systemd"
_t_full_path

# Case 5: persistence mode off -> turned on.
arch_desktop_reset
_t_stub_stdin nvidia-smi <<'STUB'
[[ $1 == --query-gpu=persistence_mode ]] && { echo "Disabled"; exit 0; }
exit 0
STUB
_t_unstub nvidia-persistenced
_t_hide nvidia-persistenced
_t_run tweak_nvidia_gpu
_t_contains "$(_t_calls)" "nvidia-smi -pm 1" "tweak_nvidia_gpu: enables persistence mode"
_t_contains "$out" "persistence mode enabled" "tweak_nvidia_gpu: logs the change"
_t_full_path

# Case 6: an existing unit file is not rewritten.
arch_desktop_reset
_t_stub nvidia-smi 'exit 0'
printf 'CUSTOM UNIT\n' >"${SYSTEMD_UNIT_DIR}/nvidia-performance.service"
_t_unstub nvidia-persistenced
_t_hide nvidia-persistenced
_t_run tweak_nvidia_gpu
_t_eq "CUSTOM UNIT" "$(cat "${SYSTEMD_UNIT_DIR}/nvidia-performance.service")" \
	"tweak_nvidia_gpu: leaves an existing unit alone"
_t_full_path

# Case 7: nvidia-persistenced present but inactive -> enabled AND started.
arch_desktop_reset
_t_stub nvidia-smi 'exit 0'
_t_stub nvidia-persistenced 'exit 0'
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-active ]] && exit 1
exit 0
STUB
_t_run tweak_nvidia_gpu
_t_contains "$(_t_calls)" "systemctl enable nvidia-persistenced.service" \
	"tweak_nvidia_gpu: enables nvidia-persistenced"
_t_contains "$(_t_calls)" "systemctl start nvidia-persistenced.service" \
	"tweak_nvidia_gpu: starts an inactive nvidia-persistenced"

# Case 8: nvidia-persistenced already active -> enabled but NOT started.
arch_desktop_reset
_t_stub nvidia-smi 'exit 0'
_t_stub nvidia-persistenced 'exit 0'
_t_stub systemctl 'exit 0'
_t_run tweak_nvidia_gpu
_t_lacks "$(_t_calls)" "systemctl start nvidia-persistenced.service" \
	"tweak_nvidia_gpu: does not start an already-active persistenced"

printf '\narch_hardware (fstrim/nvidia): %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
