#!/usr/bin/env bash
# Unit tests for lib/plagiarism_python.sh against the fake python3/pip in
# plagiarism_harness.sh. No real network or venv is needed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=plagiarism_harness.sh
. "${SCRIPT_DIR}/plagiarism_harness.sh"

# --- happy path ---------------------------------------------------------

install_python_nlp_tools "${UTILS_DIR}" >/tmp/plagiarism_python_test.log 2>&1
_status=$?
if [[ "${_status}" -eq 0 ]]; then
	_t_pass "install_python_nlp_tools succeeds against a working toolchain"
else
	_t_fail "install_python_nlp_tools should succeed (log: $(cat /tmp/plagiarism_python_test.log))"
fi

if [[ -d "${VENV_DIR}" ]]; then
	_t_pass "install_python_nlp_tools creates the virtual environment"
else
	_t_fail "install_python_nlp_tools should create ${VENV_DIR}"
fi

if grep -q '^python3 -m venv' "${DEV}/calls"; then
	_t_pass "install_python_nlp_tools invokes python3 -m venv"
else
	_t_fail "install_python_nlp_tools should invoke python3 -m venv"
fi

if grep -q 'pip install --upgrade pip' "${DEV}/calls"; then
	_t_pass "install_python_nlp_tools upgrades pip"
else
	_t_fail "install_python_nlp_tools should upgrade pip"
fi

if grep -q 'scikit-learn' "${DEV}/calls"; then
	_t_pass "install_python_nlp_tools installs the NLP package set"
else
	_t_fail "install_python_nlp_tools should install scikit-learn and friends"
fi

if grep -q 'ran:.*download_nltk_data.py' "${DEV}/scripts_run"; then
	_t_pass "install_python_nlp_tools runs download_nltk_data.py"
else
	_t_fail "install_python_nlp_tools should run download_nltk_data.py"
fi

if grep -q '^python3 -m spacy download' "${DEV}/calls"; then
	_t_pass "install_python_nlp_tools downloads the spaCy model"
else
	_t_fail "install_python_nlp_tools should download the spaCy model"
fi

if [[ -x "${INSTALL_DIR}/check_plagiarism.py" ]]; then
	_t_pass "install_python_nlp_tools installs check_plagiarism.py, executable"
else
	_t_fail "install_python_nlp_tools should install an executable check_plagiarism.py"
fi

if [[ -f "${INSTALL_DIR}/plagiarism_similarity.py" ]]; then
	_t_pass "install_python_nlp_tools installs plagiarism_similarity.py alongside it"
else
	_t_fail "install_python_nlp_tools should install plagiarism_similarity.py -- \
check_plagiarism.py imports it, so a missing copy breaks at runtime, not install time"
fi

if [[ -x "${HOME}/.local/bin/plagcheck" ]]; then
	_t_pass "install_python_nlp_tools creates an executable plagcheck wrapper"
else
	_t_fail "install_python_nlp_tools should create an executable plagcheck wrapper"
fi

if grep -q "${VENV_DIR}/bin/activate" "${HOME}/.local/bin/plagcheck"; then
	_t_pass "plagcheck wrapper activates the venv it was installed against"
else
	_t_fail "plagcheck wrapper should reference ${VENV_DIR}/bin/activate"
fi

if grep -q "${INSTALL_DIR}/check_plagiarism.py" "${HOME}/.local/bin/plagcheck"; then
	_t_pass "plagcheck wrapper points at the installed checker script"
else
	_t_fail "plagcheck wrapper should point at ${INSTALL_DIR}/check_plagiarism.py"
fi

# --- venv already exists: warn, don't recreate --------------------------

reset_state
mkdir -p "${VENV_DIR}/bin"
cat >"${VENV_DIR}/bin/activate" <<'ACTEOF'
deactivate() { :; }
pip() { printf '%s\n' "pip $*" >>"${PLAGIARISM_TEST_DEV}/calls"; return 0; }
ACTEOF
: >"${DEV}/calls"
install_python_nlp_tools "${UTILS_DIR}" >/dev/null 2>&1
if grep -q '^python3 -m venv' "${DEV}/calls"; then
	_t_fail "install_python_nlp_tools should not recreate an existing venv"
else
	_t_pass "install_python_nlp_tools skips venv creation when one already exists"
fi

# --- python3 missing: fatal, not silently skipped ------------------------

reset_state
# A bare `rm -f "${FAKE_BIN}/python3"` does not hide python3 from
# `command -v`: pyenv's shim is still reachable further down the real PATH.
# Instead point PATH at a directory that shadows python3 with nothing before
# falling through to the rest of the fakes, so `command -v python3` fails.
NO_PYTHON_BIN="${TEST_TMPDIR}/no_python_bin"
mkdir -p "${NO_PYTHON_BIN}"
for tool in git java wine cat chmod mkdir; do
	[[ -x "$(command -v "${tool}")" ]] && ln -sf "$(command -v "${tool}")" "${NO_PYTHON_BIN}/${tool}"
done
# install_python_nlp_tools calls `exit` (not `return`) on a missing python3,
# by design -- a partial install with no interpreter must abort the whole
# installer, not just this stage. Run it in a subshell so that exit only
# ends the subshell, not this test script.
if (PATH="${NO_PYTHON_BIN}" install_python_nlp_tools "${UTILS_DIR}" >/dev/null 2>&1); then
	_t_fail "install_python_nlp_tools should exit non-zero without python3"
else
	_t_pass "install_python_nlp_tools exits non-zero when python3 is missing"
fi
if grep -q "Python 3 is required" "${DEV}/errors"; then
	_t_pass "install_python_nlp_tools reports the missing-python3 error"
else
	_t_fail "install_python_nlp_tools should report the missing-python3 error"
fi

printf '\nResults: %d passed, %d failed\n' "${PASS}" "${FAIL}"
[[ "${FAIL}" -eq 0 ]]
