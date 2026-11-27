#!/usr/bin/env bash
# lib/tests/vmbox_swap.sh — prove setup_zram.sh / setup_zswap.sh in a vmbox
# guest (BIOS/GRUB): live switch both ways, persistence across a reboot,
# idempotence, and the exit-3 "reboot to apply" path.
#
# Runs INSIDE the guest, as root, one phase per call so each stays under a
# minute. Never on the host: it swaps zram off and rewrites GRUB. Not named
# test_*.sh, so run_all.sh and CI never pick it up. From the host:
#
#   vm new zsw; vm hibernate-setup zsw --swap-mb 8192
#   vm repo zsw ~/src/testsAndMisc --worktree     # lands in ~/testsAndMisc
#   C="sudo bash ~/testsAndMisc/linux_configuration/fixes/lib/tests/vmbox_swap.sh"
#   vm run zsw "$C zram";  vm run zsw 'sudo systemctl reboot'; vm start zsw
#   vm run zsw "$C booted-zram"; vm run zsw "$C again"
#   vm run zsw "$C zswap"; vm run zsw "$C again"
#   vm run zsw 'sudo systemctl reboot'; vm start zsw; vm run zsw "$C booted-zswap"
#   vm run zsw "$C zram"; vm run zsw "$C fill"; vm run zsw "$C exit3"
#   vm run zsw 'sudo systemctl reboot'; vm start zsw; vm run zsw "$C booted-zswap"
#
# The guest's zram device is scaled to the same RAM budget as the host's
# 32 GiB on ~30 GiB: 35 % of RAM compressed at the 3.2:1 the bench measures.
# Each phase prints one OK/FAIL line per check and exits non-zero on a FAIL.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly FIXES="${HERE}/../.."
readonly ZSWAP_TOKENS="zswap.enabled=1 zswap.compressor=zstd zswap.max_pool_percent=35 zswap.shrinker_enabled=1"
readonly P=/sys/module/zswap/parameters
readonly FILL_DIR=/mnt/swapfill
FAILED=0

ok() { printf 'OK   %s\n' "$1"; }
bad() {
	printf 'FAIL %s\n' "$1"
	FAILED=1
}
# want WHAT EXPECTED ACTUAL
want() { if [[ $3 == "$2" ]]; then ok "$1"; else bad "$1 (want '$2', got '$3')"; fi; }
# has WHAT HAYSTACK NEEDLE
has() { if [[ $2 == *"$3"* ]]; then ok "$1"; else bad "$1 (no '$3' in: $2)"; fi; }

zram_mib() { awk '/^MemTotal:/ {print int($2 / 1024 * 35 * 32 / 1000)}' /proc/meminfo; }
zram_swap() { swapon --noheadings --show=NAME,PRIO | awk '$1 == "/dev/zram0" {print $2}'; }
grub_line() { grep '^GRUB_CMDLINE_LINUX_DEFAULT=' /etc/default/grub; }

check_zram_live() {
	want "zram0 is swap at prio 100" 100 "$(zram_swap)"
	want "zram0 compresses with zstd" zstd "$(zramctl --noheadings -o ALGORITHM /dev/zram0 | tr -d ' ')"
	want "zswap enabled=N" N "$(cat "$P/enabled")"
}

check_zswap_live() {
	want "no zram0 swap" "" "$(zram_swap)"
	want "zswap enabled=Y" Y "$(cat "$P/enabled")"
	want "zswap compressor=zstd" zstd "$(cat "$P/compressor")"
	want "zswap max_pool_percent=35" 35 "$(cat "$P/max_pool_percent")"
	want "zswap shrinker_enabled=Y" Y "$(cat "$P/shrinker_enabled")"
}

phase_zram() {
	ZRAM_SIZE_MIB="$(zram_mib)" bash "${FIXES}/setup_zram.sh"
	check_zram_live
	has "GRUB defaults carry zswap.enabled=0" "$(grub_line)" "zswap.enabled=0"
	has "grub.cfg carries zswap.enabled=0" "$(cat /boot/grub/grub.cfg)" "zswap.enabled=0"
}

phase_zswap() {
	bash "${FIXES}/setup_zswap.sh"
	check_zswap_live
	has "GRUB defaults carry the zswap tokens" "$(grub_line)" "$ZSWAP_TOKENS"
	has "grub.cfg carries the zswap tokens" "$(cat /boot/grub/grub.cfg)" "$ZSWAP_TOKENS"
	has "resume= kept" "$(grub_line)" "resume_offset="
}

phase_booted_zram() {
	has "/proc/cmdline has zswap.enabled=0" "$(cat /proc/cmdline)" "zswap.enabled=0"
	check_zram_live
}

phase_booted_zswap() {
	has "/proc/cmdline has the zswap tokens" "$(cat /proc/cmdline)" "$ZSWAP_TOKENS"
	check_zswap_live
}

# again — rerun the script of whichever setup is live; nothing may change.
phase_again() {
	local script=setup_zswap.sh before after out
	[[ -n $(zram_swap) ]] && script=setup_zram.sh
	before="$(
		md5sum /etc/default/grub /boot/grub/grub.cfg
		swapon --show
	)"
	out="$(ZRAM_SIZE_MIB="$(zram_mib)" bash "${FIXES}/${script}" 2>&1)"
	after="$(
		md5sum /etc/default/grub /boot/grub/grub.cfg
		swapon --show
	)"
	want "${script} rerun: GRUB files and swap list unchanged" "$before" "$after"
	has "${script} rerun: prints swapon --show" "$out" "NAME"
	want "${script} rerun: no cmdline change reported" "" "$(grep 'cmdline now' <<<"$out" || true)"
}

# fill — push more into zram than MemAvailable can take back: a tmpfs file
# is swappable shmem, and RAM stays full of the rest of it.
phase_fill() {
	mkdir -p "$FILL_DIR"
	mountpoint -q "$FILL_DIR" || mount -t tmpfs -o size=7G tmpfs "$FILL_DIR"
	yes "$(seq -s ' ' 1 40)" | head -c 5G >"${FILL_DIR}/blob" || true
	zramctl
	grep MemAvailable /proc/meminfo
}

phase_exit3() {
	local rc=0 out
	out="$(bash "${FIXES}/setup_zswap.sh" 2>&1)" || rc=$?
	want "setup_zswap exits 3 when zram cannot drain" 3 "$rc"
	has "setup_zswap says reboot to apply" "$out" "reboot to apply"
	want "zram0 still active" 100 "$(zram_swap)"
	want "zswap still off" N "$(cat "$P/enabled")"
	has "GRUB defaults already carry the zswap tokens" "$(grub_line)" "$ZSWAP_TOKENS"
}

main() {
	[[ $EUID -eq 0 ]] || {
		echo "run as root inside the guest" >&2
		exit 2
	}
	case "${1:-}" in
	zram) phase_zram ;;
	zswap) phase_zswap ;;
	booted-zram) phase_booted_zram ;;
	booted-zswap) phase_booted_zswap ;;
	again) phase_again ;;
	fill) phase_fill ;;
	exit3) phase_exit3 ;;
	*)
		echo "usage: $0 zram|zswap|booted-zram|booted-zswap|again|fill|exit3" >&2
		exit 2
		;;
	esac
	return "$FAILED"
}

main "$@"
exit $?
