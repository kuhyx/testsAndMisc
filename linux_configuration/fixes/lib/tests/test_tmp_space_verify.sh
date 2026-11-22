#!/usr/bin/env bash
# Tests for lib/tmp_space.sh's ts_verify and the fix_tmp_space.sh entry
# script's argument and root handling.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=tmp_space_harness.sh
. "${SCRIPT_DIR}/tmp_space_harness.sh"

# shellcheck source=../tmp_space.sh
. "${FIXES_DIR}/lib/tmp_space.sh"
# shellcheck source=../tmp_space_verify.sh
. "${FIXES_DIR}/lib/tmp_space_verify.sh"

entry="${FIXES_DIR}/fix_tmp_space.sh"

# --- a stock machine is drift on every item ---------------------------------

ts_reset
out="$(ts_verify 2>&1)"
_t_eq "1" "$?" "verify stock: exits non-zero"
_t_contains "$out" "/tmp size 16G" "verify stock: prints the /tmp size"
_t_contains "$out" "want 30G" "verify stock: names the wanted size"
_t_contains "$out" "uid 1000 cap 13G" "verify stock: prints the user's cap"
_t_contains "$out" "not mounted" "verify stock: says the disk area is not mounted"
_t_contains "$out" "DRIFT" "verify stock: marks drift"
_t_eq "" "$(_t_calls | grep -v -e '^findmnt' -e '^stat' -e ' get ')" \
	"verify stock: only reads, never writes"

# --- after apply, verify is clean -------------------------------------------

ts_reset
ts_apply >/dev/null 2>&1
_t_reset_calls
out="$(ts_verify 2>&1)"
_t_eq "0" "$?" "verify applied: exits 0"
_t_contains "$out" "/tmp size 30G" "verify applied: /tmp is 30G"
_t_contains "$out" "uid 1000 cap 24G" "verify applied: cap is 80% of 30G"
_t_contains "$out" "used 2.0M" "verify applied: prints the user's use"
_t_contains "$out" "64G image, mounted ext4" "verify applied: disk area mounted"
_t_lacks "$out" "DRIFT" "verify applied: no drift"
_t_eq "0" "$(_t_calls | grep -c -e '^mount' -e '^systemctl' -e ' set ')" \
	"verify applied: runs no write"

# --- each single drift is caught --------------------------------------------

ts_reset
ts_apply >/dev/null 2>&1
printf '[Mount]\nOptions=size=50%%\n' >"${TMP_MOUNT_DROPIN_DIR}/size.conf"
out="$(ts_verify 2>&1)"
_t_eq "1" "$?" "edited drop-in: drift"
_t_contains "$out" "size.conf DRIFT" "edited drop-in: names the file"

ts_reset
ts_apply >/dev/null 2>&1
printf 'UUID=abc / ext4 rw,noatime 0 1\n' >"${FSTAB_FILE}"
out="$(ts_verify 2>&1)"
_t_eq "1" "$?" "missing fstab line: drift"
_t_contains "$out" "fstab DRIFT" "missing fstab line: names fstab"

ts_reset
ts_apply >/dev/null 2>&1
rm -f "${TMPFILES_CONF_DIR}/disktmp.conf"
out="$(ts_verify 2>&1)"
_t_eq "1" "$?" "missing tmpfiles entry: drift"

ts_reset
ts_apply >/dev/null 2>&1
printf '1000 0\n' >"${DEV}/quota_1000"
out="$(ts_verify 2>&1)"
_t_eq "1" "$?" "low cap: drift"
_t_contains "$out" "uid 1000 cap 1000K" "low cap: prints the low cap"

ts_reset
ts_apply >/dev/null 2>&1
printf '0 0\n' >"${DEV}/quota_1000"
out="$(ts_verify 2>&1)"
_t_eq "0" "$?" "unlimited user: not drift"
_t_contains "$out" "uid 1000 cap unlimited" "unlimited user: says so"

ts_reset
ts_apply >/dev/null 2>&1
chmod 0755 "${DISKTMP_MOUNT}"
out="$(ts_verify 2>&1)"
_t_eq "1" "$?" "wrong mode: drift"
_t_contains "$out" "mode 755" "wrong mode: prints the mode"

ts_reset
ts_apply >/dev/null 2>&1
: >"${DEV}/helper_fails"
out="$(ts_verify 2>&1)"
_t_eq "1" "$?" "helper failure: verify fails"
_t_contains "$out" "quotactl failed" "helper failure: passes the message on"

# --- entry script -----------------------------------------------------------

ts_reset
out="$("$entry" --bogus 2>&1)"
_t_eq "2" "$?" "entry: unknown option exits 2"
_t_contains "$out" "Usage:" "entry: unknown option prints usage"

out="$("$entry" --help 2>&1)"
_t_eq "0" "$?" "entry: --help exits 0"
_t_contains "$out" "--verify-only" "entry: --help documents --verify-only"

out="$("$entry" --verify-only 2>&1)"
_t_eq "1" "$?" "entry: --verify-only on a stock machine exits 1 without root"
_t_contains "$out" "DRIFT" "entry: --verify-only prints the drift"

if ((EUID != 0)); then
	_t_reset_calls
	out="$("$entry" 2>&1)"
	_t_eq "1" "$?" "entry: apply without root exits 1"
	_t_contains "$out" "must run as root" "entry: apply without root says why"
	_t_eq "" "$(_t_calls)" "entry: apply without root runs nothing"
fi

echo
echo "tmp_space_verify: ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
