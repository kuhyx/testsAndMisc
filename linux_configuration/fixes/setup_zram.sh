#!/bin/bash
# Switch swap to zram (the default) and size /dev/zram0 to match the conf.
#
# Also the one-command revert from setup_zswap.sh: puts zswap.enabled=0 back
# on the kernel cmdline, installs fixes/zram-generator.conf, starts zram0,
# and only then turns zswap off live. That order is always safe: pages left
# in the zswap pool drain back as they fault in.
#
# Resizing needs the device reset, i.e. swapoff first: the zram pages move back
# into RAM (disk swap is NOT a target of swapoff), so the script refuses when
# MemAvailable could not absorb them. Disk swapfiles are left alone.
#
# Env overrides (tests/VM): ZRAM_CONF, ZRAM_SIZE_MIB (a smaller device for a
# small guest; default 32768), ZRAM_GENERATOR_BIN, ZRAM_SKIP_APPLY=1, plus
# those in lib/swap_switch.sh.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SRC_DIR
readonly SS_NAME=setup_zram
readonly ZRAM_CONF="${ZRAM_CONF:-/etc/systemd/zram-generator.conf}"
readonly ZRAM_SIZE_MIB="${ZRAM_SIZE_MIB:-32768}"
readonly ZRAM_WANT_BYTES=$((ZRAM_SIZE_MIB * 1024 * 1024))
readonly ZRAM_GENERATOR_BIN="${ZRAM_GENERATOR_BIN:-/usr/lib/systemd/system-generators/zram-generator}"
# shellcheck source=lib/swap_switch.sh
. "${SRC_DIR}/lib/swap_switch.sh"

ensure_package() {
	[[ -x $ZRAM_GENERATOR_BIN ]] && return 0
	as_root pacman -S --needed --noconfirm zram-generator
}

disksize() {
	# sysfs is world-readable; blockdev needs root. Absent device reads as 0.
	cat "${ZRAM_SYSFS}/disksize" 2>/dev/null || echo 0
}

# install_conf — the repo conf, with zram-size swapped for ZRAM_SIZE_MIB
# when that is not the default. Rewrites only when the content differs.
install_conf() {
	local tmp
	tmp="$(mktemp)"
	sed -E "s/^zram-size = .*/zram-size = ${ZRAM_SIZE_MIB}/" "$SRC_DIR/zram-generator.conf" >"$tmp"
	[[ $ZRAM_SIZE_MIB == 32768 ]] && cp "$SRC_DIR/zram-generator.conf" "$tmp"
	cmp -s "$tmp" "$ZRAM_CONF" || as_root install -D -m 644 "$tmp" "$ZRAM_CONF"
	rm -f "$tmp"
}

resize_live() {
	if [[ -b $ZRAM_DEV ]] && ss_zram_active; then
		ss_can_drain || ss_die "MemAvailable too low to drain zram (needs its contents + 2G spare)"
		as_root swapoff "$ZRAM_DEV"
	fi
	# udev probes the freed device after swapoff and holds it open for a moment
	# ("Device or resource busy" on reset), so settle and retry the restart:
	# ExecStop resets the device, ExecStart recreates it from the new conf.
	local try
	for try in 1 2 3 4 5; do
		as_root udevadm settle
		as_root systemctl restart systemd-zram-setup@zram0.service && break
		((try < 5)) || ss_die "zram0 stayed busy after 5 resets"
		sleep 1
	done
	as_root systemctl start dev-zram0.swap 2>/dev/null || true
}

main() {
	ensure_package
	ss_set_boot_tokens "zswap.enabled=0"
	install_conf
	[[ ${ZRAM_SKIP_APPLY:-0} == 1 ]] && return 0
	as_root systemctl daemon-reload
	if [[ $(disksize) -ne $ZRAM_WANT_BYTES ]] || ! ss_zram_active; then
		resize_live
	fi
	[[ $(disksize) -eq $ZRAM_WANT_BYTES ]] || ss_die "zram0 is $(disksize) bytes, want $ZRAM_WANT_BYTES"
	ss_zswap_set enabled N
	zramctl
	ss_report
}

main "$@"
exit $?
