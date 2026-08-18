#!/usr/bin/env bash
# Unit tests for lib/plagiarism_optional.sh (Ferret/WCopyfind availability
# checks) against the fake java/wine in plagiarism_harness.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=plagiarism_harness.sh
. "${SCRIPT_DIR}/plagiarism_harness.sh"

_no_tool_path() {
	local skip="$1"
	local dir="${TEST_TMPDIR}/no_${skip}_bin"
	mkdir -p "${dir}"
	local tool
	for tool in python3 git java wine cat chmod mkdir; do
		[[ "${tool}" == "${skip}" ]] && continue
		[[ -x "$(command -v "${tool}")" ]] && ln -sf "$(command -v "${tool}")" "${dir}/${tool}"
	done
	printf '%s' "${dir}"
}

# --- check_ferret: java available -----------------------------------------

check_ferret >/tmp/plagiarism_optional_test.log 2>&1

if [[ -d "${INSTALL_DIR}/ferret" ]]; then
	_t_pass "check_ferret creates the ferret directory when java is available"
else
	_t_fail "check_ferret should create ${INSTALL_DIR}/ferret when java is available"
fi

if grep -q "requires manual download" "${DEV}/warnings"; then
	_t_pass "check_ferret explains that Ferret needs a manual download"
else
	_t_fail "check_ferret should explain that Ferret needs a manual download"
fi

# check_ferret creates the directory as a marker; a second run must not
# re-print the manual-download instructions once it already exists.
: >"${DEV}/warnings"
check_ferret >/tmp/plagiarism_optional_test.log 2>&1
if grep -q "requires manual download" "${DEV}/warnings"; then
	_t_fail "check_ferret should not repeat instructions once the ferret dir already exists"
else
	_t_pass "check_ferret is a no-op once the ferret directory already exists"
fi

# --- check_ferret: java unavailable ---------------------------------------

reset_state
no_java_path="$(_no_tool_path java)"
PATH="${no_java_path}" check_ferret >/dev/null 2>&1

if [[ -d "${INSTALL_DIR}/ferret" ]]; then
	_t_fail "check_ferret should not create the ferret directory without java"
else
	_t_pass "check_ferret skips Ferret entirely when java is unavailable"
fi

if grep -q "Java not installed" "${DEV}/warnings"; then
	_t_pass "check_ferret warns when java is unavailable"
else
	_t_fail "check_ferret should warn when java is unavailable"
fi

# --- check_wcopyfind: wine available ---------------------------------------

: >"${DEV}/warnings"
check_wcopyfind >/tmp/plagiarism_optional_test.log 2>&1

if grep -q "Wine is available" /tmp/plagiarism_optional_test.log; then
	_t_pass "check_wcopyfind reports Wine as available"
else
	_t_fail "check_wcopyfind should report Wine as available"
fi

if grep -q "requires manual download" "${DEV}/warnings"; then
	_t_pass "check_wcopyfind warns that WCopyfind needs a manual download"
else
	_t_fail "check_wcopyfind should warn that WCopyfind needs a manual download"
fi

# --- check_wcopyfind: wine unavailable --------------------------------------

: >"${DEV}/warnings"
no_wine_path="$(_no_tool_path wine)"
PATH="${no_wine_path}" check_wcopyfind >/tmp/plagiarism_optional_test.log 2>&1

if grep -q "Wine not installed" /tmp/plagiarism_optional_test.log; then
	_t_pass "check_wcopyfind reports Wine as unavailable"
else
	_t_fail "check_wcopyfind should report Wine as unavailable"
fi

if grep -q "skipped (Wine not available)" "${DEV}/warnings"; then
	_t_pass "check_wcopyfind warns that WCopyfind was skipped"
else
	_t_fail "check_wcopyfind should warn that WCopyfind was skipped"
fi

printf '\nResults: %d passed, %d failed\n' "${PASS}" "${FAIL}"
[[ "${FAIL}" -eq 0 ]]
