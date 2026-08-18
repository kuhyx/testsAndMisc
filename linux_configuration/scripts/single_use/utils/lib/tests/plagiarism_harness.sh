#!/usr/bin/env bash
# lib/tests/plagiarism_harness.sh — fake python3/pip/git/java/wine behind the
# install_plagiarism_tools.sh split.
#
# Sourced, not executed. Every external tool the installer calls is a shim on
# PATH that records its invocation into $DEV and does the minimum real
# filesystem work the calling code depends on (e.g. `python3 -m venv` must
# leave a `bin/activate` a real `source` can run). INSTALL_DIR, VENV_DIR and
# HOME all point into a throwaway tmpdir so nothing touches the real machine.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UTILS_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PASS=0
FAIL=0

_t_pass() {
	PASS=$((PASS + 1))
	printf '  OK: %s\n' "$1"
}

_t_fail() {
	FAIL=$((FAIL + 1))
	printf '  FAIL: %s\n' "$1"
}

_t_eq() {
	local want="$1" got="$2" what="$3"
	if [[ "$got" == "$want" ]]; then
		_t_pass "$what"
	else
		_t_fail "$what (want '${want}', got '${got}')"
	fi
}

TEST_TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TEST_TMPDIR}"' EXIT

readonly DEV="${TEST_TMPDIR}/device"
readonly FAKE_BIN="${TEST_TMPDIR}/fake_bin"
mkdir -p "${DEV}" "${FAKE_BIN}"

# --- fake external tools ----------------------------------------------------

cat >"${FAKE_BIN}/python3" <<'PYSHIM'
#!/usr/bin/env bash
set -euo pipefail
DEV="${PLAGIARISM_TEST_DEV}"
printf '%s\n' "python3 $*" >>"${DEV}/calls"
if [[ "$1" == "-m" && "$2" == "venv" ]]; then
	venv_dir="$3"
	mkdir -p "${venv_dir}/bin"
	cat >"${venv_dir}/bin/activate" <<'ACTEOF'
deactivate() { :; }
pip() { printf '%s\n' "pip $*" >>"${PLAGIARISM_TEST_DEV}/calls"; return 0; }
ACTEOF
	exit 0
fi
if [[ "$1" == "-m" && "$2" == "spacy" ]]; then
	[[ -f "${DEV}/fail_spacy" ]] && exit 1
	exit 0
fi
# python3 <script.py> [args...] — record which script ran and succeed.
printf '%s\n' "ran:$1" >>"${DEV}/scripts_run"
[[ -f "${DEV}/fail_$(basename "$1" .py)" ]] && exit 1
exit 0
PYSHIM
chmod +x "${FAKE_BIN}/python3"

cat >"${FAKE_BIN}/git" <<'GITSHIM'
#!/usr/bin/env bash
set -euo pipefail
DEV="${PLAGIARISM_TEST_DEV}"
printf '%s\n' "git $*" >>"${DEV}/calls"
if [[ "$1" == "clone" ]]; then
	[[ -f "${DEV}/fail_clone" ]] && exit 1
	dest="${*: -1}"
	mkdir -p "${dest}"
	exit 0
fi
exit 0
GITSHIM
chmod +x "${FAKE_BIN}/git"

cat >"${FAKE_BIN}/java" <<'JAVASHIM'
#!/usr/bin/env bash
exit 0
JAVASHIM
chmod +x "${FAKE_BIN}/java"

cat >"${FAKE_BIN}/wine" <<'WINESHIM'
#!/usr/bin/env bash
exit 0
WINESHIM
chmod +x "${FAKE_BIN}/wine"

export PLAGIARISM_TEST_DEV="${DEV}"
export PATH="${FAKE_BIN}:${PATH}"

# --- subject under test -----------------------------------------------------

HOME="${TEST_TMPDIR}/home"
INSTALL_DIR="${TEST_TMPDIR}/install"
VENV_DIR="${TEST_TMPDIR}/venv"
mkdir -p "${HOME}" "${INSTALL_DIR}"

success() { :; }
warn() { printf '%s\n' "$*" >>"${DEV}/warnings"; }
error() { printf '%s\n' "$*" >>"${DEV}/errors"; }

# shellcheck source=../plagiarism_python.sh
. "${UTILS_DIR}/lib/plagiarism_python.sh"
# shellcheck source=../plagiarism_sherlock.sh
. "${UTILS_DIR}/lib/plagiarism_sherlock.sh"
# shellcheck source=../plagiarism_optional.sh
. "${UTILS_DIR}/lib/plagiarism_optional.sh"

# reset_state — wipe INSTALL_DIR/VENV_DIR/DEV records between test groups so
# each group starts from "nothing installed yet".
reset_state() {
	rm -rf "${INSTALL_DIR}" "${VENV_DIR}" "${DEV:?}/calls" "${DEV}/scripts_run" \
		"${DEV}/warnings" "${DEV}/errors" 2>/dev/null || true
	mkdir -p "${INSTALL_DIR}"
	: >"${DEV}/calls"
	: >"${DEV}/scripts_run"
	: >"${DEV}/warnings"
	: >"${DEV}/errors"
}
reset_state
