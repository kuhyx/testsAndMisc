#!/usr/bin/env bash
# lib/tests/services_harness.sh — shared fixture for the check_and_enable_services
# split.
#
# Sourced, not executed. Every command the checks reach for — systemctl,
# guardctl, lsattr, chattr, logger, sudo, find, wc — is a PATH shim recording
# its invocation into $DEV/calls, so a test asserts on what the code TRIED to
# do rather than on the state of this machine. Nothing here touches a real unit,
# a real /etc file, or a real installer.
#
# The paths the checks probe (/usr/bin/pacman, /etc/hosts, ...) are absolute and
# cannot be redirected, so the shims answer questions about them from files
# under $DEV instead: a test declares "pretend /etc/hosts has 200 lines" by
# writing $DEV/etc_hosts_lines rather than by creating the file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

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
	local want="$1"
	local got="$2"
	local what="$3"
	if [[ "$got" == "$want" ]]; then
		_t_pass "$what"
	else
		_t_fail "$what (want '${want}', got '${got}')"
	fi
}

# Assert $DEV/calls contains a line matching a regex.
_t_called() {
	local pattern="$1"
	local what="$2"
	if grep -qE "$pattern" "${DEV}/calls" 2>/dev/null; then
		_t_pass "$what"
	else
		_t_fail "$what (no call matching /${pattern}/)"
	fi
}

_t_not_called() {
	local pattern="$1"
	local what="$2"
	if grep -qE "$pattern" "${DEV}/calls" 2>/dev/null; then
		_t_fail "$what (unexpected call matching /${pattern}/)"
	else
		_t_pass "$what"
	fi
}

_t_summary() {
	printf '\n%s: %d passed, %d failed\n' "$(basename "$0")" "$PASS" "$FAIL"
	[[ $FAIL -eq 0 ]]
}

TEST_TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TEST_TMPDIR}"' EXIT

readonly DEV="${TEST_TMPDIR}/device"
readonly FAKE_BIN="${TEST_TMPDIR}/fake_bin"
mkdir -p "${DEV}" "${FAKE_BIN}"

# --- fake external tools ----------------------------------------------------

# systemctl: `is-enabled`/`is-active <unit>` succeed only when $DEV/enabled or
# $DEV/active lists the unit. Every other subcommand (restart, ...) just
# records. `--user --machine=...` is the user_systemctl shape and is answered
# from the same two files, prefixed "user:".
cat >"${FAKE_BIN}/systemctl" <<'SYSTEMCTLSHIM'
#!/usr/bin/env bash
set -euo pipefail
DEV="${SERVICES_TEST_DEV}"
printf '%s\n' "systemctl $*" >>"${DEV}/calls"
prefix=""
args=()
for a in "$@"; do
	case "$a" in
	--user) prefix="user:" ;;
	--machine=*) ;;
	*) args+=("$a") ;;
	esac
done
verb="${args[0]:-}"
unit="${args[1]:-}"
case "$verb" in
is-enabled) grep -qxF "${prefix}${unit}" "${DEV}/enabled" 2>/dev/null ;;
is-active) grep -qxF "${prefix}${unit}" "${DEV}/active" 2>/dev/null ;;
*) exit 0 ;;
esac
SYSTEMCTLSHIM
chmod +x "${FAKE_BIN}/systemctl"

# guardctl file-guard status <name>: prints the two lines
# guard_lib_instance_healthy greps for, but only for instances listed in
# $DEV/guard_healthy. An instance in $DEV/guard_degraded prints a status whose
# path unit is inactive; anything else exits 1 (unregistered).
cat >"${FAKE_BIN}/guardctl" <<'GUARDCTLSHIM'
#!/usr/bin/env bash
set -euo pipefail
DEV="${SERVICES_TEST_DEV}"
printf '%s\n' "guardctl $*" >>"${DEV}/calls"
name="${3:-}"
if grep -qxF "$name" "${DEV}/guard_healthy" 2>/dev/null; then
	printf 'path unit: active\ntarget attrs: ----i---------e---- /etc/%s\n' "$name"
	exit 0
fi
if grep -qxF "$name" "${DEV}/guard_degraded" 2>/dev/null; then
	printf 'path unit: inactive\ntarget attrs: ------------------ /etc/%s\n' "$name"
	exit 0
fi
exit 1
GUARDCTLSHIM
chmod +x "${FAKE_BIN}/guardctl"

# lsattr: prints an attribute string for paths listed in $DEV/immutable,
# otherwise the all-dashes "no attributes" form.
cat >"${FAKE_BIN}/lsattr" <<'LSATTRSHIM'
#!/usr/bin/env bash
set -euo pipefail
DEV="${SERVICES_TEST_DEV}"
target="${1:-}"
if grep -qxF "$target" "${DEV}/immutable" 2>/dev/null; then
	printf '----i---------e---- %s\n' "$target"
