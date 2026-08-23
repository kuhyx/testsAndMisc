#!/usr/bin/env bash
# The two run modes: preflight and the full check sweep.
#
# Sourced by boot-repair, not executed. Split out of it verbatim to bring the
# entry script under the 250-line cap; it inherits the caller's strict mode,
# its $ROOT/$MODE globals and the output helpers defined there.
#
# Only function DEFINITIONS live here. The report block at the end of
# boot-repair stays inline on purpose: it is top-level code with `exit` calls,
# and sourcing it changes control flow -- tried it, 30 of 42 tests failed.
#
# shellcheck shell=bash
# shellcheck source=../boot-repair
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Modes
# ----------------------------------------------------------------------------

# PreTransaction gate: refuse a kernel upgrade when the ESP is not mounted,
# because that upgrade would write the kernel into the root filesystem instead.
run_preflight() {
	if boot_is_mounted; then
		printf 'boot-repair: ESP mounted at %s — proceeding.\n' "$ESP_MOUNTPOINT"
		exit 0
	fi
	cat >&2 <<EOF

  ==> boot-repair: ABORTING TRANSACTION

  $ESP_MOUNTPOINT is not mounted. Installing a kernel now would write it into
  the root filesystem, leaving the firmware booting a stale image whose
  modules this upgrade is about to delete.

  Fix it, then retry:
      sudo mount $ESP_MOUNTPOINT
      sudo $SCRIPT_NAME

EOF
	exit 1
}

run_checks() {
	local kver

	ensure_root_writable

	msg "Kernel / ESP consistency"
	check_fstab_options || true
	clean_shadow_files || true
	ensure_vfat || true
	mount_esp || true

	if ! kver="$(newest_complete_kernel)"; then
		problem "no complete kernel module tree found under $(rpath /usr/lib/modules)"
		msg ""
		msg "  Recover the kernel package first (offline, from cache):"
		msg "    pacman -U /var/cache/pacman/pkg/linux-*.pkg.tar.zst"
		return 1
	fi
	info "target kernel: $kver"

	ensure_depmod "$kver" || true

	# Only meaningful once the ESP is actually mounted; otherwise these would
	# write into the root filesystem — the very bug being repaired.
	if boot_is_mounted || ! is_live; then
		sync_kernel_image "$kver" || true
		rebuild_initramfs "$kver" || true
	else
		problem "ESP still unmounted — cannot sync the kernel image"
	fi

	msg ""
	msg "Upgrade safety"
	check_parallel_downloads || true
	return 0
}
