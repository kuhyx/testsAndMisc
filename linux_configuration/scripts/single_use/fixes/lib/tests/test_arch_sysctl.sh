#!/usr/bin/env bash
# lib/tests/test_arch_sysctl.sh — tests for arch_sysctl.sh.
#
# Both functions share a shape: probe every parameter with `sysctl -n`, set
# needs_update when any current value differs from the wanted one, skip when
# nothing differs AND the drop-in already exists, otherwise write the drop-in
# and reload. The cases below walk each arm of that shape for both functions,
# plus tweak_network_sysctl's modprobe guard.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=arch_desktop_harness.sh
. "${SCRIPT_DIR}/arch_desktop_harness.sh"

# shellcheck source=../arch_sysctl.sh
. "${FIXES_DIR}/lib/arch_sysctl.sh"

printf '\n-- tweak_vm_sysctl --\n'

# A sysctl stub that reports every parameter as already at its wanted value,
# so needs_update stays false. Values are keyed by the parameter name in $2
# (sysctl is called as `sysctl -n KEY`).
_stub_sysctl_tuned() {
	_t_stub_stdin sysctl <<'STUB'
case "$2" in
vm.swappiness) echo 10 ;;
vm.vfs_cache_pressure) echo 50 ;;
vm.dirty_ratio) echo 15 ;;
vm.dirty_background_ratio) echo 5 ;;
vm.dirty_writeback_centisecs) echo 1500 ;;
vm.page-cluster) echo 0 ;;
net.core.default_qdisc) echo fq ;;
net.ipv4.tcp_congestion_control) echo bbr ;;
net.ipv4.tcp_fastopen) echo 3 ;;
net.core.rmem_max) echo 16777216 ;;
net.core.wmem_max) echo 16777216 ;;
net.ipv4.tcp_rmem) printf '4096\t1048576\t16777216\n' ;;
net.ipv4.tcp_wmem) printf '4096\t1048576\t16777216\n' ;;
net.ipv4.tcp_mtu_probing) echo 1 ;;
*) exit 0 ;;
esac
STUB
}

# Case 1: values already tuned AND the drop-in exists -> skip without writing.
arch_desktop_reset
_stub_sysctl_tuned
: >"${SYSCTL_DROPIN_DIR}/90-desktop-performance.conf"
_t_run tweak_vm_sysctl
_t_eq "0" "$?" "tweak_vm_sysctl: returns 0 when already tuned"
_t_contains "$out" "already tuned" "tweak_vm_sysctl: reports the skip"
_t_eq "" "$(_t_dropin 90-desktop-performance.conf)" \
	"tweak_vm_sysctl: leaves the existing drop-in untouched"
_t_lacks "$(_t_calls)" "sysctl --system" \
	"tweak_vm_sysctl: does not reload when skipping"

# Case 2: values already tuned but NO drop-in file -> must still write it.
# This is the arm that a naive "nothing to do" check would wrongly skip.
arch_desktop_reset
_stub_sysctl_tuned
_t_run tweak_vm_sysctl
_t_contains "$(_t_dropin 90-desktop-performance.conf)" "vm.swappiness = 10" \
	"tweak_vm_sysctl: writes the drop-in when it is missing"
_t_lacks "$out" "already tuned" \
	"tweak_vm_sysctl: does not report a skip when the drop-in is absent"

# Case 3: a value differs -> write the drop-in and reload.
arch_desktop_reset
_t_stub_stdin sysctl <<'STUB'
case "$2" in
vm.swappiness) echo 60 ;;
*) exit 0 ;;
esac
STUB
_t_run tweak_vm_sysctl
dropin="$(_t_dropin 90-desktop-performance.conf)"
_t_contains "$dropin" "vm.swappiness = 10" "tweak_vm_sysctl: writes swappiness"
_t_contains "$dropin" "vm.vfs_cache_pressure = 50" \
	"tweak_vm_sysctl: writes vfs_cache_pressure"
_t_contains "$dropin" "vm.page-cluster = 0" "tweak_vm_sysctl: writes page-cluster"
_t_contains "$dropin" "managed by optimize_arch_desktop.sh" \
	"tweak_vm_sysctl: stamps the drop-in as managed"
_t_contains "$(_t_calls)" "sysctl --system" "tweak_vm_sysctl: reloads sysctl"

# Case 4: sysctl failing outright (unknown key) still reaches the write path.
arch_desktop_reset
_t_stub sysctl 'exit 1'
_t_run tweak_vm_sysctl
_t_eq "0" "$?" "tweak_vm_sysctl: returns 0 when sysctl -n fails"
_t_contains "$(_t_dropin 90-desktop-performance.conf)" "vm.dirty_ratio = 15" \
	"tweak_vm_sysctl: writes the drop-in when current values are unreadable"

printf '\n-- tweak_network_sysctl --\n'

# Case 5: the tcp_bbr module is unavailable -> warn and return without writing.
arch_desktop_reset
_t_stub modprobe 'exit 1'
_t_run tweak_network_sysctl
_t_eq "0" "$?" "tweak_network_sysctl: returns 0 when tcp_bbr is unavailable"
_t_contains "$out" "tcp_bbr kernel module unavailable" \
	"tweak_network_sysctl: warns about the missing module"
_t_eq "" "$(_t_dropin 91-desktop-network.conf)" \
	"tweak_network_sysctl: writes nothing without tcp_bbr"

# Case 6: already tuned AND drop-in present -> skip. The tcp_rmem/tcp_wmem
# values come back tab-separated from the kernel, which is why the lib
# normalizes both sides through xargs before comparing; this case is what
# proves that normalization works.
arch_desktop_reset
_stub_sysctl_tuned
: >"${SYSCTL_DROPIN_DIR}/91-desktop-network.conf"
_t_run tweak_network_sysctl
_t_contains "$out" "already tuned" \
	"tweak_network_sysctl: skips when tab-separated values match"
_t_lacks "$(_t_calls)" "sysctl --system" \
	"tweak_network_sysctl: does not reload when skipping"

# Case 7: already tuned but no drop-in -> write it.
arch_desktop_reset
_stub_sysctl_tuned
_t_run tweak_network_sysctl
_t_contains "$(_t_dropin 91-desktop-network.conf)" "net.ipv4.tcp_congestion_control = bbr" \
	"tweak_network_sysctl: writes the drop-in when it is missing"

# Case 8: a value differs -> write and reload.
arch_desktop_reset
_t_stub_stdin sysctl <<'STUB'
case "$2" in
net.ipv4.tcp_congestion_control) echo cubic ;;
*) exit 0 ;;
esac
STUB
_t_run tweak_network_sysctl
dropin="$(_t_dropin 91-desktop-network.conf)"
_t_contains "$dropin" "net.core.default_qdisc = fq" \
	"tweak_network_sysctl: writes the qdisc"
_t_contains "$dropin" "net.ipv4.tcp_rmem = 4096 1048576 16777216" \
	"tweak_network_sysctl: writes the receive buffers"
_t_contains "$dropin" "net.ipv4.tcp_mtu_probing = 1" \
	"tweak_network_sysctl: writes mtu probing"
_t_contains "$(_t_calls)" "sysctl --system" "tweak_network_sysctl: reloads sysctl"

printf '\narch_sysctl: %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
