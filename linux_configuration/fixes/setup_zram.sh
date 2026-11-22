#!/bin/bash
# Install fixes/zram-generator.conf and resize the live /dev/zram0 to match.
#
# Resizing needs the device reset, i.e. swapoff first: the zram pages move back
# into RAM (disk swap is NOT a target of swapoff), so the script refuses when
# MemAvailable could not absorb them. Disk swapfiles are left alone.
#
# Env overrides (tests/VM): ZRAM_CONF, ZRAM_WANT_BYTES, ZRAM_SKIP_APPLY=1.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SRC_DIR
readonly ZRAM_CONF="${ZRAM_CONF:-/etc/systemd/zram-generator.conf}"
readonly ZRAM_WANT_BYTES="${ZRAM_WANT_BYTES:-34359738368}" # 32 GiB
readonly DEV=/dev/zram0
readonly MIN_SPARE_KIB=$((2 * 1024 * 1024)) # keep 2 GiB free after swapoff

die() {
	echo "setup_zram: $*" >&2
	exit 1
}

as_root() {
	if [[ $EUID -eq 0 ]]; then "$@"; else sudo -n "$@"; fi
}

ensure_package() {
	[[ -x /usr/lib/systemd/system-generators/zram-generator ]] && return 0
	as_root pacman -S --needed --noconfirm zram-generator
}

disksize() {
	# sysfs is world-readable; blockdev needs root. Absent device reads as 0.
	cat /sys/block/zram0/disksize 2>/dev/null || echo 0
}

# KiB of RAM the swapoff will newly occupy: uncompressed data minus the
# compressed pages that get freed as it drains.
swapoff_cost_kib() {
	local line orig total
	line=$(zramctl --bytes --noheadings --raw -o DATA,TOTAL "$DEV")
	read -r orig total <<<"$line"
	echo $(((orig - total) / 1024))
}

mem_available_kib() {
	awk '/^MemAvailable:/ {print $2}' /proc/meminfo
}

resize_live() {
	if [[ -b $DEV ]] && swapon --noheadings --show=NAME | grep -qx "$DEV"; then
		local cost avail
		cost=$(swapoff_cost_kib)
		avail=$(mem_available_kib)
		((avail - cost >= MIN_SPARE_KIB)) ||
			die "MemAvailable ${avail}K too low to drain zram (needs ${cost}K + 2G spare)"
		as_root swapoff "$DEV"
	fi
	# udev probes the freed device after swapoff and holds it open for a moment
	# ("Device or resource busy" on reset), so settle and retry the restart:
	# ExecStop resets the device, ExecStart recreates it from the new conf.
	local try
	for try in 1 2 3 4 5; do
		as_root udevadm settle
		as_root systemctl restart systemd-zram-setup@zram0.service && break
		((try < 5)) || die "zram0 stayed busy after 5 resets"
		sleep 1
	done
	as_root systemctl start dev-zram0.swap 2>/dev/null || true
}

main() {
	ensure_package
	as_root install -D -m 644 "$SRC_DIR/zram-generator.conf" "$ZRAM_CONF"
	[[ ${ZRAM_SKIP_APPLY:-0} == 1 ]] && return 0
	as_root systemctl daemon-reload
	if [[ $(disksize) -ne $ZRAM_WANT_BYTES ]]; then
		resize_live
	fi
	[[ $(disksize) -eq $ZRAM_WANT_BYTES ]] || die "zram0 is $(disksize) bytes, want $ZRAM_WANT_BYTES"
	zramctl
	swapon --show
}

main "$@"
