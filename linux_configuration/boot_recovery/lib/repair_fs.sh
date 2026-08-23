#!/usr/bin/env bash
# Repair steps that operate on the filesystem: root remount, /boot vfat
# handling, fstab options, and shadow-file cleanup.
#
# Sourced by boot-repair, not executed. Split out of it verbatim to bring the
# entry script under the 250-line cap; it inherits the caller's strict mode,
# its $ROOT/$MODE globals and the output helpers defined there.
#
# shellcheck shell=bash
# shellcheck source=../boot-repair
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Repair steps
# ----------------------------------------------------------------------------

# The root filesystem is sometimes left read-only after a failed boot; every
# later step would fail confusingly without this.
ensure_root_writable() {
	is_live || return 0
	local testfile
	testfile="$(rpath /.boot-repair-write-test)"
	if (: >"$testfile") 2>/dev/null; then
		rm -f "$testfile"
		return 0
	fi
	problem "root filesystem is read-only"
	if acting; then
		mount -o remount,rw / || die "could not remount / read-write"
		repaired "remounted / read-write"
	else
		would "remount / read-write"
	fi
}

# Restore just enough of the RUNNING kernel's module tree to mount a vfat ESP.
# Without this the repair cannot even reach the ESP: mounting it needs vfat,
# and vfat lives in the module tree the upgrade deleted.
ensure_vfat() {
	is_live || return 0
	if modprobe -n vfat >/dev/null 2>&1 && modprobe vfat >/dev/null 2>&1; then
		ok "vfat available"
		return 0
	fi

	problem "vfat cannot be loaded for the running kernel ($(uname -r))"
	if ! acting; then
		would "restore fat/nls modules from the pacman cache"
		return 1
	fi

	local kver pkgver cache pkg
	kver="$(uname -r)"
	# uname 7.0.5-arch1-1  ->  package 7.0.5.arch1-1
	pkgver="${kver/-arch/.arch}"
	cache="$(rpath /var/cache/pacman/pkg)"

	pkg=""
	if [[ -d $cache ]]; then
		# Newest matching cached kernel package for the running version.
		pkg="$(find "$cache" -maxdepth 1 -name "linux*-${pkgver}-*.pkg.tar.zst" 2>/dev/null | sort -V | tail -1)"
	fi
	if [[ -z $pkg ]]; then
		problem "no cached package for the running kernel in $cache"
		msg ""
		msg "  Cannot restore vfat offline. Recover with an Arch ISO:"
		msg "    mount /dev/<root> /mnt -o subvol=@ && arch-chroot /mnt"
		msg "    pacman -S linux && $SCRIPT_NAME"
		return 1
	fi

	info "restoring fat/nls modules from ${pkg##*/}"
	local tmp
	tmp="$(mktemp -d)" || die "mktemp failed"
	# shellcheck disable=SC2064  # expand $tmp now, on purpose
	trap "rm -rf '$tmp'" RETURN

	# Extract only the filesystem modules needed to read a FAT32 ESP.
	tar --zstd -xf "$pkg" -C "$tmp" --wildcards \
		"usr/lib/modules/${kver}/kernel/fs/fat/*" \
		"usr/lib/modules/${kver}/kernel/fs/nls/*" 2>/dev/null ||
		{
			problem "could not extract fat/nls modules from ${pkg##*/}"
			return 1
		}

	local src dest
	src="$tmp/usr/lib/modules/${kver}/kernel"
	dest="$(rpath "/usr/lib/modules/${kver}")"
	[[ -d $src ]] || {
		problem "cached package did not contain fat/nls modules"
		return 1
	}
	mkdir -p "$dest"
	cp -a "$src" "$dest/"
	depmod "$kver" 2>/dev/null || true
	if modprobe vfat >/dev/null 2>&1; then
		repaired "restored vfat for the running kernel"
		return 0
	fi
	problem "vfat still will not load after restore"
	return 1
}

