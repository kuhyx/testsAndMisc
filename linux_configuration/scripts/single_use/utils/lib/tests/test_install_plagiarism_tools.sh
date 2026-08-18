#!/usr/bin/env bash
# End-to-end test for install_plagiarism_tools.sh's main()/print_summary(),
# which stay in the entry script rather than a lib. Runs the real script as a
# subprocess against the same fake python3/pip/git/java/wine as the lib tests,
# with HOME pointed at a throwaway tmpdir so INSTALL_DIR/VENV_DIR (derived
# from $HOME inside the script) land there too.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=plagiarism_harness.sh
. "${SCRIPT_DIR}/plagiarism_harness.sh"

readonly ENTRY_SCRIPT="${UTILS_DIR}/install_plagiarism_tools.sh"

# The entry script derives INSTALL_DIR/VENV_DIR from $HOME itself (a plain
# assignment near its top), independently of the lib tests' INSTALL_DIR/
# VENV_DIR harness variables. Running it as a real subprocess against the
# harness's $HOME means its paths land under $HOME, not under the harness's
# separate INSTALL_DIR/VENV_DIR -- so assertions below re-derive the same
# paths the script itself computes, rather than reusing the harness ones.
readonly ENTRY_INSTALL_DIR="${HOME}/.local/share/plagiarism-tools"
readonly ENTRY_VENV_DIR="${HOME}/.local/share/plagiarism-venv"

# --- full run, PATH already in ~/.local/bin -------------------------------

mkdir -p "${HOME}/.local/bin"
OUT_FULL="${TEST_TMPDIR}/out_full.log"
PATH="${FAKE_BIN}:${HOME}/.local/bin:${PATH}" bash "${ENTRY_SCRIPT}" >"${OUT_FULL}" 2>&1
_status=$?

if [[ "${_status}" -eq 0 ]]; then
	_t_pass "install_plagiarism_tools.sh exits zero on a full successful run"
else
	_t_fail "install_plagiarism_tools.sh should exit zero (log: $(cat "${OUT_FULL}"))"
fi

if grep -q "Open Source Plagiarism Detection Installer" "${OUT_FULL}"; then
	_t_pass "main prints the installer banner"
else
	_t_fail "main should print the installer banner"
fi

if grep -q "=== 1. Installing Python NLP-based Plagiarism Tools ===" "${OUT_FULL}"; then
	_t_pass "main runs stage 1 (Python NLP tools)"
else
	_t_fail "main should run stage 1"
fi

if grep -q "=== 2. Installing Sherlock Text Plagiarism Detector ===" "${OUT_FULL}"; then
	_t_pass "main runs stage 2 (Sherlock)"
else
	_t_fail "main should run stage 2"
fi

if grep -q "=== 3. Checking for Ferret" "${OUT_FULL}"; then
	_t_pass "main runs stage 3 (Ferret)"
else
	_t_fail "main should run stage 3"
fi

if grep -q "=== 4. WCopyfind Information" "${OUT_FULL}"; then
	_t_pass "main runs stage 4 (WCopyfind)"
else
	_t_fail "main should run stage 4"
fi

if grep -q "Installation Complete!" "${OUT_FULL}"; then
	_t_pass "main prints the summary"
else
	_t_fail "main should print the summary"
fi

if grep -q "Location: ${ENTRY_INSTALL_DIR}/check_plagiarism.py" "${OUT_FULL}"; then
	_t_pass "the summary reports the checker's installed location"
else
	_t_fail "the summary should report the checker's installed location"
fi

if grep -q "Location: ${ENTRY_INSTALL_DIR}/sherlock/sherlock.py" "${OUT_FULL}"; then
	_t_pass "the summary reports sherlock's installed location"
else
	_t_fail "the summary should report sherlock's installed location"
fi

if grep -q "Activate with: source ${ENTRY_VENV_DIR}/bin/activate" "${OUT_FULL}"; then
	_t_pass "the summary reports the venv activation command"
else
	_t_fail "the summary should report the venv activation command"
fi

# ~/.local/bin was already on PATH for this run, so the "add it to your PATH"
# nudge must not repeat in the summary.
if grep -q "Add ~/.local/bin to your PATH by adding this" "${OUT_FULL}"; then
	_t_fail "the summary should not repeat the PATH nudge when ~/.local/bin is already on PATH"
else
	_t_pass "the summary skips the PATH nudge when ~/.local/bin is already on PATH"
fi

# --- ~/.local/bin missing from PATH: the summary nudges once --------------

reset_state
rm -rf "${HOME}/.local"
OUT_NOPATH="${TEST_TMPDIR}/out_nopath.log"
PATH="${FAKE_BIN}:${PATH}" bash "${ENTRY_SCRIPT}" >"${OUT_NOPATH}" 2>&1

if grep -qc "Add ~/.local/bin to your PATH by adding this" "${OUT_NOPATH}"; then
	_t_pass "the summary nudges to add ~/.local/bin to PATH when it is missing"
else
	_t_fail "the summary should nudge to add ~/.local/bin to PATH when it is missing"
fi

printf '\nResults: %d passed, %d failed\n' "${PASS}" "${FAIL}"
[[ "${FAIL}" -eq 0 ]]
