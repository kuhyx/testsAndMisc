#!/usr/bin/env bash
# lib/tests/test_swap_switch.sh — setup_zswap.sh / setup_zram.sh switch the
# swap setup live, persist it on the kernel cmdline, and are idempotent.
set -uo pipefail
# shellcheck source=swap_switch_harness.sh
. "$(dirname "${BASH_SOURCE[0]}")/swap_switch_harness.sh"

ZSWAP="${FIXES_DIR}/setup_zswap.sh"
ZRAM="${FIXES_DIR}/setup_zram.sh"
readonly ZSWAP ZRAM
# _absent PATH WHAT / _same A B WHAT — file assertions as plain if/else.
_absent() { if [[ -e $1 ]]; then _t_fail "$2"; else _t_pass "$2"; fi; }
_same() { if cmp -s "$1" "$2"; then _t_pass "$3"; else _t_fail "$3"; fi; }
readonly ZSWAP_TOKENS="zswap.enabled=1 zswap.compressor=zstd zswap.max_pool_percent=35 zswap.shrinker_enabled=1"

echo "zram -> zswap, live (C1)"
_sw_machine zram
_t_run bash "$ZSWAP"
_t_eq 0 "$?" "setup_zswap: exits 0 with room to drain zram"
_t_lacks "$(cat "${DEV}/swaps")" "/dev/zram0" "setup_zswap: zram0 swapped off"
_t_contains "$(_t_calls)" "swapoff /dev/zram0" "setup_zswap: ran swapoff on zram0"
_t_eq Y "$(_sw_param enabled)" "setup_zswap: enabled=Y"
_t_eq zstd "$(_sw_param compressor)" "setup_zswap: compressor=zstd"
_t_eq 35 "$(_sw_param max_pool_percent)" "setup_zswap: max_pool_percent=35"
for f in "${LOADER_ENTRIES_DIR}"/*.conf; do
	_t_contains "$(cat "$f")" "options root=PARTUUID=x ${ZSWAP_TOKENS} rw rootfstype=ext4 resume=UUID=y resume_offset=22429696" \
		"setup_zswap: $(basename "$f") has the zswap tokens in place, resume kept"
done
_t_eq 1 "$(grep -o 'zswap.enabled' "${LOADER_ENTRIES_DIR}/linux.conf" | wc -l)" \
	"setup_zswap: one zswap.enabled token per entry"
_absent "$ZRAM_CONF" "setup_zswap: zram conf removed"
_t_eq 3 "$(find "$SWAP_SWITCH_BACKUP_DIR" -name '*.conf.orig' | wc -l)" \
	"setup_zswap: backed up the three original entries"
_t_contains "$out" "/swapfile" "setup_zswap: prints swapon --show"

echo "zswap again is a no-op (C4)"
before="$(_sw_snapshot)"
_t_reset_calls
_t_run bash "$ZSWAP"
_t_eq 0 "$?" "setup_zswap rerun: exits 0"
_t_eq "$before" "$(_sw_snapshot)" "setup_zswap rerun: boot config byte-identical"
_t_lacks "$(_t_calls)" "swapoff" "setup_zswap rerun: no swapoff"
_t_lacks "$(_t_calls)" "daemon-reload" "setup_zswap rerun: no daemon-reload"

echo "zswap -> zram revert (C3)"
_t_reset_calls
_t_run bash "$ZRAM"
_t_eq 0 "$?" "setup_zram: exits 0"
_t_contains "$(cat "${DEV}/swaps")" "/dev/zram0" "setup_zram: zram0 is swap again"
_t_eq "$WANT_BYTES" "$(cat "${ZRAM_SYSFS}/disksize")" "setup_zram: zram0 is 32G"
_t_eq N "$(_sw_param enabled)" "setup_zram: zswap enabled=N"
_t_contains "$(cat "${LOADER_ENTRIES_DIR}/linux-lts.conf")" "options ${HOST_OPTS}" \
	"setup_zram: entry back to the original options line"
_same "${FIXES_DIR}/zram-generator.conf" "$ZRAM_CONF" "setup_zram: conf installed"

echo "zram again is a no-op (C4)"
before="$(_sw_snapshot)"
_t_reset_calls
_t_run bash "$ZRAM"
_t_eq 0 "$?" "setup_zram rerun: exits 0"
_t_eq "$before" "$(_sw_snapshot)" "setup_zram rerun: boot config byte-identical"
_t_lacks "$(_t_calls)" "swapoff" "setup_zram rerun: no swapoff"

echo "zram full, too little RAM: exit 3 (C5)"
_sw_machine zram
printf 'MemTotal: 31000000 kB\nMemAvailable:   9000000 kB\n' >"$PROC_MEMINFO"
_t_run bash "$ZSWAP"
_t_eq 3 "$?" "setup_zswap: exit 3 when zram cannot drain"
_t_contains "$out" "reboot to apply" "setup_zswap: says reboot to apply"
_t_contains "$(cat "${DEV}/swaps")" "/dev/zram0" "setup_zswap exit 3: zram0 still active"
_t_eq N "$(_sw_param enabled)" "setup_zswap exit 3: zswap still off"
_t_contains "$(cat "${LOADER_ENTRIES_DIR}/linux.conf")" "$ZSWAP_TOKENS" \
	"setup_zswap exit 3: next boot comes up on zswap"
_absent "$ZRAM_CONF" "setup_zswap exit 3: zram conf removed"

echo "no disk swap: refuse"
_sw_machine bare
: >"${DEV}/swaps"
_t_run bash "$ZSWAP"
_t_eq 1 "$?" "setup_zswap: refuses with no disk swap to back zswap"
_t_contains "$out" "no disk swap" "setup_zswap: names the missing backing swap"

echo "GRUB machine"
_sw_machine zram
rm -rf "$LOADER_ENTRIES_DIR"
mkdir -p "${GRUB_DEFAULT_FILE%/*}" "${GRUB_CFG_FILE%/*}"
printf 'GRUB_TIMEOUT=1\nGRUB_CMDLINE_LINUX_DEFAULT="loglevel=3 resume=/dev/vda2"\n' >"$GRUB_DEFAULT_FILE"
_t_run bash "$ZSWAP"
_t_eq 0 "$?" "setup_zswap grub: exits 0"
_t_contains "$(cat "$GRUB_DEFAULT_FILE")" "GRUB_CMDLINE_LINUX_DEFAULT=\"loglevel=3 resume=/dev/vda2 ${ZSWAP_TOKENS}\"" \
	"setup_zswap grub: tokens appended inside the quotes"
_t_contains "$(_t_calls)" "grub-mkconfig -o ${GRUB_CFG_FILE}" "setup_zswap grub: regenerated grub.cfg"
_t_reset_calls
_t_run bash "$ZSWAP"
_t_lacks "$(_t_calls)" "grub-mkconfig" "setup_zswap grub rerun: no grub-mkconfig"
_t_run bash "$ZRAM"
_t_contains "$(cat "$GRUB_DEFAULT_FILE")" 'GRUB_CMDLINE_LINUX_DEFAULT="loglevel=3 resume=/dev/vda2 zswap.enabled=0"' \
	"setup_zram grub: zswap.enabled=0 replaces the zswap tokens"

echo "grub-mkconfig failure is loud"
_t_stub grub-mkconfig 'echo boom >&2; exit 1'
_t_run bash "$ZSWAP"
_t_eq 1 "$?" "setup_zswap grub: grub-mkconfig failure exits 1"
_t_contains "$out" "grub-mkconfig failed: boom" "setup_zswap grub: shows grub-mkconfig's output"
_sw_stubs

echo "neither bootloader: refuse"
_sw_machine zram
rm -rf "$LOADER_ENTRIES_DIR"
_t_run bash "$ZSWAP"
_t_eq 1 "$?" "setup_zswap: refuses with no loader entries and no GRUB"

echo "scaled zram for a small guest"
_sw_machine zswap
ZRAM_SIZE_MIB=4370 _t_run bash "$ZRAM"
_t_eq 0 "$?" "setup_zram ZRAM_SIZE_MIB: exits 0"
_t_eq $((4370 * 1024 * 1024)) "$(cat "${ZRAM_SYSFS}/disksize")" "setup_zram ZRAM_SIZE_MIB: zram0 sized to it"
_t_contains "$(cat "$ZRAM_CONF")" "zram-size = 4370" "setup_zram ZRAM_SIZE_MIB: conf carries it"

echo "stale grub.cfg is rebuilt, zswap -> zram (C3)"
_sw_grub zswap
sed -i "s/${ZSWAP_TOKENS}/zswap.enabled=0/" "$GRUB_DEFAULT_FILE"
_t_run bash "$ZRAM"
_t_eq 0 "$?" "setup_zram stale grub.cfg: exits 0"
_t_contains "$(_t_calls)" "grub-mkconfig -o ${GRUB_CFG_FILE}" "setup_zram stale grub.cfg: rebuilt it"
_t_eq 2 "$(_sw_cfg_lines 'zswap.enabled=0')" "setup_zram stale grub.cfg: both linux lines boot zswap.enabled=0"
_t_eq 0 "$(_sw_cfg_lines 'zswap.enabled=1')" "setup_zram stale grub.cfg: no line boots zswap"
_t_contains "$out" "cmdline now carries" "setup_zram stale grub.cfg: reports the cmdline change"

echo "stale grub.cfg is rebuilt, zram -> zswap"
_sw_grub zram
sed -i "s/zswap.enabled=0/${ZSWAP_TOKENS}/" "$GRUB_DEFAULT_FILE"
_t_run bash "$ZSWAP"
_t_eq 0 "$?" "setup_zswap stale grub.cfg: exits 0"
_t_eq 2 "$(_sw_cfg_lines "$ZSWAP_TOKENS")" "setup_zswap stale grub.cfg: both linux lines boot the zswap tokens"
_t_eq 0 "$(_sw_cfg_lines 'zswap.enabled=0')" "setup_zswap stale grub.cfg: no line boots zswap.enabled=0"

echo "matching grub.cfg: no rebuild (C4)"
_sw_grub zswap
before="$(_sw_snapshot)"
_t_run bash "$ZSWAP"
_t_eq 0 "$?" "setup_zswap grub.cfg current: exits 0"
_t_lacks "$(_t_calls)" "grub-mkconfig" "setup_zswap grub.cfg current: no grub-mkconfig"
_t_eq "$before" "$(_sw_snapshot)" "setup_zswap grub.cfg current: boot config byte-identical"
_t_lacks "$out" "cmdline now" "setup_zswap grub.cfg current: reports no change"

echo "missing grub.cfg is rebuilt"
_sw_grub zram
rm -f "$GRUB_CFG_FILE"
_t_run bash "$ZRAM"
_t_eq 0 "$?" "setup_zram no grub.cfg: exits 0"
_t_eq 2 "$(_sw_cfg_lines 'zswap.enabled=0')" "setup_zram no grub.cfg: rebuilt with zswap.enabled=0"

echo "zswap words grub-mkconfig cannot fix: loud"
_sw_grub zram
sed -i 's/^GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="zswap.enabled=1"/' "$GRUB_DEFAULT_FILE"
grub-mkconfig -o "$GRUB_CFG_FILE" # the box booted with that cmdline already
_t_reset_calls
_t_run bash "$ZRAM"
_t_eq 1 "$?" "setup_zram GRUB_CMDLINE_LINUX: exits 1"
_t_contains "$out" "GRUB_CMDLINE_LINUX" "setup_zram GRUB_CMDLINE_LINUX: names where the words come from"
_t_contains "$out" "/vmlinuz-linux" "setup_zram GRUB_CMDLINE_LINUX: shows the offending linux line"
_t_lacks "$(_t_calls)" "swapoff" "setup_zram GRUB_CMDLINE_LINUX: no swapoff"

echo "loader entry without options: loud"
_sw_machine zswap
sed -i '/^options /d' "${LOADER_ENTRIES_DIR}/linux-lts.conf"
_t_run bash "$ZRAM"
_t_eq 1 "$?" "setup_zram no options line: exits 1"
_t_contains "$out" "linux-lts.conf" "setup_zram no options line: names the entry"
_t_lacks "$(_t_calls)" "swapoff" "setup_zram no options line: no swapoff"
_t_lacks "$(_t_calls)" "systemd-zram-setup" "setup_zram no options line: zram0 not started"
_t_eq Y "$(_sw_param enabled)" "setup_zram no options line: zswap still on"

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
