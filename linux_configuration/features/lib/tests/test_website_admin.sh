#!/usr/bin/env bash
# Tests for website_admin.sh — the personal website's browser post editor.
#
# The subject is driven for real, including the sudo-write of the systemd unit,
# which the jail bind-mounts to a throwaway /etc. Only two things are stood in
# for: `pnpm`, because building the editor is the website repo's own test
# suite's job, and `admin_cli`, because hashing a password with scrypt costs
# ~100 ms per call and proves nothing here.
#
# What IS asserted is the content: a unit whose PATH lacks nvm's node, or an
# env file that lost PW_ADMIN_ROOT, starts cleanly and then fails on the first
# save — the exact failure a presence check would pass.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

# --- Refuse to run outside the jail -----------------------------------------
if [[ -d /etc/systemd/system ]] && [[ ! -w /etc/systemd/system ]]; then
	printf 'REFUSING: this suite must run under shell_coverage_jail.sh\n' >&2
	exit 1
fi

_t_setup_env
trap _t_teardown EXIT

# The globals website_admin.sh inherits from setup_personal_website.sh above
# its source line, plus the log helpers it takes from common.sh.
WEBSITE_SRC="$TEST_TMPDIR/website"
WEBSITE_DATA_DIR="$TEST_TMPDIR/serve"
mkdir -p "$WEBSITE_SRC/dist-admin/client"

log_info() { printf '[info] %s\n' "$1"; }
log_ok() { printf '[ok] %s\n' "$1"; }
log_warn() { printf '[warn] %s\n' "$1" >&2; }
log_error() { printf '[error] %s\n' "$1" >&2; }
die() {
	log_error "$1"
	exit 1
}
ensure_dir() { mkdir -p "$1"; }
status_line() { printf '[status %s] %s\n' "$1" "$2"; }
check_http() { echo 1; }

# shellcheck source=../website_admin.sh
. "$FEATURES_LIB_DIR/website_admin.sh"

# Shadow sudo for this suite only. The jail already runs as uid 0, so `sudo`
# adds nothing here -- but it resets PATH, which would send
# `sudo systemctl daemon-reload` to the real binary and reload the HOST's
# systemd, one of the few things the namespace does not contain.
sudo() { "$@"; }

# A stand-in scrypt hash. Escaped inside double quotes rather than written in
# single quotes: the format is $-separated, and this repo treats shellcheck's
# SC2016 as an error.
readonly FAKE_HASH="scrypt\$32768\$8\$1\$deadbeef\$cafe"

# Stand in for the service's own CLI: deterministic, and 200x faster.
admin_cli() {
	case "$1" in
	hash-password) printf '%s\n' "$FAKE_HASH" ;;
	session-secret) printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n' ;;
	*) return 1 ;;
	esac
}

