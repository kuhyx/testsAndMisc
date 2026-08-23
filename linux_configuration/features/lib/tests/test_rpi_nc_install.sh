#!/usr/bin/env bash
# Tests for rpi_nc_install.sh — the Raspberry Pi Nextcloud install phase.
#
# One 200-line function that apt-installs 24 packages, seeds a MariaDB
# database, `rm -rf`s /var/www/nextcloud, rewrites Apache and PHP config and
# installs a www-data crontab. It is executed for real inside the namespace
# jail, where every one of those targets is a throwaway bind mount.
#
# The destructive step is the reason this suite is worth having: a bug in the
# `rm -rf /var/www/nextcloud` line is invisible to any check that does not
# actually run it.
#
# KNOWN: kcov MIS-MEASURES this subject. It reports 10/88 = 11.36%, recording
# lines 13-54 and nothing after, even though the code past line 54 provably
# runs -- /root/.nextcloud_db_password and
# /etc/apache2/sites-available/nextcloud.conf both exist after a run, and the
# 29 assertions below pass. The three obvious explanations were each tested
# against a minimal reproduction and DISPROVEN: kcov traces correctly past a
# heredoc, into a `$(...)` command substitution, and past a heredoc-fed stub
# that reads stdin via `$(cat)`. The cause is still unknown, so this file
# stays on the coverage allowlist and the suite is kept for the assertions
# rather than the percentage. Do not "fix" the number by weakening a test.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./features_harness.sh
. "$SCRIPT_DIR/features_harness.sh"

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

log_info() { printf '[INFO] %s\n' "$*"; }
log_success() { printf '[OK] %s\n' "$*"; }
log_warning() { printf '[WARN] %s\n' "$*"; }
log_error() { printf '[ERR] %s\n' "$*"; }

# Helpers this lib inherits from its siblings in the entry script.
check_root() { :; }
wait_for_apt_lock() { :; }
generate_password() { printf 'generated-%s-chars' "$1"; }
auto_generate_nextcloud_password() { :; }
save_config() { printf 'save_config called\n'; }

# shellcheck source=../rpi_nc_install.sh
. "$FEATURES_LIB_DIR/rpi_nc_install.sh"

[[ -n $NEXTCLOUD_DATA_DIR && -n $PI_HOSTNAME ]] ||
	{
		printf 'fixture globals are not populated\n' >&2
		exit 1
	}

# --- Stubs ------------------------------------------------------------------
for tool in apt-get a2enmod a2dissite a2ensite systemctl wget unzip chown \
	php mysql crontab hostname; do
	_t_stub "$tool"
done

# php is called two ways: `php -v` must yield a parseable version banner, and
# `php occ ...` must record. One stub serves both.
cat >"$TEST_TMPDIR/bin/php" <<PHPSTUB
#!/usr/bin/env bash
printf 'php %s\n' "\$*" >>"$TEST_TMPDIR/calls.log"
if [[ \$* == "-v" ]]; then
    printf 'PHP %s.10 (cli) (built: Jan  1 2026)\n' "$PHP_VERSION_UNDER_TEST"
    exit 0
fi
if [[ \$* == *status* ]]; then
    printf '  - installed: true\n'
    exit 0
fi
exit 0
PHPSTUB
chmod +x "$TEST_TMPDIR/bin/php"

# mysql reads the CREATE DATABASE heredoc from stdin; drain it or the writer
# takes SIGPIPE and the suite dies under set -e.
cat >"$TEST_TMPDIR/bin/mysql" <<MYSQLSTUB
#!/usr/bin/env bash
sql="\$(cat)"
printf 'mysql %s\n' "\$*" >>"$TEST_TMPDIR/calls.log"
printf '%s\n' "\$sql" >>"$TEST_TMPDIR/mysql.sql"
exit 0
MYSQLSTUB
chmod +x "$TEST_TMPDIR/bin/mysql"

cat >"$TEST_TMPDIR/bin/crontab" <<CRONSTUB
#!/usr/bin/env bash
cat >/dev/null
printf 'crontab %s\n' "\$*" >>"$TEST_TMPDIR/calls.log"
exit 0
CRONSTUB
chmod +x "$TEST_TMPDIR/bin/crontab"

printf '#!/usr/bin/env bash\nprintf "10.0.0.7 \\n"\n' >"$TEST_TMPDIR/bin/hostname"
chmod +x "$TEST_TMPDIR/bin/hostname"

