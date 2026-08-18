#!/usr/bin/env bash
# Unit tests for lib/plagiarism_sherlock.sh against the fake git in
# plagiarism_harness.sh. No real network is needed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=plagiarism_harness.sh
. "${SCRIPT_DIR}/plagiarism_harness.sh"

# --- upstream clone succeeds ---------------------------------------------

install_sherlock "${UTILS_DIR}" >/dev/null 2>&1

if grep -q '^git clone' "${DEV}/calls"; then
	_t_pass "install_sherlock clones the upstream sherlock-py tool"
else
	_t_fail "install_sherlock should attempt a git clone"
fi

if [[ -d "${INSTALL_DIR}/sherlock" ]]; then
	_t_pass "install_sherlock creates the sherlock directory on a successful clone"
else
	_t_fail "install_sherlock should create ${INSTALL_DIR}/sherlock"
fi

if [[ -f "${INSTALL_DIR}/sherlock/sherlock.py" ]]; then
	_t_fail "a successful clone should not also install the bundled fallback sherlock.py"
else
	_t_pass "a successful clone does not install the bundled fallback sherlock.py"
fi

# --- already installed: no-op, warns -------------------------------------

: >"${DEV}/calls"
install_sherlock "${UTILS_DIR}" >/dev/null 2>&1

if grep -q '^git clone' "${DEV}/calls"; then
	_t_fail "install_sherlock should not re-clone when already installed"
else
	_t_pass "install_sherlock skips reinstalling when the directory already exists"
fi

if grep -q "already installed" "${DEV}/warnings"; then
	_t_pass "install_sherlock warns that sherlock is already installed"
else
	_t_fail "install_sherlock should warn that sherlock is already installed"
fi

# --- clone fails: falls back to the bundled sherlock.py -------------------

reset_state
touch "${DEV}/fail_clone"
install_sherlock "${UTILS_DIR}" >/dev/null 2>&1

if [[ -f "${INSTALL_DIR}/sherlock/sherlock.py" ]]; then
	_t_pass "install_sherlock falls back to the bundled sherlock.py when the clone fails"
else
	_t_fail "install_sherlock should fall back to the bundled sherlock.py when the clone fails"
fi

if [[ -x "${INSTALL_DIR}/sherlock/sherlock.py" ]]; then
	_t_pass "the bundled fallback sherlock.py is installed executable"
else
	_t_fail "the bundled fallback sherlock.py should be installed executable"
fi

if grep -q "Could not clone sherlock-py" "${DEV}/warnings"; then
	_t_pass "install_sherlock warns when the clone fails, before falling back"
else
	_t_fail "install_sherlock should warn when the clone fails"
fi

# The installed fallback must be byte-identical to the source file: it is the
# one artifact the git-unavailable path can serve, so a stale copy would ship
# broken plagiarism detection silently.
if diff -q "${UTILS_DIR}/sherlock.py" "${INSTALL_DIR}/sherlock/sherlock.py" >/dev/null; then
	_t_pass "the installed fallback sherlock.py matches the source file byte-for-byte"
else
	_t_fail "the installed fallback sherlock.py should match ${UTILS_DIR}/sherlock.py"
fi

# --- git not available: warns, does not attempt to install ----------------

reset_state
NO_GIT_BIN="${TEST_TMPDIR}/no_git_bin"
mkdir -p "${NO_GIT_BIN}"
for tool in python3 java wine cat chmod mkdir; do
	[[ -x "$(command -v "${tool}")" ]] && ln -sf "$(command -v "${tool}")" "${NO_GIT_BIN}/${tool}"
done
PATH="${NO_GIT_BIN}" install_sherlock "${UTILS_DIR}" >/dev/null 2>&1

if [[ -d "${INSTALL_DIR}/sherlock" ]]; then
	_t_fail "install_sherlock should not create the sherlock directory without git"
else
	_t_pass "install_sherlock skips installation entirely when git is unavailable"
fi

if grep -q "Git not available" "${DEV}/warnings"; then
	_t_pass "install_sherlock warns when git is unavailable"
else
	_t_fail "install_sherlock should warn when git is unavailable"
fi

printf '\nResults: %d passed, %d failed\n' "${PASS}" "${FAIL}"
[[ "${FAIL}" -eq 0 ]]
