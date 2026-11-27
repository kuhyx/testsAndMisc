#!/bin/bash
# Switch swap to zswap: compressed RAM cache in front of the disk swapfiles.
#
# Persists zswap.enabled=1, zstd, a 35% pool cap (the RAM budget the 32 GiB
# zram device gets at ~3:1) and the shrinker on the kernel cmdline, removes
# the zram-generator conf, then switches live: swapoff zram0 first, zswap on
# after, so no page is ever compressed twice. When MemAvailable cannot absorb
# what zram holds, it leaves the live state alone and exits 3: reboot to
# apply. resume= stays on /swapfile. setup_zram.sh is the one-command revert.
#
# Env overrides (tests/VM): ZRAM_CONF plus those in lib/swap_switch.sh.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SRC_DIR
readonly SS_NAME=setup_zswap
readonly ZRAM_CONF="${ZRAM_CONF:-/etc/systemd/zram-generator.conf}"
readonly ZSWAP_TOKENS="zswap.enabled=1 zswap.compressor=zstd zswap.max_pool_percent=35 zswap.shrinker_enabled=1"
# shellcheck source=lib/swap_switch.sh
. "${SRC_DIR}/lib/swap_switch.sh"

# Drop the zram-generator conf so the next boot makes no zram0. The package
# stays installed: setup_zram.sh reinstalls the conf to revert.
disable_zram_conf() {
	[[ -e $ZRAM_CONF ]] || return 0
	as_root mkdir -p "$SWAP_SWITCH_BACKUP_DIR"
	as_root cp -p "$ZRAM_CONF" "${SWAP_SWITCH_BACKUP_DIR}/zram-generator.conf.last"
	as_root rm -f "$ZRAM_CONF"
	as_root systemctl daemon-reload
}

main() {
	ss_has_disk_swap || ss_die "no disk swap is active; zswap needs one to back it"
	ss_set_boot_tokens "$ZSWAP_TOKENS"
	disable_zram_conf
	if ss_zram_active; then
		ss_can_drain || ss_reboot_to_apply "zram0 holds more than MemAvailable can absorb"
		as_root swapoff "$ZRAM_DEV"
		# ExecStop resets the device and frees its memory.
		as_root systemctl stop systemd-zram-setup@zram0.service
	fi
	ss_zswap_set compressor zstd
	ss_zswap_set max_pool_percent 35
	ss_zswap_set shrinker_enabled Y
	ss_zswap_set enabled Y
	ss_report
}

main "$@"
exit $?
