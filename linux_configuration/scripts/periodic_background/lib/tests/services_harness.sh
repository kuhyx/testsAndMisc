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
# The paths the checks probe (/usr/bin/pacman, /etc/hosts, ...) are prefixed
# with $SYSROOT in every lib, so this harness points SERVICES_ROOT at a fixture
# tree under the tmpdir. A test declares "pretend /etc/hosts has 200 lines" by
# actually creating $SYSROOT/etc/hosts with 200 lines -- the checks then run
# their real logic against a filesystem this process owns.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=services_assert.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/services_assert.sh"

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
	printf '%s %s\n' '----i---------e----' "$target"
else
	printf '%s %s\n' '------------------e----' "$target"
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

# shellcheck source=services_path.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/services_path.sh"

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
export PATH="${FAKE_BIN}:${REAL_BIN}"

# --- fixture filesystem -----------------------------------------------------

# Every absolute path the check libs probe is prefixed with $SYSROOT, which they
# read from SERVICES_ROOT. Pointing it at the tmpdir is what makes the
# file-existence branches reachable: the checks run their real logic, against a
# tree this process created. SERVICES_ROOT is deliberately un-defaulted in the
# libs, so a test file that forgets this line dies instead of touching /etc.
readonly SYSROOT_DIR="${TEST_TMPDIR}/sysroot"
export SERVICES_ROOT="${SYSROOT_DIR}"

mkdir -p \
	"${SYSROOT_DIR}/usr/bin" \
	"${SYSROOT_DIR}/usr/local/bin" \
	"${SYSROOT_DIR}/etc/systemd/system" \
	"${SYSROOT_DIR}/etc/pacman.d/hooks" \
	"${SYSROOT_DIR}/var/lib"

# Create a file under the fixture root, making its parent as needed.
# `sysfile etc/hosts 200` writes 200 filler lines, which is how the
# StevenBlack-list line-count check is driven.
sysfile() { # <relative-path> [line-count]
	local target="${SYSROOT_DIR}/$1"
	mkdir -p "$(dirname "$target")"
	if [[ -n "${2:-}" ]]; then
		seq 1 "$2" >"$target"
	else
		: >"$target"
	fi
}

# Remove a file or directory from the fixture root.
sysrm() { # <relative-path>...
	local rel
	for rel in "$@"; do
		rm -rf "${SYSROOT_DIR:?}/${rel}"
	done
}

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
	rm -rf "${SYSROOT_DIR:?}"
	mkdir -p \
		"${SYSROOT_DIR}/usr/bin" \
		"${SYSROOT_DIR}/usr/local/bin" \
		"${SYSROOT_DIR}/etc/systemd/system" \
		"${SYSROOT_DIR}/etc/pacman.d/hooks" \
		"${SYSROOT_DIR}/var/lib"
	: >"${DEV}/calls"
	DRY_RUN=0
	STATUS_ONLY=0
	ISSUES_FOUND=0
	FIXES_APPLIED=0
	SERVICE_STATUS=()
	MISSING_SCRIPTS=()
	# Staged fake executables are part of the machine a test describes, so they
	# reset too. Without this a `present_command discord` leaks into every later
	# group, which makes a forgetful test pass for the wrong reason.
	rm -f "${FAKE_BIN:?}"/beeper "${FAKE_BIN}"/signal-desktop "${FAKE_BIN}"/discord \
		"${FAKE_BIN}"/thorium-browser "${FAKE_BIN}"/chromium \
		"${FAKE_BIN}"/google-chrome "${FAKE_BIN}"/brave-browser \
		"${FAKE_BIN}"/VBoxManage
}
reset_state
