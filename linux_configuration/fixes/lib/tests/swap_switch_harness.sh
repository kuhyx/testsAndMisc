#!/usr/bin/env bash
# lib/tests/swap_switch_harness.sh — fake machine for setup_zram.sh,
# setup_zswap.sh and lib/swap_switch.sh.
#
# Sourced, not executed. Every path the scripts touch (loader entries, GRUB
# defaults, the zram conf, /sys/module/zswap, /sys/block/zram0, meminfo, the
# backup dir) is redirected into $TEST_TMPDIR through the scripts' env
# overrides, and the commands that change live state are stubs that update
# fixture files, so a second run sees the result of the first:
#
#   $DEV/swaps     active swap names, one per line (swapon/swapoff/systemctl)
#   $DEV/zramctl   "DATA TOTAL" bytes for zram0
#   zram disksize  $ZRAM_SYSFS/disksize, set by the systemd-zram-setup stub
#
# run_all.sh runs un-jailed in CI, so these overrides are all that keeps the
# suite off the real /boot and /sys.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export FIXES_DIR

# shellcheck source=lib_test_core.sh
. "${SCRIPT_DIR}/lib_test_core.sh"

export LOADER_ENTRIES_DIR="${TEST_TMPDIR}/boot/loader/entries"
export GRUB_DEFAULT_FILE="${TEST_TMPDIR}/etc/default/grub"
export GRUB_CFG_FILE="${TEST_TMPDIR}/boot/grub/grub.cfg"
export ZRAM_CONF="${TEST_TMPDIR}/etc/systemd/zram-generator.conf"
export ZSWAP_PARAMS_DIR="${TEST_TMPDIR}/sys/module/zswap/parameters"
export ZRAM_SYSFS="${TEST_TMPDIR}/sys/block/zram0"
export PROC_MEMINFO="${TEST_TMPDIR}/proc/meminfo"
export SWAP_SWITCH_BACKUP_DIR="${TEST_TMPDIR}/var/lib/swap-switch"
export ZRAM_GENERATOR_BIN="${TEST_TMPDIR}/zram-generator"
readonly GIB=1073741824
readonly WANT_BYTES=$((32 * GIB))
export WANT_BYTES

readonly HOST_OPTS="root=PARTUUID=x zswap.enabled=0 rw rootfstype=ext4 resume=UUID=y resume_offset=22429696"
export HOST_OPTS

