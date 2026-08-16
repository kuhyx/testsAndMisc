#!/bin/bash
# Test fixtures and the individual repair cases.
#
# Sourced by test_boot_repair.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# ----------------------------------------------------------------------------
# Fixture construction
# ----------------------------------------------------------------------------

# make_root <name> -> prints the path to a fresh fixture root
#
# Builds a consistent system: one complete kernel tree, an ESP whose kernel
# and initramfs match it, a gating fstab and serial downloads.
make_root() {
	local name="$1"
	local r="$WORKROOT/$name"
	local kver="${2:-7.1.5-arch1-2}"

	mkdir -p "$r/usr/lib/modules/$kver/kernel/fs/fat"
	mkdir -p "$r/boot" "$r/etc" "$r/var/cache/pacman/pkg"

	# Fake kernel image carrying the version banner boot-repair greps for.
	printf 'Linux version %s (linux@archlinux) fake image\n' "$kver" \
		>"$r/usr/lib/modules/$kver/vmlinuz"
	: >"$r/usr/lib/modules/$kver/modules.dep"
	: >"$r/usr/lib/modules/$kver/kernel/fs/fat/vfat.ko.zst"

	# ESP contents, consistent with the kernel tree.
	cp "$r/usr/lib/modules/$kver/vmlinuz" "$r/boot/vmlinuz-linux"
	printf 'usr/lib/modules/%s/kernel/fs/fat/vfat.ko.zst\n' "$kver" \
		>"$r/boot/initramfs-linux.img"
	mkdir -p "$r/boot/EFI" "$r/boot/loader"

	printf 'UUID=DEAD-BEEF\t/boot\tvfat\tdefaults\t0 2\n' >"$r/etc/fstab"
	printf 'ParallelDownloads = 1\n' >"$r/etc/pacman.conf"

	printf '%s' "$r"
}

run_repair() {
	"$BOOT_REPAIR" --root "$1" "${@:2}" 2>&1
}

# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------

test_healthy_system() {
	echo "TEST: healthy system reports consistent"
	local r out rc
	r="$(make_root healthy)"
	out="$(run_repair "$r" --dry-run)"
	rc=$?
	assert_eq "exit status is 0" "$rc" "0"
	assert_contains "reports consistent" "$out" "nothing to repair"
	assert_contains "picks the right kernel" "$out" "target kernel: 7.1.5-arch1-2"
}

test_stale_esp_kernel_detected() {
	echo "TEST: stale ESP kernel is detected and repaired"
	local r out rc
	r="$(make_root stale)"
	# Simulate the real incident: ESP still holds the previous kernel.
	printf 'Linux version 7.0.5-arch1-1 (linux@archlinux) fake image\n' \
		>"$r/boot/vmlinuz-linux"

	out="$(run_repair "$r" --dry-run)"
	rc=$?
	assert_eq "dry-run exits 1" "$rc" "1"
	assert_contains "detects the mismatch" "$out" "ESP kernel is 7.0.5-arch1-1 but installed tree is 7.1.5-arch1-2"
	assert_contains "dry-run changes nothing" "$out" "would install"

	# The ESP must be untouched by a dry run.
	assert_contains "dry-run left ESP alone" "$(cat "$r/boot/vmlinuz-linux")" "7.0.5-arch1-1"

	out="$(run_repair "$r")"
	assert_contains "repairs the kernel image" "$out" "installed kernel 7.1.5-arch1-2 to the ESP"
	assert_contains "ESP now has the new kernel" "$(cat "$r/boot/vmlinuz-linux")" "7.1.5-arch1-2"
}

test_incomplete_tree_ignored() {
	echo "TEST: a gutted module tree is not chosen as the target"
	local r out
	r="$(make_root gutted)"
	# The exact wreckage the failed upgrade leaves: metadata only, no kernel/,
	# no vmlinuz. It sorts newer, so a naive 'newest' pick would take it.
	mkdir -p "$r/usr/lib/modules/9.9.9-arch1-1"
	: >"$r/usr/lib/modules/9.9.9-arch1-1/modules.dep"
	: >"$r/usr/lib/modules/9.9.9-arch1-1/modules.alias"

	out="$(run_repair "$r" --dry-run)"
	assert_contains "ignores the incomplete tree" "$out" "target kernel: 7.1.5-arch1-2"
	assert_not_contains "does not pick 9.9.9" "$out" "target kernel: 9.9.9-arch1-1"
}

test_picks_newest_complete() {
	echo "TEST: newest COMPLETE tree wins"
	local r out kver
	r="$(make_root multi)"
	kver="7.2.0-arch1-1"
	mkdir -p "$r/usr/lib/modules/$kver/kernel/fs/fat"
	printf 'Linux version %s (linux@archlinux) fake image\n' "$kver" \
		>"$r/usr/lib/modules/$kver/vmlinuz"
	: >"$r/usr/lib/modules/$kver/modules.dep"

	out="$(run_repair "$r" --dry-run)"
	assert_contains "selects the newer complete tree" "$out" "target kernel: 7.2.0-arch1-1"
}

