#!/usr/bin/env bash
# lib/tests/tmp_space_harness.sh — shared setup for the tmp_space.sh tests.
#
# Sourced, not executed. Builds on lib_test_core.sh and adds a fake machine:
#
#   * every path tmp_space.sh writes (the tmp.mount drop-in, fstab, the
#     tmpfiles.d entry, the image, both mount points, /run/user) is pointed
#     into $TEST_TMPDIR through the lib's env overrides;
#   * findmnt, stat -f, mount, systemctl, mkfs.ext4 and blkid are stubs that
#     read and update fixture files in $DEV, so a remount really changes what
#     the next statfs reports and a second run sees the result of the first
#     (truncate is logged, then real: a sparse 64G file costs nothing and
#     gives verify a real apparent size);
#   * the quota helper is a stub python that keeps one "<limit> <used>" file
#     per uid, in KiB, like the real tmp_quota.py prints.
#
# run_all.sh runs UN-jailed in ci_mirror.sh and in CI, so these overrides are
# the only thing between the suite and the real /etc/fstab.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck source=lib_test_core.sh
. "${SCRIPT_DIR}/lib_test_core.sh"

# Read by the lib under test, never by this harness; export makes it explicit.
export TMP_MOUNT_DROPIN_DIR="${TEST_TMPDIR}/etc/tmp.mount.d"
export FSTAB_FILE="${TEST_TMPDIR}/etc/fstab"
export TMPFILES_CONF_DIR="${TEST_TMPDIR}/etc/tmpfiles.d"
export DISKTMP_IMAGE_DIR="${TEST_TMPDIR}/var/lib/disktmp"
export DISKTMP_MOUNT="${TEST_TMPDIR}/var/disktmp"
export TMP_MOUNT_POINT="${TEST_TMPDIR}/tmp"
export RUN_USER_DIR="${TEST_TMPDIR}/run/user"
export TMP_SPACE_PYTHON="${FAKE_BIN}/fake-interp"
export TMP_QUOTA_HELPER="${FIXES_DIR}/tmp_quota.py"

readonly GIB=1073741824
# 16G stock tmpfs and its systemd-applied 80% cap, as on kuhy's host.
readonly STOCK_BLOCKS=$((16 * GIB / 4096))
readonly STOCK_CAP_KIB=13421772
readonly TARGET_CAP_KIB=25165824
export TARGET_CAP_KIB # read by the test files

# Fixture names: findmnt reports FSTYPE from fstype<path with / as _>.
_ts_fstype_fixture() {
	printf '%s/fstype%s' "${DEV}" "${1//\//_}"
}

_ts_stubs() {
	_t_stub_stdin findmnt <<'STUB'
target="${*: -1}"
f="${LIB_TEST_DEV}/fstype${target//\//_}"
[[ -f "$f" ]] || exit 1
cat "$f"
STUB
	# Only `stat -f` is faked: it reports /tmp's block count. Mode reads go
	# to the real stat, because the real chmod ran on the tmpdir.
	_t_stub_stdin stat <<'STUB'
if [[ "$1" == "-f" ]]; then
	printf '%s 4096\n' "$(cat "${LIB_TEST_DEV}/tmp_blocks")"
	exit 0
fi
exec /usr/bin/stat "$@"
STUB
	_t_stub_stdin mount <<'STUB'
[[ -f "${LIB_TEST_DEV}/mount_fails" ]] && exit 32
if [[ "$*" == *remount,size=30G* ]]; then
	printf '%s\n' $((30 * 1073741824 / 4096)) >"${LIB_TEST_DEV}/tmp_blocks"
else
	target="${*: -1}"
	printf 'ext4\n' >"${LIB_TEST_DEV}/fstype${target//\//_}"
fi
STUB
	_t_stub systemctl 'exit 0'
	_t_stub_stdin truncate <<'STUB'
exec /usr/bin/truncate "$@"
STUB
	_t_stub_stdin mkfs.ext4 <<'STUB'
printf 'ext4\n' >"${LIB_TEST_DEV}/blkid_type"
STUB
	_t_stub_stdin blkid <<'STUB'
[[ -f "${LIB_TEST_DEV}/blkid_type" ]] || exit 2
cat "${LIB_TEST_DEV}/blkid_type"
STUB
	_t_stub_stdin fake-interp <<'STUB'
# argv: <helper> get|set --uid N --mount M [--limit-kib K]
f="${LIB_TEST_DEV}/quota_$4"
[[ -f "${LIB_TEST_DEV}/helper_fails" ]] && {
	echo "tmp_quota: quotactl failed" >&2
	exit 1
}
if [[ "$2" == "get" ]]; then
	cat "$f"
else
	read -r _ used <"$f"
	printf '%s %s\n' "$8" "$used" >"$f"
fi
STUB
}

# ts_reset — a stock machine: /tmp a 16G tmpfs, uid 1000 logged in with
# systemd's cap, uid 0 present, no drop-in, no image, fstab with one line.
ts_reset() {
	_t_reset_calls
	rm -rf "${TEST_TMPDIR:?}/etc" "${TEST_TMPDIR:?}/var" "${TEST_TMPDIR:?}/run" \
		"${TMP_MOUNT_POINT}"
	rm -f "${DEV}"/fstype* "${DEV}"/quota_* "${DEV}/blkid_type" \
		"${DEV}/mount_fails" "${DEV}/helper_fails"
	mkdir -p "${TEST_TMPDIR}/etc" "${RUN_USER_DIR}/1000" "${RUN_USER_DIR}/0" \
		"${TMP_MOUNT_POINT}"
	printf 'UUID=abc / ext4 rw,noatime 0 1\n' >"${FSTAB_FILE}"
	printf '%s\n' "${STOCK_BLOCKS}" >"${DEV}/tmp_blocks"
	printf 'tmpfs\n' >"$(_ts_fstype_fixture "${TMP_MOUNT_POINT}")"
	printf '%s 2048\n' "${STOCK_CAP_KIB}" >"${DEV}/quota_1000"
	printf '0 0\n' >"${DEV}/quota_0"
}

_ts_stubs
