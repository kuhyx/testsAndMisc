#!/usr/bin/env bash
# lib/tests/hosts_guard_harness.sh — shared setup for the hosts-guard
# migration lib tests (hosts_guard_migrate.sh, hosts_guard_rollback.sh).
#
# Sourced, not executed. Builds on lib_test_core.sh and adds what both libs
# read from their entry script, migrate_hosts_guard_to_guard_lib.sh:
#
#   * the path globals (GUARDCTL, TARGETS_DIR, STATE_DIR, HOOKS_DIR,
#     PLUGIN_INSTALL_DIR, PLUGIN_SRC_DIR), all pointed into the tmpdir;
#   * the LEGACY_HOOKS / LEGACY_UNITS / INSTANCES tables, verbatim;
#   * msg/note/warn/err, `run`, instance_spec and instance_registered,
#     redefined verbatim -- they live in the entry script, not in any lib;
#   * the real log_*/has_cmd helpers, via lib/common.sh.
#
# The entry script marks most of these `readonly`, but it is never sourced
# here: this harness owns its own copies, so nothing is being overwritten.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_ROOT="$(cd "${FIXES_DIR}/../.." && pwd)"

# shellcheck source=lib_test_core.sh
. "${SCRIPT_DIR}/lib_test_core.sh"

# shellcheck source=../../../lib/common.sh
. "${REPO_ROOT}/linux_configuration/lib/common.sh"

# --- globals owned by migrate_hosts_guard_to_guard_lib.sh -------------------

# Read by the libs under test, never by this harness, so static analysis
# cannot see the use; export makes the intent explicit.
export SCRIPT_NAME="migrate_hosts_guard_to_guard_lib.sh"
export GUARDCTL="${TEST_TMPDIR}/guardctl"
export TARGETS_DIR="${TEST_TMPDIR}/guard-lib/targets"
export STATE_DIR="${TEST_TMPDIR}/guard-lib-migration"
export HOOKS_DIR="${TEST_TMPDIR}/pacman.d/hooks"
export PLUGIN_INSTALL_DIR="${TEST_TMPDIR}/guard-lib-plugins"
export PLUGIN_SRC_DIR="${TEST_TMPDIR}/plugin_src"
# The two seams added to hosts_guard_migrate.sh, plus the one in
# hosts_guard_rollback.sh, so validate_requirements and do_rollback can be
# driven without a real /etc or a real pacman lock.
export SYSTEMD_UNIT_DIR="${TEST_TMPDIR}/systemd_units"
export PACMAN_DB_LCK="${TEST_TMPDIR}/pacman_db.lck"
export HOSTS_FILE="${TEST_TMPDIR}/etc_hosts"
export DRY_RUN=0

export RED=''
export GREEN=''
export YELLOW=''
export BLUE=''
export NC=''

# Verbatim from the entry script.
readonly LEGACY_HOOKS=(
	"10-unlock-etc-hosts.hook"
	"90-relock-etc-hosts.hook"
)
readonly LEGACY_UNITS=(
	"hosts-guard.path"
	"hosts-guard.service"
	"hosts-bind-mount.service"
	"nsswitch-guard.path"
	"nsswitch-guard.service"
	"resolved-guard.path"
	"resolved-guard.service"
)
readonly INSTANCES=(hosts nsswitch resolved)

# The three tables above are read by the LIBS under test, never by this file,
# so shellcheck cannot see the use from here and flags each as unused. Bash
# cannot export an array, so the honest way to record the use is a helper the
# tests actually call -- it both silences the warning truthfully and gives the
# assertions a readable way to ask what the tables contain.
_t_table() { # <hooks|units|instances>
	case "$1" in
	hooks) printf '%s\n' "${LEGACY_HOOKS[@]}" ;;
	units) printf '%s\n' "${LEGACY_UNITS[@]}" ;;
	instances) printf '%s\n' "${INSTANCES[@]}" ;;
	*) return 1 ;;
	esac
}

msg() { printf "${GREEN}[✓]${NC} %s\n" "$*"; }
note() { printf "${BLUE}[i]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}[!]${NC} %s\n" "$*"; }
err() { printf "${RED}[✗]${NC} %s\n" "$*" >&2; }

run() {
	if ((DRY_RUN == 1)); then
		printf "${YELLOW}DRY-RUN:${NC} %s\n" "$*"
		return 0
	fi
	"$@"
}

# instance_spec, with the three real targets redirected into the tmpdir so a
# migration can be driven end to end without touching /etc.
instance_spec() { # <name> -> echoes "target|bind|plugin|also_watch"
	case "$1" in
	hosts) echo "${HOSTS_FILE}|yes||" ;;
	nsswitch) echo "${TEST_TMPDIR}/nsswitch.conf|no|nsswitch-plugin.sh|" ;;
	resolved)
		echo "${TEST_TMPDIR}/resolved.conf|no|resolved-plugin.sh|${TEST_TMPDIR}/resolved.conf.d"
		;;
	*) return 1 ;;
	esac
}

instance_registered() { [[ -f "$TARGETS_DIR/$1.conf" ]]; }

_hosts_guard_default_stubs() {
	local tool
	for tool in systemctl chattr mountpoint umount install; do
		_t_stub "$tool" 'exit 0'
	done
	# guardctl is addressed by absolute path, not through PATH, so it is
	# written directly rather than stubbed.
	cat >"${GUARDCTL}" <<'GUARDCTL_STUB'
#!/usr/bin/env bash
printf 'guardctl %s\n' "$*" >>"${LIB_TEST_DEV}/calls"
exit 0
GUARDCTL_STUB
	chmod +x "${GUARDCTL}"
}

# hosts_guard_reset — start a test group from "nothing has happened yet".
hosts_guard_reset() {
	_t_reset_calls
	DRY_RUN=0
	export DRY_RUN
	rm -rf "${TARGETS_DIR}" "${STATE_DIR}" "${HOOKS_DIR}" "${PLUGIN_INSTALL_DIR}" \
		"${PLUGIN_SRC_DIR}" "${SYSTEMD_UNIT_DIR}"
	mkdir -p "${TARGETS_DIR}" "${HOOKS_DIR}" "${PLUGIN_SRC_DIR}" "${SYSTEMD_UNIT_DIR}"
	rm -f "${PACMAN_DB_LCK}"
	printf '127.0.0.1 localhost\n' >"${HOSTS_FILE}"
	_t_full_path
	_hosts_guard_default_stubs
}

# _t_templates — create the three systemd templates validate_requirements
# insists on, so a test can reach the checks that come after them.
_t_templates() {
	local unit
	for unit in guard-file@.path guard-file@.service guard-bind-mount@.service; do
		: >"${SYSTEMD_UNIT_DIR}/${unit}"
	done
}

# _t_register NAME... — mark instances as already registered with guard-lib.
_t_register() {
	local name
	for name in "$@"; do
		: >"${TARGETS_DIR}/${name}.conf"
	done
}

hosts_guard_reset