test_fstab_nofail_fixed() {
	echo "TEST: noauto/nofail on /boot is detected and reset"
	local r out
	r="$(make_root fstab)"
	printf 'UUID=DEAD-BEEF\t/boot\tvfat\tdefaults,noauto,nofail\t0 2\n' >"$r/etc/fstab"

	out="$(run_repair "$r" --dry-run)"
	assert_contains "detects the silent-failure options" "$out" "noauto/nofail"

	out="$(run_repair "$r")"
	assert_contains "resets the options" "$out" "reset to 'defaults'"
	assert_contains "fstab now gates" "$(cat "$r/etc/fstab")" "defaults"
	assert_not_contains "nofail is gone" "$(cat "$r/etc/fstab")" "nofail"
	# A backup must exist so the change is reversible.
	if compgen -G "$r/etc/fstab.bak-*" >/dev/null; then
		pass "fstab backup written"
	else
		fail "fstab backup written"
	fi
}

test_shadow_files_removed() {
	echo "TEST: shadow kernel files in an unmounted /boot are removed"
	local r out
	r="$(make_root shadow)"
	# An unmounted /boot has no EFI/ or loader/ — that is what makes the files
	# below shadows on the root filesystem rather than the real ESP.
	rm -rf "${r:?}/boot"
	mkdir -p "$r/boot"
	printf 'Linux version 7.1.5-arch1-2 (linux@archlinux) fake\n' >"$r/boot/vmlinuz-linux"
	printf 'usr/lib/modules/7.1.5-arch1-2/x\n' >"$r/boot/initramfs-linux.img"
	printf 'stale\n' >"$r/boot/initramfs-linux-fallback.img"

	out="$(run_repair "$r")"
	assert_contains "detects the shadows" "$out" "orphaned kernel file"
	assert_contains "removes them" "$out" "removed 3 shadow file"
	# The fallback image is not regenerated by a --root run, so its absence
	# proves the deletion happened. (vmlinuz-linux legitimately reappears:
	# sync_kernel_image reinstalls the target kernel straight afterwards.)
	if [[ ! -f $r/boot/initramfs-linux-fallback.img ]]; then
		pass "shadow fallback image deleted"
	else
		fail "shadow fallback image deleted"
	fi
}

test_shadow_guard_refuses_real_esp() {
	echo "TEST: SAFETY — never delete from a directory that looks like a real ESP"
	local r out
	r="$(make_root guarded)"
	# EFI/ and loader/ are present (make_root creates them), so even though the
	# fixture is "unmounted", boot-repair must refuse to delete anything.
	out="$(run_repair "$r")"
	assert_contains "refuses to delete" "$out" "refusing to delete anything"
	if [[ -f $r/boot/vmlinuz-linux ]]; then
		pass "real ESP kernel preserved"
	else
		fail "real ESP kernel preserved" "boot-repair deleted a real ESP kernel!"
	fi
}

test_parallel_downloads_fixed() {
	echo "TEST: ParallelDownloads > 1 is detected and set to 1"
	local r out
	r="$(make_root paralleldl)"
	printf 'ParallelDownloads = 5\n' >"$r/etc/pacman.conf"

	out="$(run_repair "$r" --dry-run)"
	assert_contains "detects the hook-segfault trigger" "$out" "ParallelDownloads = 5"

	out="$(run_repair "$r")"
	assert_contains "sets it to 1" "$out" "set ParallelDownloads = 1"
	assert_contains "config updated" "$(cat "$r/etc/pacman.conf")" "ParallelDownloads = 1"
}

test_missing_modules_dep() {
	echo "TEST: missing modules.dep is reported"
	local r out
	r="$(make_root nodep)"
	rm -f "$r/usr/lib/modules/7.1.5-arch1-2/modules.dep"

	out="$(run_repair "$r" --dry-run)"
	assert_contains "detects missing modules.dep" "$out" "modules.dep missing for 7.1.5-arch1-2"
}

test_no_kernel_at_all() {
	echo "TEST: no complete kernel tree gives actionable offline guidance"
	local r out rc
	r="$(make_root nokernel)"
	rm -rf "$r/usr/lib/modules"
	mkdir -p "$r/usr/lib/modules"

	out="$(run_repair "$r" --dry-run)"
	rc=$?
	assert_eq "exits non-zero" "$rc" "1"
	assert_contains "explains the offline recovery" "$out" "pacman -U /var/cache/pacman/pkg/linux-"
}

test_help_and_bad_args() {
	echo "TEST: CLI contract"
	local out rc
	out="$("$BOOT_REPAIR" --help 2>&1)"
	rc=$?
	assert_eq "--help exits 0" "$rc" "0"
	assert_contains "help mentions dry-run" "$out" "--dry-run"

	out="$("$BOOT_REPAIR" --nonsense 2>&1)"
	rc=$?
	assert_eq "unknown option exits 2" "$rc" "2"
}
