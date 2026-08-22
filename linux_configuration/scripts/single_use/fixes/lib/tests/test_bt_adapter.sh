#!/usr/bin/env bash
# Tests for lib/bt_adapter.sh: check_firmware and _download_firmware.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bt_harness.sh
. "${SCRIPT_DIR}/bt_harness.sh"

# shellcheck source=../bt_adapter.sh
. "${FIXES_DIR}/lib/bt_adapter.sh"

# _dmesg_out TEXT — stub dmesg to emit TEXT.
_dmesg_out() {
	printf '%s\n' "$1" >"${DEV}/dmesg_out"
	local body
	body="$(
		cat <<'DMESG_BODY'
cat "${LIB_TEST_DEV}/dmesg_out"
DMESG_BODY
	)"
	_t_stub dmesg "$body"
}

# _record_download ARGS... — stand-in for the real downloader, recording only.
_record_download() {
	printf 'download_called %s\n' "$*" >>"${DEV}/fixes"
}

# --- check_firmware ---------------------------------------------------------

# dmesg mentions no .hcd file at all: nothing is missing.
bt_reset
_dmesg_out "usb 1-1: new full-speed USB device number 2"
out="$(check_firmware 2>&1)"
_t_contains "$out" "No missing firmware detected" \
	"check_firmware: reports nothing missing when dmesg names no .hcd file"
_t_eq "" "$(_t_fixes)" "check_firmware: applies no fix when no firmware is missing"

# dmesg names a firmware file that is NOT present under the absolute
# /usr/lib/firmware the lib reads, so the download branch runs. The name is
# deliberately one no distribution ships; the "already installed" arm is
# covered by the real-path case below.
bt_reset
_dmesg_out "bluetooth hci0: Direct firmware load for brcm/BCM99999-nonexistent.hcd failed"
out="$(
	# Called indirectly by check_firmware.
	eval '_download_firmware() { _record_download "$@"; }'
	check_firmware 2>&1
)"
_t_contains "$out" "Missing firmware: brcm/BCM99999-nonexistent.hcd" \
	"check_firmware: warns about a firmware file dmesg reports as missing"
_t_contains "$out" "Downloading BCM99999-nonexistent.hcd" \
	"check_firmware: applies the download fix for missing firmware"
_t_contains "$(_t_fixes)" \
	"download_called https://github.com/winterheart/broadcom-bt-firmware/raw/master/brcm/BCM99999-nonexistent.hcd /usr/lib/firmware/brcm/BCM99999-nonexistent.hcd" \
	"check_firmware: builds the upstream URL and destination path for the download"

# A firmware file that IS present under /usr/lib/firmware is skipped. Which
# files exist varies by host, so this case is driven by whatever is really
# there and self-skips when the directory has none.
bt_reset
present_fw="$(find /usr/lib/firmware/brcm -name '*.hcd' -printf '%f\n' 2>/dev/null | head -1)"
if [[ -n $present_fw ]]; then
	_dmesg_out "bluetooth hci0: Direct firmware load for brcm/${present_fw} failed"
	out="$(check_firmware 2>&1)"
	_t_contains "$out" "Firmware brcm/${present_fw} already installed" \
		"check_firmware: skips a firmware file that is already installed"
	_t_eq "" "$(_t_fixes)" \
		"check_firmware: applies no fix when the firmware is already installed"
else
	_t_pass "check_firmware: SKIP already-installed case (no .hcd under /usr/lib/firmware/brcm)"
fi

# Several missing files in one dmesg dump are each handled, and duplicates
# collapse: the lib pipes through `sort -u`.
bt_reset
_dmesg_out "bluetooth hci0: Direct firmware load for brcm/BCM111.hcd failed
bluetooth hci0: Direct firmware load for brcm/BCM222.hcd failed
bluetooth hci0: Direct firmware load for brcm/BCM111.hcd failed"
out="$(
	eval '_download_firmware() { _record_download "$@"; }'
	check_firmware 2>&1
)"
_t_eq "2" "$(grep -c 'download_called' "${DEV}/fixes")" \
	"check_firmware: de-duplicates repeated firmware names via sort -u"
_t_contains "$(_t_fixes)" "brcm/BCM111.hcd" "check_firmware: handles the first missing file"
_t_contains "$(_t_fixes)" "brcm/BCM222.hcd" "check_firmware: handles the second missing file"

# --- _download_firmware -----------------------------------------------------

# wget succeeding is enough: curl is never reached.
bt_reset
dest="${TEST_TMPDIR}/fw/BCM.hcd"
rm -rf "${TEST_TMPDIR}/fw"
# Real call shapes: wget -q "$url" -O "$dest" and curl -sL "$url" -o "$dest",
# so the destination is the 4th argument to each.
_t_stub_writes wget 4 "fw-from-wget"
_t_stub_writes curl 4 "fw-from-curl"
_download_firmware "https://example.invalid/BCM.hcd" "$dest"
_t_eq "fw-from-wget" "$(cat "$dest")" \
	"_download_firmware: fetches with wget and writes the destination file"
_t_lacks "$(_t_calls)" "curl " \
	"_download_firmware: does not fall back to curl when wget succeeds"
_t_pass "_download_firmware: creates the destination directory (write above succeeded)"

# wget failing falls back to curl.
bt_reset
dest="${TEST_TMPDIR}/fw2/BCM.hcd"
rm -rf "${TEST_TMPDIR}/fw2"
_t_stub wget 'exit 1'
_t_stub_writes curl 4 "fw-from-curl"
_download_firmware "https://example.invalid/BCM.hcd" "$dest"
_t_eq "fw-from-curl" "$(cat "$dest")" \
	"_download_firmware: falls back to curl when wget fails"

echo
echo "bt_adapter (firmware): ${PASS} passed, ${FAIL} failed"
((FAIL == 0))
