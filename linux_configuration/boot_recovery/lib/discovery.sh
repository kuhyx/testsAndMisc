#!/usr/bin/env bash
# Path, kernel and ESP discovery, plus mount state.
#
# Sourced by boot-repair, not executed. Split out of it verbatim to bring the
# entry script under the 250-line cap; it inherits the caller's strict mode,
# its $ROOT/$MODE globals and the output helpers defined there.
#
# shellcheck shell=bash
# shellcheck source=../boot-repair
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Path helpers — everything is expressed relative to \$ROOT so the logic can be
# exercised against a fixture tree without touching the real machine.
# ----------------------------------------------------------------------------

# Join $ROOT with an absolute path, avoiding a doubled leading slash.
rpath() {
	local p="$1"
	if [[ $ROOT == "/" ]]; then
		printf '%s' "$p"
	else
		printf '%s%s' "${ROOT%/}" "$p"
	fi
}

# True when operating on the live system (so mount/modprobe are meaningful).
is_live() { [[ $ROOT == "/" ]]; }

# ----------------------------------------------------------------------------
# Kernel discovery
# ----------------------------------------------------------------------------

# Read the version banner out of a kernel image. Works on a bare file with no
# tooling beyond grep, which matters in a degraded emergency shell.
# Usage: kernel_image_version <path> -> prints e.g. 7.1.5-arch1-2, or nothing
kernel_image_version() {
	local img="$1"
	[[ -r $img ]] || return 1
	grep -aoE '[0-9]+\.[0-9]+\.[0-9]+-arch[0-9]+-[0-9]+' "$img" 2>/dev/null | head -1
}

# A module tree is "complete" only if it has both the kernel image and actual
# modules. The failure mode leaves behind a directory holding just the
# modules.* metadata files, which must not be mistaken for a usable kernel.
kernel_tree_complete() {
	local dir="$1"
	[[ -f $dir/vmlinuz ]] || return 1
	[[ -d $dir/kernel ]] || return 1
	return 0
}

# Newest complete module tree under $ROOT/usr/lib/modules, by version sort.
newest_complete_kernel() {
	local moddir kver best=""
	moddir="$(rpath /usr/lib/modules)"
	[[ -d $moddir ]] || return 1
	while IFS= read -r kver; do
		[[ -n $kver ]] || continue
		kernel_tree_complete "$moddir/$kver" || continue
		best="$kver"
	done < <(find "$moddir" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort -V)
	[[ -n $best ]] || return 1
	printf '%s' "$best"
}

# ----------------------------------------------------------------------------
# ESP discovery
# ----------------------------------------------------------------------------

# The fstab spec for /boot (e.g. "UUID=8A14-F8A7"), if present.
fstab_boot_spec() {
	local fstab spec mnt
	fstab="$(rpath /etc/fstab)"
	[[ -r $fstab ]] || return 1
	while read -r spec mnt _; do
		[[ $spec == \#* ]] && continue
		[[ -z ${spec:-} ]] && continue
		if [[ $mnt == "$ESP_MOUNTPOINT" ]]; then
			printf '%s' "$spec"
			return 0
		fi
	done <"$fstab"
	return 1
}

# The mount options field for /boot in fstab.
fstab_boot_options() {
	local fstab spec mnt opts
	fstab="$(rpath /etc/fstab)"
	[[ -r $fstab ]] || return 1
	while read -r spec mnt _ opts _; do
		[[ $spec == \#* ]] && continue
		[[ -z ${spec:-} ]] && continue
		if [[ $mnt == "$ESP_MOUNTPOINT" ]]; then
			printf '%s' "$opts"
			return 0
		fi
	done <"$fstab"
	return 1
}

# Resolve the fstab spec to a block device. Prefers /dev/disk/by-uuid so it
# works without blkid, which may be unavailable in a minimal shell.
resolve_esp_device() {
	local spec uuid dev
	if [[ -n $ESP_DEV_OVERRIDE ]]; then
		printf '%s' "$ESP_DEV_OVERRIDE"
		return 0
	fi
	spec="$(fstab_boot_spec)" || return 1
	case "$spec" in
	UUID=*)
		uuid="${spec#UUID=}"
		if [[ -e /dev/disk/by-uuid/$uuid ]]; then
			dev="$(readlink -f "/dev/disk/by-uuid/$uuid")"
			printf '%s' "$dev"
			return 0
		fi
		# Fall back to blkid when the by-uuid symlink is absent.
		if command -v blkid >/dev/null 2>&1; then
			dev="$(blkid -U "$uuid" 2>/dev/null)" && [[ -n $dev ]] && {
				printf '%s' "$dev"
				return 0
			}
		fi
		return 1
		;;
	/dev/*)
		printf '%s' "$spec"
		return 0
		;;
	*)
		return 1
		;;
	esac
}

# ----------------------------------------------------------------------------
# Mount state
# ----------------------------------------------------------------------------

boot_is_mounted() {
	is_live || return 1
	findmnt -n "$ESP_MOUNTPOINT" >/dev/null 2>&1
}

# True when the system booted via UEFI, i.e. an ESP can exist at all. The
# kernel only creates /sys/firmware/efi when it was loaded by EFI firmware.
#
# Expressed via rpath so a fixture tree can declare its own firmware type;
# on the live machine this resolves to the real /sys path and is exact.
system_is_uefi() { [[ -d "$(rpath /sys/firmware/efi)" ]]; }