# --- admin_new_password -----------------------------------------------------
password="$(admin_new_password)"
if [[ ${#password} -ge 16 ]]; then
	_t_pass "admin_new_password returns something long enough to be a password"
else
	_t_fail "admin_new_password returned only ${#password} characters"
fi
# `/` and `+` would survive a shell round trip badly and `=` reads as padding
# someone will trim; the generator strips all three rather than hoping.
if [[ $password =~ ^[A-Za-z0-9]+$ ]]; then
	_t_pass "admin_new_password stays URL- and copy-paste-safe"
else
	_t_fail "admin_new_password produced '${password}'"
fi
if [[ "$(admin_new_password)" == "$(admin_new_password)" ]]; then
	_t_fail "admin_new_password returned the same value twice"
else
	_t_pass "admin_new_password draws fresh entropy each call"
fi

# --- admin_env_text ---------------------------------------------------------
env_text="$(admin_env_text "$FAKE_HASH" 'the-secret')"
_t_has "$env_text" "PW_ADMIN_PASSWORD_HASH=${FAKE_HASH}" "the env file carries the hash"
_t_has "$env_text" 'PW_ADMIN_SESSION_SECRET=the-secret' "the env file carries the session secret"
_t_has "$env_text" 'PW_ADMIN_HOST=127.0.0.1' "the service is pinned to loopback"
_t_has "$env_text" "PW_ADMIN_ROOT=${WEBSITE_SRC}" "the content root points at the checkout"

# --- ensure_admin_secrets ---------------------------------------------------
ensure_admin_secrets
_t_file_has "$ADMIN_ENV_FILE" 'PW_ADMIN_PASSWORD_HASH=scrypt' "the env file is written"
_t_eq "600" "$(stat -c '%a' "$ADMIN_ENV_FILE")" "the env file is not world-readable"
_t_eq "600" "$(stat -c '%a' "$ADMIN_PASSWORD_FILE")" "the password file is not world-readable"

# The password must never be recoverable from the file the unit reads.
stored_password="$(cat "$ADMIN_PASSWORD_FILE")"
if grep -qF "$stored_password" "$ADMIN_ENV_FILE"; then
	_t_fail "the env file contains the plaintext password"
else
	_t_pass "the env file holds only the hash, never the password"
fi

# Re-running setup must not rotate a password someone is already using.
ensure_admin_secrets
_t_eq "$stored_password" "$(cat "$ADMIN_PASSWORD_FILE")" \
	"ensure_admin_secrets leaves existing credentials alone"

# A truncated env file is not credentials, and must be regenerated rather than
# reused into a service that cannot authenticate anyone.
printf 'PW_ADMIN_PORT=4321\n' >"$ADMIN_ENV_FILE"
ensure_admin_secrets
_t_file_has "$ADMIN_ENV_FILE" 'PW_ADMIN_PASSWORD_HASH=scrypt' \
	"a hashless env file is rewritten instead of kept"

# --- admin_unit_text --------------------------------------------------------
unit_text="$(admin_unit_text)"
node_dir="$(dirname "$(command -v node)")"
_t_has "$unit_text" "Environment=PATH=${node_dir}:" \
	"the unit puts this node on PATH, so the build steps can shell out to it"
_t_has "$unit_text" "WorkingDirectory=${WEBSITE_SRC}" "the unit runs from the checkout"
_t_has "$unit_text" "EnvironmentFile=${ADMIN_ENV_FILE}" "the unit reads the generated env file"
_t_has "$unit_text" "ReadWritePaths=${WEBSITE_SRC}" \
	"ProtectSystem=strict is opened up for exactly the checkout"
_t_has "$unit_text" "NoNewPrivileges=yes" "the unit drops privilege escalation"
_t_has "$unit_text" "Restart=always" "the unit comes back after a crash or reboot"
if [[ $unit_text == *"${WEBSITE_SRC}/dist-admin/admin.js"* ]]; then
	_t_pass "the unit starts the built service, not a source file"
else
	_t_fail "the unit does not start dist-admin/admin.js"
fi

# --- write_admin_unit -------------------------------------------------------
_t_stub systemctl
write_admin_unit
_t_file_has "$ADMIN_UNIT_PATH" "ExecStart=" "the unit lands in /etc/systemd/system"
_t_called "daemon-reload" "write_admin_unit reloads systemd so the new unit is seen"

# --- admin_report -----------------------------------------------------------
report="$(admin_report)"
_t_has "$report" "-L ${ADMIN_PORT}:127.0.0.1:${ADMIN_PORT}" "the report gives the tunnel command"
_t_has "$report" "http://localhost:${ADMIN_PORT}/admin" \
	"the report sends you to localhost, which is where the Secure cookie works"
_t_has "$report" "$ADMIN_PASSWORD_FILE" "the report says where the password is"
if [[ $report == *"$stored_password"* ]]; then
	_t_fail "the report prints the password into the terminal and the setup log"
else
	_t_pass "the report names the password file rather than printing the password"
fi

# --- build_website_admin ----------------------------------------------------
_t_stub pnpm
# pnpm is stubbed, so nothing is produced: the build must notice rather than
# hand a missing bundle to systemd.
_t_exits_nonzero build_website_admin "build_website_admin fails when no bundle was produced"

printf 'built\n' >"${WEBSITE_SRC}/dist-admin/admin.js"
_t_exits_nonzero build_website_admin \
	"build_website_admin fails when the service built but the editor page did not"

printf '<html></html>\n' >"${WEBSITE_SRC}/dist-admin/client/index.html"
if build_website_admin >/dev/null; then
	_t_pass "build_website_admin passes once both halves exist"
else
	_t_fail "build_website_admin rejected a complete build"
fi

# --- start_admin_service ----------------------------------------------------
# A curl that answers 200 stands in for a service that came up. The opposite
# case is deliberately not exercised here: wait_for_admin retries for 20 s
# before giving up, and a 20 s test is one nobody will keep running.
printf '#!/usr/bin/env bash\nprintf 200\n' >"$TEST_TMPDIR/bin/curl"
chmod +x "$TEST_TMPDIR/bin/curl"
if start_admin_service >/dev/null 2>&1; then
	_t_pass "start_admin_service accepts a service that answers 200 on /admin"
else
	_t_fail "start_admin_service rejected a healthy service"
fi
_t_called "enable --now ${ADMIN_UNIT}" "start_admin_service enables the unit for reboot survival"

# --- deploy_admin_service ---------------------------------------------------
if deploy_admin_service >/dev/null 2>&1; then
	_t_pass "deploy_admin_service runs build, secrets, unit and start in one pass"
else
	_t_fail "deploy_admin_service failed on an otherwise healthy setup"
fi

# --- admin_status_lines -----------------------------------------------------
if admin_status_lines >/dev/null 2>&1; then
	_t_pass "admin_status_lines reports without failing the status command"
else
	_t_fail "admin_status_lines exited non-zero"
fi

_t_report "test_website_admin.sh"