# unzip must actually MATERIALISE the tree. The phase does `rm -rf
# /var/www/nextcloud` and then unzips over it, so a stub that only records
# leaves the later `cd /var/www/nextcloud` with nothing to enter -- the
# function returns 1 and `set -e` aborts the suite from inside a command
# substitution with no stderr at all, which is indistinguishable from a
# coverage-tool failure.
cat >"$TEST_TMPDIR/bin/unzip" <<UNZIPSTUB
#!/usr/bin/env bash
printf 'unzip %s\n' "\$*" >>"$TEST_TMPDIR/calls.log"
mkdir -p /var/www/nextcloud
printf 'extracted\n' >/var/www/nextcloud/occ
exit 0
UNZIPSTUB
chmod +x "$TEST_TMPDIR/bin/unzip"

# The environment the phase expects to find.
mkdir -p /etc/apache2/sites-available /var/www /root /tmp
cat >"$PHP_INI" <<'INI'
memory_limit = 128M
upload_max_filesize = 2M
post_max_size = 8M
max_execution_time = 30
max_input_time = 60
;date.timezone =
INI

# A stale install that the phase must clear. If `rm -rf /var/www/nextcloud`
# ever stops working, this file survives and the assertion below catches it.
mkdir -p /var/www/nextcloud
printf 'stale\n' >/var/www/nextcloud/STALE_MARKER
# unzip is stubbed, so the extracted tree is staged by hand.
: >/tmp/nextcloud.zip

phase_output="$(phase_install_nextcloud 2>&1)"

# --- Packages and database --------------------------------------------------
_t_called 'apt-get install' "the dependency set is installed"
_t_called 'php-imagick' "the imagick module is among the packages"
_t_file_has "$TEST_TMPDIR/mysql.sql" 'CREATE DATABASE IF NOT EXISTS nextcloud' "the database is created idempotently"
_t_file_has "$TEST_TMPDIR/mysql.sql" "GRANT ALL PRIVILEGES ON nextcloud" "the nextcloud user is granted its own schema"
_t_file_has /root/.nextcloud_db_password 'generated-32-chars' "the generated db password is persisted"
_t_eq "600" "$(stat -c '%a' /root/.nextcloud_db_password)" "the db password file is mode 600"

# --- The destructive step ---------------------------------------------------
if [[ -e /var/www/nextcloud/STALE_MARKER ]]; then
	_t_fail "a stale /var/www/nextcloud is cleared before extracting"
else
	_t_pass "a stale /var/www/nextcloud is cleared before extracting"
fi
_t_called 'unzip' "the release archive is extracted"
_t_called 'chown' "the tree is handed to www-data"

# --- Apache -----------------------------------------------------------------
_t_file_has /etc/apache2/sites-available/nextcloud.conf 'DocumentRoot /var/www/nextcloud' "the vhost points at the install"
_t_file_has /etc/apache2/sites-available/nextcloud.conf 'AllowOverride All' "the vhost allows Nextcloud's .htaccess"
_t_file_has /etc/apache2/sites-available/nextcloud.conf 'Dav off' "WebDAV is disabled for Apache (Nextcloud serves its own)"
_t_called 'a2enmod rewrite' "mod_rewrite is enabled"
_t_called 'a2dissite 000-default' "the default site is disabled"
_t_called 'a2ensite nextcloud' "the Nextcloud site is enabled"

# --- PHP --------------------------------------------------------------------
_t_file_has "$PHP_INI" 'memory_limit = 512M' "memory_limit is raised"
_t_file_has "$PHP_INI" 'upload_max_filesize = 16G' "the upload limit is raised"
_t_file_has "$PHP_INI" 'max_execution_time = 3600' "the execution ceiling is raised"
_t_file_has "$PHP_INI" 'opcache.interned_strings_buffer=16' "the OPcache block is appended"

# --- occ --------------------------------------------------------------------
_t_called 'occ maintenance:install' "the installer runs"
_t_called 'trusted_domains 1 --value=10.0.0.7' "the Pi's IP is trusted"
_t_called "trusted_domains 3 --value=${PI_HOSTNAME}.local" "the .local name is trusted"
_t_called 'memcache.locking' "Redis is wired in for locking"
_t_called 'occ background:cron' "background jobs move to cron"
_t_called 'crontab -u www-data' "the www-data crontab is installed"
_t_has "$phase_output" 'Nextcloud is responding!' "an installed: true status reads as healthy"
_t_has "$phase_output" 'save_config called' "the run is persisted to the config"
_t_has "$phase_output" 'Access Nextcloud at: http://10.0.0.7' "the access URL is reported"

# --- The OPcache block must not be appended twice ---------------------------
# The guard is `grep -q opcache.interned_strings_buffer`; a second run over an
# already-configured ini must leave exactly one copy.
before="$(grep -c 'opcache.interned_strings_buffer' "$PHP_INI")"
mkdir -p /var/www/nextcloud
phase_install_nextcloud >/dev/null 2>&1
after="$(grep -c 'opcache.interned_strings_buffer' "$PHP_INI")"
_t_eq "$before" "$after" "re-running does not duplicate the OPcache block"

_t_report "test_rpi_nc_install.sh"
