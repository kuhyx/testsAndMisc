#!/bin/bash
# Grow the /tmp tmpfs to 30G and add a capped, disk-backed temp area.
#
# Sourced by fix_tmp_space.sh; the caller sets strict mode. Every function
# returns non-zero instead of exiting, so the tests can call them directly.
# Every path is env-overridable so tests/tmp_space_harness.sh can point it
# into a tmpdir (run_all.sh runs un-jailed in CI).
#
# Why: the stock tmp.mount is size=50% with usrquota, and systemd caps each
# user at 80% of it at login (systemd-user-runtime-dir). A heavy build hit
# that cap with EDQUOT on 2026-11-22.

TS_DROPIN_DIR="${TMP_MOUNT_DROPIN_DIR:-/etc/systemd/system/tmp.mount.d}"
TS_FSTAB="${FSTAB_FILE:-/etc/fstab}"
TS_TMPFILES_DIR="${TMPFILES_CONF_DIR:-/etc/tmpfiles.d}"
TS_IMAGE_DIR="${DISKTMP_IMAGE_DIR:-/var/lib/disktmp}"
TS_MOUNT="${DISKTMP_MOUNT:-/var/disktmp}"
TS_TMP="${TMP_MOUNT_POINT:-/tmp}"
TS_RUN_USER="${RUN_USER_DIR:-/run/user}"
# System python on purpose: the helper needs nothing outside the stdlib and
# must not depend on whichever venv is first on root's PATH.
TS_PYTHON="${TMP_SPACE_PYTHON:-/usr/bin/python3}"
TS_HELPER="${TMP_QUOTA_HELPER:-$(dirname "${BASH_SOURCE[0]}")/../tmp_quota.py}"
TS_IMAGE="${TS_IMAGE_DIR}/disktmp.img"

readonly TS_TMP_BYTES=$((30 * 1024 * 1024 * 1024))
# systemd's own login cap is 80% of the mount, computed from statfs with
# its own rounding; 1 MiB of slack lets its value count as "already right".
readonly TS_CAP_PERCENT=80
readonly TS_CAP_SLACK_KIB=1024

TS_CHANGED=0 # set by any write; the second run reports "nothing changed"

ts_say() { printf 'tmp-space: %s\n' "$*"; }
ts_err() { printf 'tmp-space: ERROR: %s\n' "$*" >&2; }
ts_human() { numfmt --to=iec "$1"; }

ts_dropin_body() {
	cat <<'DROPIN'
[Mount]
Options=mode=1777,strictatime,nosuid,nodev,size=30G,nr_inodes=1m,x-systemd.graceful-option=usrquota
DROPIN
}

# nofail drops the mount's ordering before local-fs.target, and with it the
# ordering before systemd-tmpfiles-setup: in the vmbox guest tmpfiles started
# 22 ms before the mount finished, so its boot-time emptying could hit the
# directory underneath instead of the image. x-systemd.before restores it.
ts_fstab_line() {
	printf '%s %s ext4 %s 0 0\n' "$TS_IMAGE" "$TS_MOUNT" \
		loop,nosuid,nodev,noatime,discard,nofail,x-systemd.before=systemd-tmpfiles-setup.service
}

ts_tmpfiles_body() { printf 'D %s 1777 root root 10d\n' "$TS_MOUNT"; }

# ts_fstype MOUNTPOINT — the filesystem type mounted exactly there, or "".
ts_fstype() { findmnt -no FSTYPE --mountpoint "$1" 2>/dev/null || true; }

ts_tmp_bytes() {
	local blocks bsize
	read -r blocks bsize < <(stat -f -c '%b %S' "$TS_TMP")
	printf '%s\n' $((blocks * bsize))
}

# ts_write FILE BODY — write BODY to FILE unless it already holds exactly it.
ts_write() {
	local file="$1" body="$2"
	[[ -f "$file" && "$(cat "$file")" == "$body" ]] && return 0
	mkdir -p "$(dirname "$file")"
	printf '%s\n' "$body" >"$file"
	ts_say "wrote ${file}"
	TS_CHANGED=1
}

# ts_fstab_state — "ours", "foreign" (another line owns the mount point) or
# "absent".
ts_fstab_state() {
	local want line
	want="$(ts_fstab_line)"
	while IFS= read -r line; do
		[[ "$line" == "$want" ]] && {
			echo ours
			return 0
		}
	done <"$TS_FSTAB"
	if awk -v m="$TS_MOUNT" '$1 !~ /^#/ && $2 == m { f = 1 } END { exit !f }' \
		"$TS_FSTAB"; then
		echo foreign
	else
		echo absent
	fi
}

ts_target_kib() { echo $(($(ts_tmp_bytes) * TS_CAP_PERCENT / 100 / 1024)); }