else
	printf -- '------------------e---- %s\n' "$target"
fi
exit 0
LSATTRSHIM
chmod +x "${FAKE_BIN}/lsattr"

for tool in chattr logger sudo systemd-resolved; do
	cat >"${FAKE_BIN}/${tool}" <<SIMPLESHIM
#!/usr/bin/env bash
printf '%s\n' "${tool} \$*" >>"\${SERVICES_TEST_DEV}/calls"
exit 0
SIMPLESHIM
	chmod +x "${FAKE_BIN}/${tool}"
done

# `command -v <browser>` decides whether the browser/VBox checks apply. bash's
# builtin `command` cannot be shimmed on PATH, so the tests instead create the
# fake executables themselves under $FAKE_BIN via present_command below.
present_command() { # <name>...
	local name
	for name in "$@"; do
		printf '#!/usr/bin/env bash\nexit 0\n' >"${FAKE_BIN}/${name}"
		chmod +x "${FAKE_BIN}/${name}"
	done
}

absent_command() { # <name>...
	local name
	for name in "$@"; do
		rm -f "${FAKE_BIN}/${name}"
	done
}

export SERVICES_TEST_DEV="${DEV}"
export PATH="${FAKE_BIN}:${PATH}"

# --- globals the libs read --------------------------------------------------

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
BLUE=$'\033[0;34m'
CYAN=$'\033[0;36m'
NC=$'\033[0m'

DRY_RUN=0
STATUS_ONLY=0
ISSUES_FOUND=0
FIXES_APPLIED=0
declare -A SERVICE_STATUS=()
declare -a MISSING_SCRIPTS=()

# Installer paths point into the tmpdir so a test controls whether the repair
# path finds its script (present) or reports it missing (absent).
#
# Exported because the check libs that read them are sourced by the individual
# test files rather than by this harness, so standalone shellcheck sees only
# the write here and reports SC2034. They genuinely cross a process boundary
# too (the require_root probe runs as a child), so export is the accurate
# declaration rather than a way to quiet the warning.
export PACMAN_WRAPPER_INSTALL="${TEST_TMPDIR}/install_pacman_wrapper.sh"
export MAKEPKG_WRAPPER_INSTALL="${TEST_TMPDIR}/install_makepkg_wrapper.sh"
export PACMAN_WRAPPER_MANIFEST="${TEST_TMPDIR}/pacman-source.sha256"
export MAKEPKG_WRAPPER_MANIFEST="${TEST_TMPDIR}/makepkg-source.sha256"
export MIDNIGHT_SHUTDOWN_SCRIPT="${TEST_TMPDIR}/setup_midnight_shutdown.sh"
export STARTUP_MONITOR_SCRIPT="${TEST_TMPDIR}/setup_pc_startup_monitor.sh"
export PERIODIC_SYSTEM_SCRIPT="${TEST_TMPDIR}/setup_periodic_system.sh"
export HOSTS_INSTALL_SCRIPT="${TEST_TMPDIR}/hosts_install.sh"
export GUARD_LIB_MIGRATE_SCRIPT="${TEST_TMPDIR}/migrate_hosts_guard.sh"
export COMPULSIVE_BLOCK_SCRIPT="${TEST_TMPDIR}/block_compulsive_opening.sh"
export LEECHBLOCK_SCRIPT="${TEST_TMPDIR}/install_leechblock.sh"
export REMOVE_GUEST_MODE_SCRIPT="${TEST_TMPDIR}/remove_guest_mode.sh"
export VBOX_HOSTS_SCRIPT="${TEST_TMPDIR}/enforce_vbox_hosts.sh"
export WORKOUT_LOCKER_INSTALL_SCRIPT="${TEST_TMPDIR}/install_systemd.sh"
export WORKOUT_LOCKER_SCRIPT="${TEST_TMPDIR}/screen_lock.py"

# Create an installer stub that records being run, so "did the repair path fire"
# is observable without any real installation happening.
make_installer() { # <path>
	printf '#!/usr/bin/env bash\nprintf "%%s\\n" "ran %s $*" >>"%s/calls"\nexit 0\n' \
		"$(basename "$1")" "${DEV}" >"$1"
	chmod +x "$1"
}

# shellcheck source=../services_common.sh
. "${LIB_DIR}/services_common.sh"

# reset_state — return every mutable global and every $DEV fact to "nothing has
# happened yet", so each test group starts from a known machine.
reset_state() {
	rm -f "${DEV:?}"/* 2>/dev/null || true
	: >"${DEV}/calls"
	DRY_RUN=0
	STATUS_ONLY=0
	ISSUES_FOUND=0
	FIXES_APPLIED=0
	SERVICE_STATUS=()
	MISSING_SCRIPTS=()
}
reset_state
