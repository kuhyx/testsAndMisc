#!/usr/bin/env bash
# lib/tests/test_arch_hardware_boot.sh — arch_hardware (boot/journal) — tweak_mitigations, tweak_nm_wait_online, tweak_journal and tweak_ananicy.
#
# Split from test_arch_hardware.sh to hold every file under the 250-line cap.
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

printf '\n-- tweak_mitigations --\n'

# Case 9: not aggressive -> nothing happens.
arch_desktop_reset
_t_run tweak_mitigations
_t_eq "0" "$?" "tweak_mitigations: returns 0 without --aggressive"
_t_contains "$out" "use --aggressive" "tweak_mitigations: explains how to opt in"

# Case 10: aggressive, but no boot loader found.
arch_desktop_reset
AGGRESSIVE="true"
_t_run tweak_mitigations
_t_contains "$out" "Could not detect boot loader" \
	"tweak_mitigations: warns when no boot loader is present"

# Case 11: systemd-boot, mitigations not yet set -> appended to the options line.
arch_desktop_reset
AGGRESSIVE="true"
mkdir -p "${LOADER_ENTRIES_DIR}"
printf 'title Arch\noptions root=/dev/sda2 rw\n' >"${LOADER_ENTRIES_DIR}/arch.conf"
_t_run tweak_mitigations
_t_contains "$(cat "${LOADER_ENTRIES_DIR}/arch.conf")" "rw mitigations=off" \
	"tweak_mitigations: appends to the systemd-boot options line"
_t_contains "$out" "REBOOT REQUIRED" "tweak_mitigations: warns a reboot is needed"

# Case 12: systemd-boot, already set -> left alone.
arch_desktop_reset
AGGRESSIVE="true"
mkdir -p "${LOADER_ENTRIES_DIR}"
printf 'options root=/dev/sda2 rw mitigations=off\n' >"${LOADER_ENTRIES_DIR}/arch.conf"
_t_run tweak_mitigations
_t_contains "$out" "already set in systemd-boot" \
	"tweak_mitigations: reports systemd-boot already configured"

# Case 13: systemd-boot directory present but EMPTY -> no entry, no crash.
arch_desktop_reset
AGGRESSIVE="true"
mkdir -p "${LOADER_ENTRIES_DIR}"
_t_run tweak_mitigations
_t_eq "0" "$?" "tweak_mitigations: survives an empty loader entries dir"

# Case 14: GRUB, not yet set -> cmdline rewritten and grub-mkconfig run.
arch_desktop_reset
AGGRESSIVE="true"
printf 'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\n' >"${GRUB_DEFAULT_FILE}"
_t_run tweak_mitigations
_t_contains "$(cat "${GRUB_DEFAULT_FILE}")" 'quiet splash mitigations=off' \
	"tweak_mitigations: appends to the GRUB cmdline"
_t_contains "$(_t_calls)" "grub-mkconfig" "tweak_mitigations: regenerates the GRUB config"

# Case 15: GRUB, already set -> left alone.
arch_desktop_reset
AGGRESSIVE="true"
printf 'GRUB_CMDLINE_LINUX_DEFAULT="quiet mitigations=off"\n' >"${GRUB_DEFAULT_FILE}"
_t_run tweak_mitigations
_t_contains "$out" "already set in GRUB" "tweak_mitigations: reports GRUB already configured"
_t_lacks "$(_t_calls)" "grub-mkconfig" "tweak_mitigations: does not regenerate when unchanged"

printf '\n-- tweak_nm_wait_online --\n'

# Case 16: already disabled -> skip.
arch_desktop_reset
_t_stub systemctl 'exit 1'
_t_run tweak_nm_wait_online
_t_contains "$out" "already disabled" "tweak_nm_wait_online: reports the skip"

# Case 17: enabled -> disabled.
arch_desktop_reset
_t_stub systemctl 'exit 0'
_t_run tweak_nm_wait_online
_t_contains "$(_t_calls)" "systemctl disable NetworkManager-wait-online.service" \
	"tweak_nm_wait_online: disables the service"

printf '\n-- tweak_journal --\n'

