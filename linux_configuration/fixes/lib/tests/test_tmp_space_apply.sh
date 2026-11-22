#!/usr/bin/env bash
# Tests for lib/tmp_space.sh: ts_apply on a stock machine, a second run, and
# every refusal (fail-closed) path.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=tmp_space_harness.sh
. "${SCRIPT_DIR}/tmp_space_harness.sh"

# shellcheck source=../tmp_space.sh
. "${FIXES_DIR}/lib/tmp_space.sh"
# shellcheck source=../tmp_space_verify.sh
. "${FIXES_DIR}/lib/tmp_space_verify.sh"

dropin="${TMP_MOUNT_DROPIN_DIR}/size.conf"
image="${DISKTMP_IMAGE_DIR}/disktmp.img"
want_opts='Options=mode=1777,strictatime,nosuid,nodev,size=30G,nr_inodes=1m,x-systemd.graceful-option=usrquota'

# --- first run on a stock machine -------------------------------------------

ts_reset
out="$(ts_apply 2>&1)"
rc=$?
calls="$(_t_calls)"
_t_eq "0" "$rc" "apply: exits 0 on a stock machine"
_t_eq "[Mount]
${want_opts}" "$(cat "$dropin" 2>/dev/null)" \
	"apply: drop-in keeps the stock options with size=30G"
_t_contains "$(cat "${FSTAB_FILE}")" "UUID=abc / ext4 rw,noatime 0 1" \
	"apply: keeps the existing fstab lines"
_t_contains "$(cat "${FSTAB_FILE}")" \
	"${image} ${DISKTMP_MOUNT} ext4 loop,nosuid,nodev,noatime,discard,nofail,x-systemd.before=systemd-tmpfiles-setup.service 0 0" \
	"apply: appends the disktmp loop line to fstab"
_t_eq "D ${DISKTMP_MOUNT} 1777 root root 10d" \
	"$(cat "${TMPFILES_CONF_DIR}/disktmp.conf" 2>/dev/null)" \
	"apply: tmpfiles entry empties and ages the disk area"
_t_eq "1" "$(grep -c '^systemctl daemon-reload' <<<"$calls")" \
	"apply: reloads systemd exactly once"
_t_lacks "$calls" "systemctl restart" "apply: never restarts a unit"
_t_lacks "$calls" "umount" "apply: never unmounts anything"
_t_contains "$calls" "mount -o remount,size=30G ${TMP_MOUNT_POINT}" \
	"apply: remounts /tmp live at 30G"
_t_contains "$calls" "fake-interp ${TMP_QUOTA_HELPER} set --uid 1000 --mount ${TMP_MOUNT_POINT} --limit-kib ${TARGET_CAP_KIB}" \
	"apply: raises uid 1000's cap to 80% of 30G"
_t_lacks "$calls" "set --uid 0" "apply: leaves root's unlimited quota alone"
_t_contains "$calls" "truncate -s 64G ${image}" "apply: creates a sparse 64G image"
_t_contains "$calls" "mkfs.ext4 -F -q -m 0 -L disktmp ${image}" \
	"apply: formats the image ext4 with no reserved blocks"
_t_contains "$calls" "mount -T ${FSTAB_FILE} ${DISKTMP_MOUNT}" \
	"apply: mounts the disk area through its fstab line"
_t_eq "1777" "$(/usr/bin/stat -c %a "${DISKTMP_MOUNT}")" \
	"apply: the disk area is world-writable with the sticky bit"
_t_eq "600" "$(/usr/bin/stat -c %a "$image")" \
	"apply: the image is readable by root only"
_t_contains "$out" "/tmp" "apply: reports what it changed"

# --- second run changes nothing and says so in one line ---------------------

before_fstab="$(cat "${FSTAB_FILE}")"
_t_reset_calls
out="$(ts_apply 2>&1)"
rc=$?
calls="$(_t_calls)"
_t_eq "0" "$rc" "apply again: exits 0"
_t_eq "1" "$(wc -l <<<"$out")" "apply again: prints exactly one line"
_t_contains "$out" "nothing changed" "apply again: says nothing changed"
_t_lacks "$calls" "systemctl" "apply again: no daemon-reload"
_t_eq "0" "$(grep -c '^mount ' <<<"$calls")" "apply again: no remount, no mount"
_t_lacks "$calls" "mkfs" "apply again: never reformats the image"
_t_lacks "$calls" " set " "apply again: no quota write"
_t_eq "$before_fstab" "$(cat "${FSTAB_FILE}")" "apply again: fstab unchanged"

# --- refusals: each fails closed and writes nothing it should not -----------

ts_reset
printf 'ext4\n' >"$(_ts_fstype_fixture "${TMP_MOUNT_POINT}")"
out="$(ts_apply 2>&1)"
_t_eq "1" "$?" "not tmpfs: apply fails"
_t_contains "$out" "not a tmpfs" "not tmpfs: says why"
_t_eq "0" "$(_t_calls | grep -vc '^findmnt')" "not tmpfs: only probes, runs nothing"
if [[ -e "$dropin" ]]; then
	_t_fail "not tmpfs: wrote the drop-in"
else
	_t_pass "not tmpfs: writes no drop-in"
fi

ts_reset
printf '/dev/sdb1 %s ext4 rw 0 2\n' "${DISKTMP_MOUNT}" >>"${FSTAB_FILE}"
out="$(ts_apply 2>&1)"
_t_eq "1" "$?" "foreign fstab line: apply fails"
_t_contains "$out" "already has a different line" "foreign fstab line: says why"
_t_eq "1" "$(grep -c "${DISKTMP_MOUNT}" "${FSTAB_FILE}")" \
	"foreign fstab line: is left as it was"

ts_reset
mkdir -p "${DISKTMP_IMAGE_DIR}"
printf 'data' >"$image"
printf 'xfs\n' >"${DEV}/blkid_type"
out="$(ts_apply 2>&1)"
_t_eq "1" "$?" "foreign image: apply fails"
_t_contains "$out" "not ext4" "foreign image: says why"
_t_lacks "$(_t_calls)" "mkfs" "foreign image: is never reformatted"

ts_reset
mkdir -p "${DISKTMP_IMAGE_DIR}"
printf 'data' >"$image"
out="$(ts_apply 2>&1)"
_t_eq "1" "$?" "unreadable image: apply fails"
_t_lacks "$(_t_calls)" "mkfs" "unreadable image: is never reformatted"

ts_reset
: >"${DEV}/helper_fails"
out="$(ts_apply 2>&1)"
_t_eq "1" "$?" "helper failure: apply fails"
_t_contains "$out" "quotactl failed" "helper failure: passes the helper's message on"

ts_reset
printf '0 0\n' >"${DEV}/quota_1000"
ts_apply >/dev/null 2>&1
_t_lacks "$(_t_calls)" "set --uid" "unlimited user: is not given a cap"

ts_reset
printf '%s 0\n' $((TARGET_CAP_KIB + 500)) >"${DEV}/quota_1000"
ts_apply >/dev/null 2>&1
_t_lacks "$(_t_calls)" "set --uid" "cap within systemd's rounding: left alone"

ts_reset
: >"${DEV}/mount_fails"
out="$(ts_apply 2>&1)"
_t_eq "1" "$?" "remount failure: apply fails"

echo
echo "tmp_space_apply: ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
