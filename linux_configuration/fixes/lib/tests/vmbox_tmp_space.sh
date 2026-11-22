#!/usr/bin/env bash
# lib/tests/vmbox_tmp_space.sh — prove fix_tmp_space.sh inside a vmbox guest.
#
# Runs INSIDE the guest, as root, one phase per call so every call stays
# under a minute. Never run it on the host: it remounts /tmp, writes /etc
# and creates a 64G image. Not named test_*.sh, so run_all.sh (and CI) never
# picks it up. From the host:
#
#   vm new tmpspace
#   vm repo tmpspace ~/src/testsAndMisc --worktree       # lands in ~/testsAndMisc
#   C=~/testsAndMisc/linux_configuration/fixes/lib/tests/vmbox_tmp_space.sh
#   vm run tmpspace "sudo bash $C before"   # red: --verify-only exits 1
#   vm run tmpspace "sudo bash $C apply"
#   vm run tmpspace "sudo bash $C quota"
#   vm run tmpspace "sudo bash $C disk"
#   vm run tmpspace "sudo bash $C again"
#   vm run tmpspace 'sudo systemctl reboot'; vm start tmpspace
#   vm run tmpspace "sudo bash $C rebooted"
#
# Each phase prints one OK/FAIL line per check and exits non-zero on any FAIL.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly FIXES="${HERE}/../.."
readonly ENTRY="${FIXES}/fix_tmp_space.sh"
readonly HELPER="${FIXES}/tmp_quota.py"
readonly USER_NAME="${SUDO_USER:?run through sudo from the guest user}"
USER_UID="$(id -u "$USER_NAME")"
readonly USER_UID
readonly PROBE_USER=tmpqprobe
readonly TARGET_KIB=25165824 # 80% of 30G, in KiB
readonly CANARY=/tmp/vmbox-tmp-space-canary
readonly DISK_CANARY=/var/disktmp/vmbox-reboot-canary
FAILED=0

ok() { printf 'OK   %s\n' "$1"; }
bad() {
	printf 'FAIL %s\n' "$1"
	FAILED=1
}
# check WHAT CMD... — OK when CMD exits 0.
check() {
	local what="$1"
	shift
	if "$@" >/dev/null 2>&1; then ok "$what"; else bad "$what"; fi
}
as_user() { runuser -u "$1" -- "${@:2}"; }
cap_kib() { /usr/bin/python3 "$HELPER" get --uid "$1" --mount /tmp | cut -d' ' -f1; }
# check_cap CAP WHAT — OK when CAP is 80% of 30G within systemd's rounding.
check_cap() {
	if (($1 >= TARGET_KIB - 1024 && $1 <= TARGET_KIB + 1024)); then ok "$2"; else bad "$2"; fi
}

phase_before() {
	: >"$CANARY"
	findmnt -no OPTIONS /tmp
	if as_user "$USER_NAME" "$ENTRY" --verify-only; then
		bad "stock guest: --verify-only should report drift"
	else
		ok "stock guest: --verify-only exits non-zero (red)"
	fi
}

phase_apply() {
	"$ENTRY"
	local opts
	opts="$(findmnt -no OPTIONS /tmp)"
	printf 'findmnt /tmp: %s\n' "$opts"
	check "/tmp is size=30G" grep -q 'size=31457280k' <<<"$opts"
	check "/tmp kept usrquota" grep -q usrquota <<<"$opts"
	check "/tmp canary survived the remount" test -e "$CANARY"
	check "X11 socket survived the remount" test -S /tmp/.X11-unix/X0
	check "X server still answers" as_user "$USER_NAME" env DISPLAY=:0 xset q
	local cap
	cap="$(cap_kib "$USER_UID")"
	printf 'uid %s cap %s KiB (want %s)\n' "$USER_UID" "$cap" "$TARGET_KIB"
	check_cap "$cap" "logged-in user's cap is 80% of 30G"
	check "/dev/shm left alone" grep -qv 'size=31457280k' <<<"$(findmnt -no OPTIONS /dev/shm)"
}