# _sw_machine STATE — build a fresh fake machine. STATE is zram (zram0 active
# at 32G, zswap off), zswap (no zram, zswap on) or bare (neither).
_sw_machine() {
	local state="$1"
	rm -rf "${TEST_TMPDIR:?}/boot" "${TEST_TMPDIR:?}/etc" "${TEST_TMPDIR:?}/sys" \
		"${TEST_TMPDIR:?}/proc" "${TEST_TMPDIR:?}/var"
	mkdir -p "$LOADER_ENTRIES_DIR" "$ZSWAP_PARAMS_DIR" "$ZRAM_SYSFS" \
		"${PROC_MEMINFO%/*}" "${ZRAM_CONF%/*}"
	: >"$ZRAM_GENERATOR_BIN"
	chmod +x "$ZRAM_GENERATOR_BIN"
	local entry
	for entry in linux linux-fallback linux-lts; do
		printf 'title   Arch Linux (%s)\nlinux   /vmlinuz-%s\noptions %s\n' \
			"$entry" "$entry" "$HOST_OPTS" >"${LOADER_ENTRIES_DIR}/${entry}.conf"
	done
	printf 'MemTotal:       31000000 kB\nMemAvailable:   15000000 kB\n' >"$PROC_MEMINFO"
	printf '%s %s\n' $((11 * GIB)) $((3 * GIB)) >"${DEV}/zramctl"
	printf 'zstd\n' >"${ZSWAP_PARAMS_DIR}/compressor"
	printf '20\n' >"${ZSWAP_PARAMS_DIR}/max_pool_percent"
	printf 'Y\n' >"${ZSWAP_PARAMS_DIR}/shrinker_enabled"
	printf '/swapfile\n/swapfile2\n' >"${DEV}/swaps"
	case "$state" in
	zram)
		cp "${FIXES_DIR}/zram-generator.conf" "$ZRAM_CONF"
		printf '%s\n' "$WANT_BYTES" >"${ZRAM_SYSFS}/disksize"
		printf '/dev/zram0\n' >>"${DEV}/swaps"
		printf 'N\n' >"${ZSWAP_PARAMS_DIR}/enabled"
		;;
	zswap)
		sed -i 's/zswap.enabled=0/zswap.enabled=1 zswap.compressor=zstd zswap.max_pool_percent=35 zswap.shrinker_enabled=1/' \
			"${LOADER_ENTRIES_DIR}"/*.conf
		printf '0\n' >"${ZRAM_SYSFS}/disksize"
		printf 'Y\n' >"${ZSWAP_PARAMS_DIR}/enabled"
		printf '35\n' >"${ZSWAP_PARAMS_DIR}/max_pool_percent"
		;;
	bare)
		printf '0\n' >"${ZRAM_SYSFS}/disksize"
		printf 'N\n' >"${ZSWAP_PARAMS_DIR}/enabled"
		;;
	esac
	_t_reset_calls
}

# _sw_grub STATE — the _sw_machine STATE machine, booted by GRUB instead of
# systemd-boot: defaults carrying STATE's zswap words, grub.cfg built from them.
_sw_grub() {
	local words="zswap.enabled=0"
	_sw_machine "$1"
	[[ $1 == zswap ]] && words="zswap.enabled=1 zswap.compressor=zstd zswap.max_pool_percent=35 zswap.shrinker_enabled=1"
	rm -rf "$LOADER_ENTRIES_DIR"
	mkdir -p "${GRUB_DEFAULT_FILE%/*}" "${GRUB_CFG_FILE%/*}"
	printf 'GRUB_TIMEOUT=1\nGRUB_CMDLINE_LINUX=""\nGRUB_CMDLINE_LINUX_DEFAULT="loglevel=3 resume=/dev/vda2 %s"\n' \
		"$words" >"$GRUB_DEFAULT_FILE"
	grub-mkconfig -o "$GRUB_CFG_FILE"
	_t_reset_calls
}

# _sw_cfg_lines PATTERN — how many grub.cfg `linux` lines match PATTERN.
_sw_cfg_lines() { grep -P '^\s*linux\s' "$GRUB_CFG_FILE" | grep -c -- "$1"; }

# _sw_snapshot — checksum of every boot-config file, for byte-identity checks.
_sw_snapshot() {
	cat "${LOADER_ENTRIES_DIR}"/*.conf "$GRUB_DEFAULT_FILE" "$GRUB_CFG_FILE" 2>/dev/null | md5sum
}

# _sw_param NAME — current fake zswap parameter.
_sw_param() { cat "${ZSWAP_PARAMS_DIR}/$1"; }

_sw_stubs() {
	_t_stub_stdin sudo <<'STUB'
[[ $1 == -n ]] && shift
exec "$@"
STUB
	_t_stub udevadm 'exit 0'
	_t_stub pacman 'exit 0'
	# Writes grub.cfg the way Arch's does: tab-indented `linux` lines, the
	# default and fallback entries get both cmdline variables, recovery only
	# GRUB_CMDLINE_LINUX.
	_t_stub_stdin grub-mkconfig <<'STUB'
[[ $1 == -o ]] || exit 2
. "$GRUB_DEFAULT_FILE"
both="${GRUB_CMDLINE_LINUX:-} ${GRUB_CMDLINE_LINUX_DEFAULT:-}"
{
	printf 'menuentry "Arch Linux" {\n\tlinux\t/vmlinuz-linux root=UUID=x rw  %s\n}\n' "$both"
	printf 'menuentry "Arch Linux (fallback)" {\n\tlinux\t/vmlinuz-linux root=UUID=x rw  %s\n}\n' "$both"
	printf 'menuentry "Arch Linux (recovery)" {\n\tlinux\t/vmlinuz-linux root=UUID=x rw single %s\n}\n' "${GRUB_CMDLINE_LINUX:-}"
} >"$2"
STUB
	_t_stub_stdin swapon <<'STUB'
swaps="${LIB_TEST_DEV}/swaps"
case "$*" in
*--show=NAME*) cat "$swaps" ;;
*--show*) printf 'NAME TYPE\n'; sed 's/$/ swap/' "$swaps" ;;
*) printf '%s\n' "${*: -1}" >>"$swaps" ;;
esac
STUB
	_t_stub_stdin swapoff <<'STUB'
grep -vx -- "$1" "${LIB_TEST_DEV}/swaps" >"${LIB_TEST_DEV}/swaps.new" || true
mv "${LIB_TEST_DEV}/swaps.new" "${LIB_TEST_DEV}/swaps"
STUB
	_t_stub_cat zramctl zramctl
	_t_stub_stdin systemctl <<'STUB'
case "$*" in
"restart systemd-zram-setup@zram0.service")
	size="$(sed -n 's/^zram-size *= *//p' "$ZRAM_CONF")"
	echo $(((size) * 1024 * 1024)) >"${ZRAM_SYSFS}/disksize" ;;
"stop systemd-zram-setup@zram0.service") echo 0 >"${ZRAM_SYSFS}/disksize" ;;
"start dev-zram0.swap") echo /dev/zram0 >>"${LIB_TEST_DEV}/swaps" ;;
esac
exit 0
STUB
}
_sw_stubs
