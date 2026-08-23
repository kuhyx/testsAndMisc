#!/bin/bash

# ============================================================================
# Reversible live test for boot-repair.
#
# Fixture tests cannot exercise the parts that matter most — unmounting the
# ESP, the pre-transaction gate, and deleting shadow files off the real root
# filesystem. This does, on the real machine, and restores state afterwards.
#
# It refuses to start unless the system is already consistent, and an EXIT trap
# remounts the ESP no matter how it ends.
#
# Run: sudo ./tests/live_test.sh
# ============================================================================

set -uo pipefail

readonly BOOT_REPAIR="/usr/local/sbin/boot-repair"
readonly ESP="/boot"

PASS=0
FAIL=0
UNMOUNTED=0

pass() {
	PASS=$((PASS + 1))
	printf '  [PASS] %s\n' "$1"
}
fail() {
	FAIL=$((FAIL + 1))
	printf '  [FAIL] %s\n' "$1"
	[[ -n ${2:-} ]] && printf '         %s\n' "$2"
}

# Always put the ESP back, however we exit.
restore() {
	local rc=$?
	if [[ $UNMOUNTED -eq 1 ]] && ! findmnt -n "$ESP" >/dev/null 2>&1; then
		echo
		echo "RESTORE: remounting $ESP..."
		mount "$ESP" && echo "  remounted." || echo "  !! REMOUNT FAILED — run: sudo mount $ESP" >&2
	fi
	exit $rc
}
trap restore EXIT

[[ $EUID -eq 0 ]] || {
	echo "must run as root: sudo $0" >&2
	exit 2
}
[[ -x $BOOT_REPAIR ]] || {
	echo "$BOOT_REPAIR not installed; run ../install.sh first" >&2
	exit 2
}

echo "=== boot-repair live test ==="
echo

# --- Precondition: refuse to run on an already-broken system ----------------
echo "PRE: system must be consistent before we perturb it"
if "$BOOT_REPAIR" --dry-run >/dev/null 2>&1; then
	pass "system is consistent"
else
	echo "  ABORT: system is not consistent. Repair it first: sudo $BOOT_REPAIR" >&2
	exit 2
fi

ESP_KVER_BEFORE="$(grep -aoE '[0-9]+\.[0-9]+\.[0-9]+-arch[0-9]+-[0-9]+' "$ESP/vmlinuz-linux" | head -1)"
echo "  ESP kernel before: $ESP_KVER_BEFORE"

# --- 1. Pre-transaction gate passes while the ESP is mounted ----------------
echo
echo "TEST 1: --preflight allows a kernel transaction when the ESP is mounted"
if "$BOOT_REPAIR" --preflight >/dev/null 2>&1; then
	pass "gate opens (exit 0)"
else
	fail "gate opens (exit 0)" "preflight refused a mounted ESP"
fi

# --- 2. Unmount and confirm the gate closes ---------------------------------
echo
echo "TEST 2: --preflight BLOCKS a kernel transaction when the ESP is unmounted"
umount "$ESP" || {
	echo "  could not unmount $ESP (in use?)" >&2
	exit 2
}
UNMOUNTED=1
if "$BOOT_REPAIR" --preflight >/dev/null 2>&1; then
	fail "gate closes (exit 1)" "preflight allowed an unmounted ESP — pacman would corrupt the boot setup"
else
	pass "gate closes (exit 1)"
fi

# --- 3. Dry-run must not write while the ESP is unmounted -------------------
echo
echo "TEST 3: --dry-run detects the unmounted ESP and writes nothing"
out="$("$BOOT_REPAIR" --dry-run 2>&1)"
if [[ $out == *"is not mounted"* ]]; then
	pass "detects unmounted ESP"
else
	fail "detects unmounted ESP" "$out"
fi
if [[ -z "$(find "$ESP" -maxdepth 1 -type f 2>/dev/null)" ]]; then
	pass "dry-run wrote nothing into the unmounted mountpoint"
else
	fail "dry-run wrote nothing into the unmounted mountpoint" "files appeared under $ESP"
fi

# --- 4. The dangerous path: shadow files on the root filesystem -------------
echo
echo "TEST 4: shadow files are deleted, then the real ESP is mounted intact"
printf 'FAKE SHADOW vmlinuz 7.1.5-arch1-2\n' >"$ESP/vmlinuz-linux"
printf 'FAKE SHADOW initramfs modules/7.1.5-arch1-2\n' >"$ESP/initramfs-linux.img"
echo "  planted 2 shadow files in the unmounted $ESP"

out="$("$BOOT_REPAIR" 2>&1)"
while IFS= read -r line; do printf '    | %s\n' "$line"; done <<<"$out"

if [[ $out == *"shadow file"* ]]; then
	pass "shadow files detected and removed"
else
	fail "shadow files detected and removed"
fi
if findmnt -n "$ESP" >/dev/null 2>&1; then
	UNMOUNTED=0
	pass "ESP mounted by the repair"
else
	fail "ESP mounted by the repair"
fi

# --- 5. The real ESP survived unharmed --------------------------------------
echo
echo "TEST 5: the real ESP is intact"
for d in EFI loader; do
	if [[ -d $ESP/$d ]]; then
		pass "$ESP/$d preserved"
	else
		fail "$ESP/$d preserved" "boot-repair destroyed part of the real ESP!"
	fi
done

ESP_KVER_AFTER="$(grep -aoE '[0-9]+\.[0-9]+\.[0-9]+-arch[0-9]+-[0-9]+' "$ESP/vmlinuz-linux" 2>/dev/null | head -1)"
if [[ $ESP_KVER_AFTER == "$ESP_KVER_BEFORE" ]]; then
	pass "ESP kernel unchanged ($ESP_KVER_AFTER)"
else
	fail "ESP kernel unchanged" "was $ESP_KVER_BEFORE, now ${ESP_KVER_AFTER:-unreadable}"
fi

# --- 6. Back to a clean bill of health --------------------------------------
echo
echo "TEST 6: system is consistent again"
if "$BOOT_REPAIR" --dry-run >/dev/null 2>&1; then
	pass "final dry-run reports consistent"
else
	fail "final dry-run reports consistent"
fi

echo
echo "=== $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
