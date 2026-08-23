#!/usr/bin/env bash
# Repair steps that operate on the kernel: depmod, the kernel image, the
# initramfs, and the pacman parallel-download check.
#
# Sourced by boot-repair, not executed. Split out of it verbatim to bring the
# entry script under the 250-line cap; it inherits the caller's strict mode,
# its $ROOT/$MODE globals and the output helpers defined there.
#
# shellcheck shell=bash
# shellcheck source=../boot-repair
# ----------------------------------------------------------------------------

# depmod output is what modprobe consults; the same skipped-hook bug that
# leaves the ESP stale also leaves modules.dep missing for the new kernel.
ensure_depmod() {
	local kver dep
	kver="$1"
	dep="$(rpath "/usr/lib/modules/${kver}/modules.dep")"
	if [[ -f $dep ]]; then
		ok "modules.dep present for $kver"
		return 0
	fi
	problem "modules.dep missing for $kver"
	if ! acting; then
		would "run depmod $kver"
		return 1
	fi
	if is_live; then
		depmod "$kver" || {
			problem "depmod $kver failed"
			return 1
		}
	else
		depmod -b "${ROOT%/}" "$kver" || {
			problem "depmod failed"
			return 1
		}
	fi
	repaired "generated modules.dep for $kver"
	return 0
}

# The core repair: make the ESP's kernel image match the installed module tree.
sync_kernel_image() {
	local kver src dest have
	kver="$1"
	src="$(rpath "/usr/lib/modules/${kver}/vmlinuz")"
	dest="$(rpath "${ESP_MOUNTPOINT}/vmlinuz-linux")"

	[[ -f $src ]] || {
		problem "no kernel image at $src"
		return 1
	}

	if [[ -f $dest ]]; then
		have="$(kernel_image_version "$dest" || true)"
		if [[ $have == "$kver" ]]; then
			ok "ESP kernel matches installed tree ($kver)"
			return 0
		fi
		problem "ESP kernel is ${have:-unreadable} but installed tree is $kver"
	else
		problem "no kernel image on the ESP"
	fi

	if ! acting; then
		would "install $kver to $dest"
		return 1
	fi
	install -Dm644 "$src" "$dest"
	repaired "installed kernel $kver to the ESP"
	return 0
}

# Which kernel an initramfs was built for. Prefers lsinitcpio, but falls back
# to scanning the image directly — lsinitcpio is not guaranteed to be present
# in a degraded emergency shell.
initramfs_version() {
	local img="$1" v=""
	[[ -r $img ]] || return 1
	if command -v lsinitcpio >/dev/null 2>&1; then
		v="$(lsinitcpio "$img" 2>/dev/null |
			grep -oE 'modules/[0-9]+\.[0-9]+\.[0-9]+-arch[0-9]+-[0-9]+' |
			head -1 | cut -d/ -f2 || true)"
	fi
	if [[ -z $v ]]; then
		v="$(grep -aoE 'modules/[0-9]+\.[0-9]+\.[0-9]+-arch[0-9]+-[0-9]+' "$img" 2>/dev/null |
			head -1 | cut -d/ -f2 || true)"
	fi
	[[ -n $v ]] || return 1
	printf '%s' "$v"
}

# Rebuild every preset so the initramfs matches the kernel we just installed.
rebuild_initramfs() {
	local kver img have
	kver="$1"
	img="$(rpath "${ESP_MOUNTPOINT}/initramfs-linux.img")"

	have="$(initramfs_version "$img" || true)"

	if [[ -n $have && $have == "$kver" ]]; then
		ok "initramfs matches $kver"
		return 0
	fi

	problem "initramfs is ${have:-missing/unknown}, expected $kver"
	if ! acting; then
		would "run mkinitcpio -P"
		return 1
	fi
	is_live || {
		warn "skipping mkinitcpio (--root given)"
		return 1
	}
	command -v mkinitcpio >/dev/null 2>&1 || {
		problem "mkinitcpio is not installed"
		return 1
	}
	mkinitcpio -P || {
		problem "mkinitcpio -P failed"
		return 1
	}
	repaired "rebuilt initramfs for $kver"
	return 0
}

# The actual root cause on this machine. With ParallelDownloads > 1, pacman-git
# segfaults every forked hook child, so mkinitcpio and depmod never run and the
# transaction still reports success.
check_parallel_downloads() {
	local conf value
	conf="$(rpath /etc/pacman.conf)"
	[[ -r $conf ]] || return 0
	value="$(grep -E '^[[:space:]]*ParallelDownloads[[:space:]]*=' "$conf" 2>/dev/null |
		tail -1 | sed 's/.*=[[:space:]]*//' | tr -d '[:space:]')"
	[[ -n $value ]] || {
		ok "ParallelDownloads not set (pacman default is serial)"
		return 0
	}
	if [[ $value == "1" ]]; then
		ok "ParallelDownloads = 1"
		return 0
	fi
	problem "ParallelDownloads = $value — forked alpm hooks segfault, silently skipping mkinitcpio"
	if ! acting; then
		would "set ParallelDownloads = 1 in $conf"
		return 1
	fi
	cp -a "$conf" "${conf}.bak-$(date +%Y%m%d-%H%M%S)"
	sed -i -E 's/^([[:space:]]*ParallelDownloads[[:space:]]*=[[:space:]]*).*/\11/' "$conf"
	repaired "set ParallelDownloads = 1"
	return 0
}