phase_quota() {
	id "$PROBE_USER" >/dev/null 2>&1 || useradd -M "$PROBE_USER"
	local uid file=/tmp/vmbox-quota-probe out
	uid="$(id -u "$PROBE_USER")"
	/usr/bin/python3 "$HELPER" set --uid "$uid" --mount /tmp --limit-kib 51200
	if out="$(as_user "$PROBE_USER" dd if=/dev/zero of="$file" bs=1M count=60 2>&1)"; then
		bad "60M write under a 50M cap should fail"
	else
		grep -m1 'quota' <<<"$out" || true
		check "60M write under a 50M cap fails with EDQUOT" grep -q 'quota exceeded' <<<"$out"
	fi
	rm -f "$file"
	/usr/bin/python3 "$HELPER" set --uid "$uid" --mount /tmp --limit-kib 204800
	check "100M write after raising the cap live to 200M succeeds" \
		as_user "$PROBE_USER" dd if=/dev/zero of="$file" bs=1M count=100
	/usr/bin/python3 "$HELPER" get --uid "$uid" --mount /tmp
	rm -f "$file"
}

phase_disk() {
	findmnt -no SOURCE,FSTYPE,OPTIONS /var/disktmp
	check "/var/disktmp is an ext4 loop mount" \
		grep -q '^/dev/loop[0-9]* ext4' <<<"$(findmnt -no SOURCE,FSTYPE /var/disktmp)"
	check "/var/disktmp is mode 1777" test "$(stat -c %a /var/disktmp)" = 1777
	check "image is 64G sparse" test "$(stat -c %s /var/lib/disktmp/disktmp.img)" = 68719476736
	du -h /var/lib/disktmp/disktmp.img
	as_user "$USER_NAME" sh -c 'echo hello >/var/disktmp/vmbox-user-file'
	sync
	check "user's file landed inside the image" \
		grep -q 'vmbox-user-file' <<<"$(debugfs -R 'ls -l /' /var/lib/disktmp/disktmp.img 2>/dev/null)"
	as_user "$USER_NAME" sh -c ": >$DISK_CANARY"
}

phase_again() {
	local out
	out="$("$ENTRY")"
	printf 'second run: %s\n' "$out"
	check "second run prints one line" test "$(wc -l <<<"$out")" = 1
	check "second run says nothing changed" grep -q 'nothing changed' <<<"$out"
	check "--verify-only exits 0 as root" "$ENTRY" --verify-only
	as_user "$USER_NAME" "$ENTRY" --verify-only || true
	check "--verify-only exits 0 as the user" as_user "$USER_NAME" "$ENTRY" --verify-only
}

phase_rebooted() {
	findmnt -no OPTIONS /tmp
	check "/tmp is 30G from the drop-in" grep -q 'size=31457280k' <<<"$(findmnt -no OPTIONS /tmp)"
	journalctl -b -u "user-runtime-dir@${USER_UID}" --no-pager | grep 'quota.*/tmp' || true
	local cap
	cap="$(cap_kib "$USER_UID")"
	printf 'uid %s cap %s KiB at login\n' "$USER_UID" "$cap"
	check_cap "$cap" "login cap is systemd's 80% of 30G"
	check "/var/disktmp is mounted" findmnt -M /var/disktmp
	check "/var/disktmp was emptied at boot" test ! -e "$DISK_CANARY"
	check "--verify-only exits 0 after reboot" "$ENTRY" --verify-only
}

case "${1:-}" in
before) phase_before ;;
apply) phase_apply ;;
quota) phase_quota ;;
disk) phase_disk ;;
again) phase_again ;;
rebooted) phase_rebooted ;;
*)
	echo "Usage: $0 before|apply|quota|disk|again|rebooted" >&2
	exit 2
	;;
esac
exit "$FAILED"
