#!/usr/bin/env bash
# Tests for nc_php.sh — PHP, Redis and the Nextcloud install itself.
#
# The subject targets a Raspberry Pi running Debian: it edits
# /etc/php/<ver>/apache2/php.ini, drives `occ` as www-data, and installs a
# crontab. None of those paths exist on this Arch host, so the jail is given
# them with --seed-dir/--seed-file; see run_all.sh's header for the exact
# invocation. Run outside the jail this would edit a php.ini that is not
# there, which is why the guard below refuses.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

# The seeded php.ini only exists inside the jail. Its absence means we are not
# contained, and configure_php would `cp` a file that is not there.
PHP_VERSION_UNDER_TEST="8.2"
PHP_INI="/etc/php/${PHP_VERSION_UNDER_TEST}/apache2/php.ini"
if [[ ! -f $PHP_INI ]]; then
	printf 'REFUSING: %s is absent; this suite must run under the jail\n' "$PHP_INI" >&2
	exit 1
fi

_t_setup_env
trap _t_teardown EXIT

# Globals the entry script defines above its source line.
NEXTCLOUD_ADMIN_USER="admin"
NEXTCLOUD_ADMIN_PASSWORD="hunter2"
NEXTCLOUD_DATA_DIR="/var/nextcloud-data"
PI_HOSTNAME="raspberrypi"

# The logging helpers the libs inherit from the caller.
log_info() { printf '[INFO] %s\n' "$*"; }
log_success() { printf '[OK] %s\n' "$*"; }
log_warning() { printf '[WARN] %s\n' "$*"; }
log_error() { printf '[ERR] %s\n' "$*"; }

# shellcheck source=../nc_php.sh
. "$FEATURES_LIB_DIR/nc_php.sh"

[[ -n $NEXTCLOUD_DATA_DIR && -n $PI_HOSTNAME ]] ||
	{
		printf 'fixture globals are not populated\n' >&2
		exit 1
	}

# --- configure_php ----------------------------------------------------------
# php reports the seeded version; apache2 restart is recorded, not performed.
printf '#!/usr/bin/env bash\nprintf "%%s" "%s"\n' "$PHP_VERSION_UNDER_TEST" \
	>"$TEST_TMPDIR/bin/php"
chmod +x "$TEST_TMPDIR/bin/php"
_t_stub systemctl

cat >"$PHP_INI" <<'INI'
memory_limit = 128M
upload_max_filesize = 2M
post_max_size = 8M
max_execution_time = 30
max_input_time = 60
;date.timezone =
INI
mkdir -p "/etc/php/${PHP_VERSION_UNDER_TEST}/mods-available"
: >"/etc/php/${PHP_VERSION_UNDER_TEST}/mods-available/apcu.ini"

configure_php

_t_file_has "$PHP_INI" 'memory_limit = 512M' "memory_limit raised for Nextcloud"
_t_file_has "$PHP_INI" 'upload_max_filesize = 16G' "upload limit raised to 16G"
_t_file_has "$PHP_INI" 'post_max_size = 16G' "post_max_size raised to 16G"
_t_file_has "$PHP_INI" 'max_execution_time = 360' "execution time raised"
_t_file_has "$PHP_INI" 'date.timezone = Europe/Warsaw' "timezone set (the ;-prefixed default is replaced)"
_t_file_has "$PHP_INI" 'opcache.enable=1' "OPcache enabled"
_t_file_has "$PHP_INI" 'opcache.save_comments=1' "OPcache keeps comments (Nextcloud needs them)"
_t_file_has "${PHP_INI}.backup" 'memory_limit = 128M' "the original php.ini is backed up before editing"
_t_file_has "/etc/php/${PHP_VERSION_UNDER_TEST}/mods-available/apcu.ini" 'apc.enable_cli=1' "APCu enabled for the CLI"
_t_called 'restart apache2' "apache is restarted to pick up the new ini"

# --- configure_redis --------------------------------------------------------
configure_redis
_t_called 'enable redis-server' "redis is enabled at boot"
_t_called 'start redis-server' "redis is started now"

# --- install_nextcloud ------------------------------------------------------
mkdir -p /root /var/www/nextcloud
printf 'dbsecret\n' >/root/.nextcloud_db_password
printf '#!/usr/bin/env bash\nprintf "10.0.0.5 \\n"\n' >"$TEST_TMPDIR/bin/hostname"
chmod +x "$TEST_TMPDIR/bin/hostname"
_t_stub chown
# `occ` is invoked as `php occ ...`; the php stub above must now record instead
# of printing a version, or every occ call would be silently swallowed.
_t_stub php

install_nextcloud
_t_called 'occ maintenance:install' "the installer is run"
_t_called 'admin-user admin' "the configured admin user is passed through"
_t_called 'trusted_domains 1 --value=10.0.0.5' "the server IP is trusted"
_t_called "trusted_domains 2 --value=$PI_HOSTNAME" "the hostname is trusted"
_t_called "trusted_domains 3 --value=${PI_HOSTNAME}.local" "the .local name is trusted"
_t_called 'memcache.locking' "Redis is wired in for locking"
_t_called 'default_phone_region' "the phone region is set"
if [[ -d $NEXTCLOUD_DATA_DIR ]]; then
	_t_pass "the data directory is created"