# fstab must GATE on the ESP. `nofail` turns this failure into a silent boot of
# a stale kernel, which is strictly worse: the machine looks fine until the
# module tree disappears, one upgrade later.
check_fstab_options() {
	local opts fstab
	fstab="$(rpath /etc/fstab)"
	opts="$(fstab_boot_options)" || {
		problem "no /boot entry in $fstab"
		return 1
	}
	if [[ $opts != *noauto* && $opts != *nofail* ]]; then
		ok "fstab gates on /boot ($opts)"
		return 0
	fi
	problem "fstab has noauto/nofail on /boot ($opts) — failures would be silent"
	if ! acting; then
		would "rewrite the /boot options to 'defaults'"
		return 1
	fi
	cp -a "$fstab" "${fstab}.bak-$(date +%Y%m%d-%H%M%S)"
	# Rewrite only the options field of the /boot line.
	awk -v mp="$ESP_MOUNTPOINT" '
		/^[[:space:]]*#/ { print; next }
		NF >= 4 && $2 == mp { $4 = "defaults"; print; next }
		{ print }
	' OFS='\t' "$fstab" >"${fstab}.new"
	mv "${fstab}.new" "$fstab"
	repaired "fstab /boot options reset to 'defaults'"
	if is_live; then
		systemctl daemon-reload 2>/dev/null || true
	fi
	return 0
}

# Orphaned kernel files written into the ROOT filesystem's /boot directory
# while the ESP was unmounted. They shadow the real ESP and waste ~250 MB.
#
# This is the single most dangerous step in the script: doing it after mounting
# would delete the real kernel. Hence the three hard guards below.
clean_shadow_files() {
	local bootdir
	bootdir="$(rpath "$ESP_MOUNTPOINT")"
	[[ -d $bootdir ]] || return 0

	# GUARD 1: never touch a mounted /boot.
	if boot_is_mounted; then
		return 0
	fi
	# GUARD 2: a real ESP always has EFI/ or loader/. If either is present in
	# something we believe is unmounted, our mount detection is wrong — stop.
	if [[ -d $bootdir/EFI || -d $bootdir/loader ]]; then
		warn "unmounted $ESP_MOUNTPOINT contains EFI/ or loader/ — refusing to delete anything"
		return 1
	fi
	# GUARD 3: on a BIOS/GRUB system there is no ESP at all, so an unmounted
	# /boot is not a shadow — it is the only kernel the machine has. Deleting it
	# leaves the machine unbootable (measured 2026-08-22: a BIOS guest never
	# booted again). --esp is the deliberate override: naming the device by hand
	# asserts the firmware assumption that /sys/firmware/efi otherwise proves.
	if ! system_is_uefi && [[ -z $ESP_DEV_OVERRIDE ]]; then
		warn "no /sys/firmware/efi — this system booted via BIOS and has no ESP;"
		warn "  $ESP_MOUNTPOINT holds the real kernel. Refusing to delete anything."
		warn "  If that is wrong, name the ESP explicitly: $SCRIPT_NAME --esp DEVICE"
		return 1
	fi

	local -a shadows=()
	local f
	while IFS= read -r f; do
		[[ -n $f ]] && shadows+=("$f")
	done < <(find "$bootdir" -maxdepth 1 -type f \
		\( -name 'vmlinuz-*' -o -name 'initramfs-*.img' -o -name '*-ucode.img' \) 2>/dev/null)

	[[ ${#shadows[@]} -gt 0 ]] || return 0

	problem "${#shadows[@]} orphaned kernel file(s) in the unmounted $ESP_MOUNTPOINT (shadowing the ESP)"
	if ! acting; then
		would "delete: ${shadows[*]##*/}"
		return 1
	fi
	rm -f "${shadows[@]}"
	repaired "removed ${#shadows[@]} shadow file(s) from the root filesystem"
	return 0
}

mount_esp() {
	is_live || return 0
	if boot_is_mounted; then
		ok "$ESP_MOUNTPOINT mounted ($(findmnt -n -o SOURCE "$ESP_MOUNTPOINT"))"
		return 0
	fi
	problem "$ESP_MOUNTPOINT is not mounted"
	if ! acting; then
		would "mount the ESP at $ESP_MOUNTPOINT"
		return 1
	fi
	local dev
	dev="$(resolve_esp_device)" || {
		problem "could not determine the ESP device"
		return 1
	}
	mkdir -p "$ESP_MOUNTPOINT"
	mount -t vfat "$dev" "$ESP_MOUNTPOINT" || {
		problem "mounting $dev at $ESP_MOUNTPOINT failed"
		return 1
	}
	repaired "mounted $dev at $ESP_MOUNTPOINT"
	return 0
}