# Case 18: a multi-gigabyte journal IS vacuumed. journalctl prints "4.2G"
# with NO space before the unit, which is exactly what the old regex missed:
# it required one, so this branch could never run on a real machine.
arch_desktop_reset
_t_stub_stdin journalctl <<'STUB'
[[ $1 == --disk-usage ]] && {
	echo "Archived and active journals take up 4.2G in the file system."
	exit 0
}
exit 0
STUB
_t_run tweak_journal
_t_contains "$(_t_calls)" "journalctl --vacuum-size=300M" \
	"tweak_journal: vacuums a 4.2G journal printed without a space"

# Case 19: the spaced form still matches, so the fix is a widening.
arch_desktop_reset
_t_stub_stdin journalctl <<'STUB'
[[ $1 == --disk-usage ]] && {
	echo "Archived and active journals take up 4.2 G in the file system."
	exit 0
}
exit 0
STUB
_t_run tweak_journal
_t_contains "$(_t_calls)" "journalctl --vacuum-size=300M" \
	"tweak_journal: still vacuums when the unit is spaced"

# Case 20: a megabyte-sized journal is left alone.
arch_desktop_reset
_t_stub_stdin journalctl <<'STUB'
[[ $1 == --disk-usage ]] && {
	echo "Archived and active journals take up 305.5M in the file system."
	exit 0
}
exit 0
STUB
_t_run tweak_journal
_t_lacks "$(_t_calls)" "journalctl --vacuum-size=300M" \
	"tweak_journal: does not vacuum a 305.5M journal"
_t_contains "$out" "already under 1GiB" "tweak_journal: reports the journal is small"
_t_contains "$(cat "${JOURNALD_CONF_DIR}/size-limit.conf")" "SystemMaxUse=300M" \
	"tweak_journal: writes the size cap drop-in"
_t_contains "$(_t_calls)" "systemctl restart systemd-journald" \
	"tweak_journal: restarts journald after writing the cap"

# Case 21: the cap is already configured -> not rewritten, journald not restarted.
arch_desktop_reset
_t_stub journalctl 'exit 0'
printf '[Journal]\nSystemMaxUse=300M\n' >"${JOURNALD_CONF_DIR}/size-limit.conf"
_t_run tweak_journal
_t_contains "$out" "size cap already configured" \
	"tweak_journal: reports the cap is already in place"
_t_lacks "$(_t_calls)" "systemctl restart systemd-journald" \
	"tweak_journal: does not restart journald when nothing changed"

printf '\n-- tweak_ananicy --\n'

# Case 22: ananicy-cpp already enabled -> skip.
arch_desktop_reset
_t_stub systemctl 'exit 0'
_t_run tweak_ananicy
_t_contains "$out" "ananicy-cpp is already enabled" "tweak_ananicy: reports the skip"

# Case 23: ananicy-cpp installed but not enabled -> enabled.
arch_desktop_reset
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-enabled ]] && exit 1
exit 0
STUB
_t_stub pacman 'exit 0'
_t_run tweak_ananicy
_t_contains "$(_t_calls)" "systemctl enable --now ananicy-cpp.service" \
	"tweak_ananicy: enables ananicy-cpp when the package is installed"

# Case 24: only the original ananicy is installed, and it is not enabled.
arch_desktop_reset
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-enabled ]] && exit 1
exit 0
STUB
_t_stub_stdin pacman <<'STUB'
[[ $2 == ananicy-cpp ]] && exit 1
exit 0
STUB
_t_run tweak_ananicy
_t_contains "$(_t_calls)" "systemctl enable --now ananicy.service" \
	"tweak_ananicy: falls back to the original ananicy"

# Case 25: the original ananicy is installed AND already enabled.
arch_desktop_reset
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-enabled && $2 == ananicy-cpp.service ]] && exit 1
exit 0
STUB
_t_stub_stdin pacman <<'STUB'
[[ $2 == ananicy-cpp ]] && exit 1
exit 0
STUB
_t_run tweak_ananicy
_t_contains "$out" "ananicy is already enabled" \
	"tweak_ananicy: reports the original ananicy already enabled"

# Case 26: neither package installed -> the AUR hint.
arch_desktop_reset
_t_stub_stdin systemctl <<'STUB'
[[ $1 == is-enabled ]] && exit 1
exit 0
STUB
_t_stub pacman 'exit 1'
_t_run tweak_ananicy
_t_contains "$out" "yay -S ananicy-cpp" "tweak_ananicy: prints the AUR install hint"

printf '\narch_hardware (boot/journal): %d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