# ts_quota UID — "<limit_kib> <used_kib>" from the helper; fails with its
# message when quotactl does.
ts_quota() {
	"$TS_PYTHON" "$TS_HELPER" get --uid "$1" --mount "$TS_TMP"
}

# ts_uids — every logged-in non-root uid: the set systemd capped at login.
ts_uids() {
	local dir uid
	for dir in "$TS_RUN_USER"/*/; do
		uid="$(basename "$dir")"
		[[ "$uid" =~ ^[0-9]+$ ]] && ((uid != 0)) && echo "$uid"
	done
	return 0
}

ts_apply_files() {
	if [[ "$(ts_fstype "$TS_TMP")" != tmpfs ]]; then
		ts_err "${TS_TMP} is not a tmpfs; refusing to touch it"
		return 1
	fi
	local state
	state="$(ts_fstab_state)"
	if [[ "$state" == foreign ]]; then
		ts_err "${TS_FSTAB} already has a different line for ${TS_MOUNT}"
		return 1
	fi
	local before="$TS_CHANGED"
	ts_write "${TS_DROPIN_DIR}/size.conf" "$(ts_dropin_body)"
	if [[ "$state" == absent ]]; then
		# Fail-open on purpose: nofail lets the machine boot without the
		# image, and the 1777 directory underneath then takes the writes
		# uncapped instead of every command that uses it failing.
		printf '# Disk-backed temp area (fix_tmp_space.sh)\n%s\n' \
			"$(ts_fstab_line)" >>"$TS_FSTAB"
		ts_say "added ${TS_MOUNT} to ${TS_FSTAB}"
		TS_CHANGED=1
	fi
	# One reload covers the drop-in and the fstab line.
	if ((TS_CHANGED != before)); then
		systemctl daemon-reload || return 1
	fi
	ts_write "${TS_TMPFILES_DIR}/disktmp.conf" "$(ts_tmpfiles_body)"
}

# Remount live: never unmount or restart tmp.mount, /tmp/.X11-unix is there.
ts_apply_tmp() {
	(($(ts_tmp_bytes) == TS_TMP_BYTES)) && return 0
	mount -o remount,size=30G "$TS_TMP" || return 1
	ts_say "remounted ${TS_TMP} at 30G"
	TS_CHANGED=1
}

# Raise each logged-in user's cap live; systemd only sets it at login.
# Restarting user-runtime-dir@ would end the session, so never do that.
ts_apply_caps() {
	local target uid out limit
	target="$(ts_target_kib)"
	for uid in $(ts_uids); do
		out="$(ts_quota "$uid")" || return 1
		read -r limit _ <<<"$out"
		# 0 is "no limit": raising it to 80% would be a cut, not a raise.
		((limit == 0 || limit >= target - TS_CAP_SLACK_KIB)) && continue
		"$TS_PYTHON" "$TS_HELPER" set --uid "$uid" --mount "$TS_TMP" \
			--limit-kib "$target" >/dev/null || return 1
		ts_say "raised uid ${uid}'s ${TS_TMP} cap to $(ts_human $((target * 1024)))"
		TS_CHANGED=1
	done
}

ts_apply_disk() {
	# The directory stays searchable so --verify-only can stat the image as a
	# user; the image itself is 0600, it holds every user's temp files.
	mkdir -p "$TS_IMAGE_DIR"
	if [[ ! -e "$TS_IMAGE" ]]; then
		truncate -s 64G "$TS_IMAGE" || return 1
		chmod 0600 "$TS_IMAGE"
		mkfs.ext4 -F -q -m 0 -L disktmp "$TS_IMAGE" || return 1
		ts_say "created ${TS_IMAGE}"
		TS_CHANGED=1
	elif [[ "$(blkid -o value -s TYPE "$TS_IMAGE" 2>/dev/null)" != ext4 ]]; then
		# Fail-closed: never reformat a file this script did not just make.
		ts_err "${TS_IMAGE} exists but is not ext4; refusing to format it"
		return 1
	fi
	if [[ "$(ts_fstype "$TS_MOUNT")" != ext4 ]]; then
		mkdir -p "$TS_MOUNT"
		chmod 1777 "$TS_MOUNT" # the fail-open directory under the mount
		mount -T "$TS_FSTAB" "$TS_MOUNT" || return 1
		ts_say "mounted ${TS_MOUNT}"
		TS_CHANGED=1
	fi
	if [[ "$(stat -c %a "$TS_MOUNT")" != 1777 ]]; then
		chmod 1777 "$TS_MOUNT"
		TS_CHANGED=1
	fi
}

ts_apply() {
	TS_CHANGED=0
	ts_apply_files || return 1
	ts_apply_tmp || return 1
	ts_apply_caps || return 1
	ts_apply_disk || return 1
	((TS_CHANGED == 0)) && ts_say "already applied, nothing changed"
	return 0
}