else
	_t_fail "the data directory is created"
fi

# An empty admin password must be prompted for rather than silently accepted.
prompt_password() {
	printf '[prompt] %s\n' "$1"
	printf -v "$2" '%s' "prompted-secret"
}
NEXTCLOUD_ADMIN_PASSWORD=""
out="$(install_nextcloud 2>&1)"
_t_has "$out" '[prompt] Enter Nextcloud admin password' "an empty admin password is prompted for"
_t_called 'admin-pass prompted-secret' "the prompted password reaches the installer"
NEXTCLOUD_ADMIN_PASSWORD="hunter2"

# --- setup_nextcloud_cron ---------------------------------------------------
# setup_nextcloud_cron PIPES into crontab. A stub that exits without reading
# stdin makes the writer take SIGPIPE, which aborts the suite under `set -e`
# -- so this one drains stdin before recording.
cat >"$TEST_TMPDIR/bin/crontab" <<'CRONTAB'
#!/usr/bin/env bash
# The cron entry arrives on STDIN, not in argv, so it must be RECORDED
# rather than discarded -- asserting on the call log alone would pass
# no matter what line the code piped in.
cat >>"$TEST_TMPDIR/crontab.stdin"
printf 'crontab %s\n' "$*" >>"$TEST_TMPDIR/calls.log"
# `-l` must emit at least one line: the real code pipes it through
# `grep -v nextcloud/cron.php`, and grep exits 1 on no match, which
# aborts the caller under pipefail. An existing unrelated entry is also
# the realistic case -- it proves the rewrite PRESERVES other cron jobs.
if [[ $* == *-l* ]]; then
    printf '0 4 * * * /usr/local/bin/some-unrelated-job\n'
fi
exit 0
CRONTAB
chmod +x "$TEST_TMPDIR/bin/crontab"
setup_nextcloud_cron
_t_called 'crontab -u www-data' "the www-data crontab is written"
_t_called 'occ background:cron' "Nextcloud is switched to cron mode"
_t_file_has "$TEST_TMPDIR/crontab.stdin" 'php -f /var/www/nextcloud/cron.php' \
	"the Nextcloud cron entry is piped into crontab"
_t_file_has "$TEST_TMPDIR/crontab.stdin" 'some-unrelated-job' \
	"an unrelated existing cron entry is preserved"

# --- phase_nextcloud --------------------------------------------------------
# The orchestrator. Its siblings live in other libs, so the fixture supplies
# them; what is asserted here is the ORDER, which is load-bearing: php and
# redis must both be configured before the installer runs, and the cron job
# must be added before the final verification.
#
# Run in a SUBSHELL. These definitions shadow the real functions, and letting
# them leak into the enclosing shell silently replaced the subject's own
# functions for every later assertion -- coverage fell from 83.53% to 57.65%
# and the tests still "passed", because they were exercising the stubs.
phase_order_result="$(
	{
		check_root() { printf 'root '; }
		install_nextcloud_dependencies() { printf 'deps '; }
		# Its stdout is captured by `db_password=$(configure_mariadb)`, so a
		# marker printed here would be swallowed. Record to stderr, which the
		# command substitution does not consume, and emit the password on
		# stdout as the real function does.
		configure_mariadb() {
			printf 'mariadb ' >&2
			printf 'dbpass'
		}
		download_nextcloud() { printf 'download '; }
		configure_apache() { printf 'apache '; }
		configure_php() { printf 'php '; }
		configure_redis() { printf 'redis '; }
		install_nextcloud() { printf 'install '; }
		setup_nextcloud_cron() { printf 'cron '; }
		verify_nextcloud() { printf 'verify '; }
		log_info() { :; }
		log_success() { :; }
		phase_nextcloud
	} 2>&1
)"
_t_eq "root deps mariadb download apache php redis install cron verify " \
	"$phase_order_result" "the install phases run in dependency order"

# --- verify_nextcloud -------------------------------------------------------
printf '#!/usr/bin/env bash\nprintf "200"\n' >"$TEST_TMPDIR/bin/curl"
chmod +x "$TEST_TMPDIR/bin/curl"
out="$(verify_nextcloud 2>&1)"
_t_has "$out" 'Nextcloud is responding!' "a 200 from status.php reads as healthy"
_t_has "$out" 'Access Nextcloud at: http://10.0.0.5' "the access URL is reported"

# A non-200 must warn, not claim success.
printf '#!/usr/bin/env bash\nprintf "503"\n' >"$TEST_TMPDIR/bin/curl"
chmod +x "$TEST_TMPDIR/bin/curl"
out="$(verify_nextcloud 2>&1)"
_t_has "$out" 'may not be fully ready' "a non-200 warns instead of claiming success"

_t_report "test_nc_php.sh"
