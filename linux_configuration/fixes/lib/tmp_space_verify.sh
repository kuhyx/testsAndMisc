#!/bin/bash
# fix_tmp_space.sh --verify-only: read-only report of every item ts_apply
# writes; sets TS_DRIFT and returns non-zero on any mismatch.
#
# Sourced after tmp_space.sh (split out for the 250-line cap); uses its paths,
# constants and probes. Changes nothing, so it runs without root: a user may
# read its own quota.

readonly TS_IMAGE_BYTES=$((64 * 1024 * 1024 * 1024))
TS_DRIFT=0 # set on any mismatch

# ts_report WHAT OK — one verify line; OK=0 marks drift.
ts_report() {
	if (($2)); then
		ts_say "$1"
	else
		ts_say "$1 DRIFT"
		TS_DRIFT=1
	fi
}

# ts_report_file FILE BODY — drift unless FILE holds exactly BODY.
ts_report_file() {
	local ok=0
	[[ -f "$1" && "$(cat "$1")" == "$2" ]] && ok=1
	ts_report "$1" "$ok"
}

ts_verify_caps() {
	local target uid out limit used
	target="$(ts_target_kib)"
	for uid in $(ts_uids); do
		if ! out="$(ts_quota "$uid")"; then
			TS_DRIFT=1
			continue
		fi
		read -r limit used <<<"$out"
		if ((limit == 0)); then
			ts_report "uid ${uid} cap unlimited, used $(ts_human $((used * 1024)))" 1
			continue
		fi
		ts_report "uid ${uid} cap $(ts_human $((limit * 1024))), used $(ts_human $((used * 1024))) (want $(ts_human $((target * 1024))))" \
			$((limit >= target - TS_CAP_SLACK_KIB))
	done
}

ts_verify_disk() {
	local size=0 mode
	[[ -f "$TS_IMAGE" ]] && size="$(stat -c %s "$TS_IMAGE")"
	if [[ "$(ts_fstype "$TS_MOUNT")" != ext4 ]]; then
		ts_report "${TS_MOUNT} $(ts_human "$size") image, not mounted" 0
		return 0
	fi
	mode="$(stat -c %a "$TS_MOUNT")"
	ts_report "${TS_MOUNT} $(ts_human "$size") image, mounted ext4, mode ${mode}" \
		$((size == TS_IMAGE_BYTES && mode == 1777))
}

# ts_verify — read-only; works without root (a user may read its own quota).
ts_verify() {
	TS_DRIFT=0
	local bytes
	bytes="$(ts_tmp_bytes)"
	ts_report "${TS_TMP} size $(ts_human "$bytes") (want 30G)" \
		$((bytes == TS_TMP_BYTES))
	ts_report_file "${TS_DROPIN_DIR}/size.conf" "$(ts_dropin_body)"
	local fstab_ok=0
	[[ "$(ts_fstab_state)" == ours ]] && fstab_ok=1
	ts_report "${TS_MOUNT} line in ${TS_FSTAB}" "$fstab_ok"
	ts_report_file "${TS_TMPFILES_DIR}/disktmp.conf" "$(ts_tmpfiles_body)"
	ts_verify_caps
	ts_verify_disk
	return "$TS_DRIFT"
}
